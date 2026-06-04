"""
deploy_sepolia.py – Deploy ViolationRegistry.sol lên Sepolia Testnet

Yêu cầu trong .env:
  WALLET_PRIVATE_KEY=...   (64 hex chars, co hoac khong co 0x prefix)
  SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID

Sau khi deploy thành công, script tự động cập nhật CONTRACT_ADDRESS trong .env.
"""

import os
import sys
import re
import solcx
from dotenv import load_dotenv

load_dotenv()

PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")
RPC_URL = os.getenv("SEPOLIA_RPC_URL", "")

SEPOLIA_CHAIN_ID = 11155111


def _normalize_key(key: str) -> str:
    """Tu dong them 0x prefix neu MetaMask export key khong co."""
    key = key.strip()
    if len(key) == 64 and not key.startswith("0x"):
        key = "0x" + key
    return key


PRIVATE_KEY = _normalize_key(PRIVATE_KEY)


def check_env():
    """Kiểm tra .env đã có đủ thông tin Sepolia chưa."""
    errors = []
    if not PRIVATE_KEY.startswith("0x") or len(PRIVATE_KEY) != 66:
        errors.append(
            "WALLET_PRIVATE_KEY khong hop le. Can 64 ky tu hex.\n"
            "  Lay tu MetaMask: Account Details > Show Private Key\n"
            "  Co the paste ca co hoac khong co 0x prefix deu duoc.")
    if not RPC_URL.startswith("http"):
        errors.append(
            "SEPOLIA_RPC_URL khong hop le.\n"
            "  Dang ky mien phi tai https://app.infura.io hoac https://dashboard.alchemy.com"
        )
    if errors:
        print("[DEPLOY-SEPOLIA] Thieu cau hinh trong .env:")
        for e in errors:
            print(f"  [!] {e}")
        sys.exit(1)


def compile_contract():
    """Compile ViolationRegistry.sol bang solcx."""
    print("[DEPLOY-SEPOLIA] Kiem tra va cai dat Solidity compiler 0.8.20...")
    try:
        solcx.install_solc("0.8.20")
        solcx.set_solc_version("0.8.20")
        print("[DEPLOY-SEPOLIA] Solidity compiler OK")
    except Exception as e:
        print(f"[DEPLOY-SEPOLIA] Loi cai dat solc: {e}")
        sys.exit(1)

    print("[DEPLOY-SEPOLIA] Compiling ViolationRegistry.sol...")
    try:
        compiled = solcx.compile_files(
            ["ViolationRegistry.sol"],
            output_values=["abi", "bin"],
            solc_version="0.8.20",
        )
        key = "ViolationRegistry.sol:ViolationRegistry"
        interface = compiled[key]
        print("[DEPLOY-SEPOLIA] Compilation OK")
        return interface["abi"], interface["bin"]
    except Exception as e:
        print(f"[DEPLOY-SEPOLIA] Loi compile: {e}")
        sys.exit(1)


def deploy_contract(abi, bytecode):
    """Deploy contract lên Sepolia Testnet."""
    from web3 import Web3
    from eth_account import Account

    print(f"[DEPLOY-SEPOLIA] Ket noi toi Sepolia RPC...")
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 60}))

    if not w3.is_connected():
        print(f"[DEPLOY-SEPOLIA] Khong ket noi duoc toi RPC: {RPC_URL}")
        print("  Kiem tra lai SEPOLIA_RPC_URL trong .env")
        sys.exit(1)

    chain_id = w3.eth.chain_id
    if chain_id != SEPOLIA_CHAIN_ID:
        print(f"[DEPLOY-SEPOLIA] CANH BAO: Chain ID = {chain_id}, khong phai Sepolia {SEPOLIA_CHAIN_ID}!")
        print("  Kiem tra lai SEPOLIA_RPC_URL trong .env")
        sys.exit(1)

    print(f"[DEPLOY-SEPOLIA] Da ket noi Sepolia Testnet! Chain ID: {chain_id}")

    account = Account.from_key(PRIVATE_KEY)
    balance = w3.from_wei(w3.eth.get_balance(account.address), "ether")
    print(f"[DEPLOY-SEPOLIA] Vi deployer : {account.address}")
    print(f"[DEPLOY-SEPOLIA] So du       : {balance:.6f} SepoliaETH")

    if balance < 0.001:
        print("[DEPLOY-SEPOLIA] So du qua thap! Can it nhat 0.001 SepoliaETH de deploy.")
        print("  Lay SepoliaETH mien phi tai:")
        print("    - https://www.alchemy.com/faucets/ethereum-sepolia")
        print("    - https://cloud.google.com/application/web3/faucet/ethereum/sepolia")
        sys.exit(1)

    # Build transaction
    print("[DEPLOY-SEPOLIA] Dang gui transaction deploy...")
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address, "pending")

    # EIP-1559 gas pricing
    try:
        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", 0)
        max_priority = w3.to_wei(2, "gwei")
        max_fee = int(base_fee * 2) + max_priority

        tx = contract.constructor().build_transaction({
            "chainId": SEPOLIA_CHAIN_ID,
            "from": account.address,
            "nonce": nonce,
            "gas": 3_000_000,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority,
        })
        print(f"[DEPLOY-SEPOLIA] Gas strategy: EIP-1559 (maxFee={w3.from_wei(max_fee, 'gwei'):.1f} gwei)")
    except Exception:
        # Fallback to legacy gas pricing
        gas_price = int(w3.eth.gas_price * 1.3)
        tx = contract.constructor().build_transaction({
            "chainId": SEPOLIA_CHAIN_ID,
            "from": account.address,
            "nonce": nonce,
            "gas": 3_000_000,
            "gasPrice": gas_price,
        })
        print(f"[DEPLOY-SEPOLIA] Gas strategy: Legacy (gasPrice={w3.from_wei(gas_price, 'gwei'):.1f} gwei)")

    # Sign and send
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hex = tx_hash.hex()

    print(f"[DEPLOY-SEPOLIA] TX da gui! Hash: {tx_hex}")
    print(f"[DEPLOY-SEPOLIA] Xem tren Etherscan: https://sepolia.etherscan.io/tx/{tx_hex}")
    print(f"[DEPLOY-SEPOLIA] Dang cho xac nhan tu mang Sepolia ~15-30 giay...")

    # Wait for receipt
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    except Exception as e:
        print(f"[DEPLOY-SEPOLIA] Het thoi gian cho xac nhan: {e}")
        print(f"  TX Hash: {tx_hex}")
        print(f"  Kiem tra tren: https://sepolia.etherscan.io/tx/{tx_hex}")
        sys.exit(1)

    if receipt["status"] != 1:
        print("[DEPLOY-SEPOLIA] Transaction THAT BAI (reverted)!")
        print(f"  TX Hash: {tx_hex}")
        sys.exit(1)

    contract_address = receipt.contractAddress
    print(f"[DEPLOY-SEPOLIA] Deploy THANH CONG!")
    print(f"[DEPLOY-SEPOLIA]   Contract  : {contract_address}")
    print(f"[DEPLOY-SEPOLIA]   Block     : {receipt['blockNumber']}")
    print(f"[DEPLOY-SEPOLIA]   Gas used  : {receipt['gasUsed']}")
    print(f"[DEPLOY-SEPOLIA]   Etherscan : https://sepolia.etherscan.io/address/{contract_address}")

    return contract_address


def update_env(contract_address):
    """Cập nhật CONTRACT_ADDRESS trong .env, giữ nguyên các biến khác."""
    env_path = ".env"
    if not os.path.exists(env_path):
        print("[DEPLOY-SEPOLIA] File .env khong ton tai!")
        sys.exit(1)

    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Thay thế hoặc thêm CONTRACT_ADDRESS
    pattern = r"^CONTRACT_ADDRESS=.*$"
    replacement = f"CONTRACT_ADDRESS={contract_address}"

    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + f"\n{replacement}\n"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[DEPLOY-SEPOLIA] .env da cap nhat CONTRACT_ADDRESS = {contract_address}")


def main():
    print("=" * 60)
    print("  ECOGUARD AI — DEPLOY LEN SEPOLIA TESTNET")
    print("=" * 60)
    print()

    check_env()
    abi, bytecode = compile_contract()
    contract_address = deploy_contract(abi, bytecode)
    update_env(contract_address)

    print()
    print("=" * 60)
    print("  DEPLOY HOAN TAT!")
    print(f"  Contract: {contract_address}")
    print(f"  Etherscan: https://sepolia.etherscan.io/address/{contract_address}")
    print("=" * 60)


if __name__ == "__main__":
    main()
