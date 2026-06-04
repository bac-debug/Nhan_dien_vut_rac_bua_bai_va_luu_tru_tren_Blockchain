"""
blockchain.py – Tự động ký và ghi vi phạm lên Ethereum Sepolia Testnet

Luồng hoạt động:
  inference_thread phát hiện vi phạm
      → tính SHA-256 hash của ảnh
      → gọi record_violation_on_chain() trong thread riêng (không block AI)
          → ký giao dịch bằng private key từ .env
          → gửi lên Sepolia qua RPC
          → nhận tx_hash
          → cập nhật SQLite (update_tx_hash)
          → in log
"""

import os
import time
import threading
from dotenv import load_dotenv

# Load .env trước khi import web3
load_dotenv()

# ── Kiểm tra biến môi trường ──────────────────────────────────────────────────
_raw_key = os.getenv("WALLET_PRIVATE_KEY", "").strip()
# MetaMask export key không có 0x prefix → tự động thêm
if len(_raw_key) == 64 and not _raw_key.startswith("0x"):
    _raw_key = "0x" + _raw_key
PRIVATE_KEY       = _raw_key
RPC_URL           = os.getenv("SEPOLIA_RPC_URL", "")
CONTRACT_ADDRESS  = os.getenv("CONTRACT_ADDRESS", "")

# ABI tối thiểu của ViolationRegistry.sol (chỉ cần hàm logViolation + sự kiện)
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "violationId", "type": "uint256"},
            {"internalType": "string",  "name": "imageHash",   "type": "string"}
        ],
        "name": "logViolation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "violationId", "type": "uint256"},
            {"internalType": "string",  "name": "imageHash",   "type": "string"}
        ],
        "name": "verifyViolation",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "internalType": "uint256", "name": "violationId", "type": "uint256"},
            {"indexed": False, "internalType": "string",  "name": "imageHash",   "type": "string"},
            {"indexed": True,  "internalType": "address", "name": "reporter",    "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp",   "type": "uint256"}
        ],
        "name": "ViolationLogged",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "totalRecords",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ── Trạng thái kết nối blockchain ─────────────────────────────────────────
blockchain_status = {
    "connected":  False,
    "wallet":     "",
    "network":    "",
    "chain_id":   0,
    "error":      ""
}

# Khóa để tránh gửi nhiều giao dịch cùng lúc (nonce conflict)
_tx_lock = threading.Lock()

# ── Lazy-load web3 (chỉ import khi cấu hình đầy đủ) ──────────────────────
_w3       = None
_contract = None
_account  = None

def _is_configured() -> bool:
    """Kiểm tra .env đã điền đủ thông tin chưa."""
    return (
        PRIVATE_KEY.startswith("0x") and len(PRIVATE_KEY) == 66 and
        RPC_URL.startswith("http") and
        CONTRACT_ADDRESS.startswith("0x") and len(CONTRACT_ADDRESS) == 42
    )

def init_blockchain() -> bool:
    """
    Khởi tạo kết nối Web3 và smart contract.
    Trả về True nếu thành công, False nếu thiếu cấu hình hoặc lỗi.
    """
    global _w3, _contract, _account, blockchain_status

    if not _is_configured():
        blockchain_status["error"] = (
            "Chưa cấu hình .env: cần WALLET_PRIVATE_KEY, "
            "SEPOLIA_RPC_URL, CONTRACT_ADDRESS"
        )
        print(f"[BLOCKCHAIN] ⚠ Chưa cấu hình: {blockchain_status['error']}")
        return False

    try:
        from web3 import Web3
        from eth_account import Account

        w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 30}))
        if not w3.is_connected():
            blockchain_status["error"] = f"Không kết nối được tới RPC: {RPC_URL}"
            print(f"[BLOCKCHAIN] ✗ {blockchain_status['error']}")
            return False

        account  = Account.from_key(PRIVATE_KEY)
        checksum = Web3.to_checksum_address(CONTRACT_ADDRESS)
        contract = w3.eth.contract(address=checksum, abi=CONTRACT_ABI)

        _w3       = w3
        _contract = contract
        _account  = account

        chain_id = w3.eth.chain_id
        balance  = w3.from_wei(w3.eth.get_balance(account.address), "ether")

        blockchain_status.update({
            "connected": True,
            "wallet":    account.address,
            "network":   "Sepolia Testnet" if chain_id == 11155111 else f"Chain {chain_id}",
            "chain_id":  chain_id,
            "error":     ""
        })

        print(f"[BLOCKCHAIN] ✓ Kết nối thành công!")
        print(f"[BLOCKCHAIN]   Ví    : {account.address}")
        print(f"[BLOCKCHAIN]   Mạng  : {blockchain_status['network']}")
        print(f"[BLOCKCHAIN]   Số dư : {balance:.6f} ETH")
        print(f"[BLOCKCHAIN]   Contract: {checksum}")
        return True

    except Exception as e:
        blockchain_status["error"] = str(e)
        blockchain_status["connected"] = False
        print(f"[BLOCKCHAIN] ✗ Lỗi khởi tạo: {e}")
        return False


def record_violation_on_chain(violation_id: int, image_hash: str,
                               on_success=None, max_retries: int = 3):
    """
    Ký và ghi vi phạm lên blockchain trong một thread riêng.
    Không block luồng inference.

    Args:
        violation_id : ID vi phạm từ SQLite
        image_hash   : SHA-256 hex string (64 ký tự, không có 0x)
        on_success   : callback(tx_hash: str) gọi khi thành công
        max_retries  : số lần thử lại nếu thất bại
    """
    if not blockchain_status["connected"] or _w3 is None:
        print(f"[BLOCKCHAIN] Bỏ qua ghi chain (chưa kết nối) - vi phạm #{violation_id}")
        return

    def _submit():
        from web3 import Web3

        for attempt in range(1, max_retries + 1):
            try:
                with _tx_lock:
                    nonce = _w3.eth.get_transaction_count(_account.address, "pending")

                    # Build transaction với EIP-1559 hoặc legacy gas
                    tx_params = {
                        "from":     _account.address,
                        "nonce":    nonce,
                        "gas":      300_000,
                        "chainId":  blockchain_status["chain_id"],
                    }

                    # EIP-1559 cho Sepolia, legacy cho Ganache
                    try:
                        latest = _w3.eth.get_block("latest")
                        base_fee = latest.get("baseFeePerGas", 0)
                        if base_fee > 0:
                            max_priority = _w3.to_wei(2, "gwei")
                            tx_params["maxFeePerGas"] = int(base_fee * 2) + max_priority
                            tx_params["maxPriorityFeePerGas"] = max_priority
                        else:
                            tx_params["gasPrice"] = int(_w3.eth.gas_price * 1.2)
                    except Exception:
                        tx_params["gasPrice"] = int(_w3.eth.gas_price * 1.2)

                    tx = _contract.functions.logViolation(
                        violation_id, image_hash
                    ).build_transaction(tx_params)

                    signed = _account.sign_transaction(tx)
                    tx_hash = _w3.eth.send_raw_transaction(signed.raw_transaction)
                    tx_hex  = tx_hash.hex()

                print(f"[BLOCKCHAIN] ⏳ Vi phạm #{violation_id} | TX gửi: {tx_hex}")

                # Chờ transaction được confirm (timeout 180s cho Sepolia)
                receipt = _w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

                if receipt["status"] == 1:
                    print(f"[BLOCKCHAIN] ✅ Vi phạm #{violation_id} đã ghi lên chain!")
                    print(f"[BLOCKCHAIN]   TX Hash : {tx_hex}")
                    print(f"[BLOCKCHAIN]   Block   : {receipt['blockNumber']}")
                    print(f"[BLOCKCHAIN]   Gas dùng: {receipt['gasUsed']}")
                    if blockchain_status["chain_id"] == 11155111:
                        print(f"[BLOCKCHAIN]   Etherscan: https://sepolia.etherscan.io/tx/{tx_hex}")
                    if on_success:
                        on_success(tx_hex)
                else:
                    print(f"[BLOCKCHAIN] ✗ Transaction bị revert - vi phạm #{violation_id}")
                return  # Thoát vòng lặp retry

            except Exception as e:
                print(f"[BLOCKCHAIN] Lỗi lần {attempt}/{max_retries} - vi phạm #{violation_id}: {e}")
                if attempt < max_retries:
                    time.sleep(5 * attempt)  # Tăng dần thời gian chờ
                else:
                    print(f"[BLOCKCHAIN] ✗ Hết số lần thử - vi phạm #{violation_id} không được ghi lên chain")

    # Chạy trong thread riêng để không block inference
    t = threading.Thread(target=_submit, daemon=True,
                         name=f"blockchain-viol-{violation_id}")
    t.start()


def get_status() -> dict:
    """Trả về trạng thái kết nối blockchain cho API."""
    return blockchain_status.copy()
