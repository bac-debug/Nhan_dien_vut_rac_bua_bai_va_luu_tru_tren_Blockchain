import os
import sys
import solcx
from web3 import Web3

# ── Initialize solc 0.8.20
print("[DEPLOY] Checking and installing Solidity compiler version 0.8.20...")
try:
    solcx.install_solc("0.8.20")
    solcx.set_solc_version("0.8.20")
    print("[DEPLOY] Solidity compiler OK")
except Exception as e:
    print(f"[DEPLOY] Error installing solc: {e}")
    sys.exit(1)

# ── Compile contract
print("[DEPLOY] Compiling ViolationRegistry.sol...")
try:
    temp_file = "ViolationRegistry.sol"
    compiled_sol = solcx.compile_files(
        [temp_file],
        output_values=["abi", "bin"],
        solc_version="0.8.20"
    )
    contract_key = f"{temp_file}:ViolationRegistry"
    contract_interface = compiled_sol[contract_key]
    abi = contract_interface["abi"]
    bytecode = contract_interface["bin"]
    print("[DEPLOY] Compilation OK")
except Exception as e:
    print(f"[DEPLOY] Compilation error: {e}")
    sys.exit(1)

# ── Connect to Web3 local Ganache
RPC_URL = "http://127.0.0.1:8545"
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    print(f"[DEPLOY] Error: Cannot connect to local RPC at {RPC_URL}. Please verify Ganache is running.")
    sys.exit(1)

print(f"[DEPLOY] Connected to Ganache! Chain ID: {w3.eth.chain_id}")

# Get first account from Ganache
accounts = w3.eth.accounts
if not accounts:
    print("[DEPLOY] Error: No accounts found on Ganache.")
    sys.exit(1)

deployer = accounts[0]
print(f"[DEPLOY] Using deployer account: {deployer}")

# Ganache first private key from startup logs
PRIVATE_KEY = "0xae050491d3dfba01bd5c86f58201a17a80e3f3823cc3b6164b2de6e4a3c02fd2"

# ── Deploy contract
print("[DEPLOY] Sending contract deployment transaction...")
ViolationRegistry = w3.eth.contract(abi=abi, bytecode=bytecode)

try:
    nonce = w3.eth.get_transaction_count(deployer)
    transaction = ViolationRegistry.constructor().build_transaction({
        "chainId": w3.eth.chain_id,
        "from": deployer,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.eth.gas_price
    })
    
    # Sign transaction with private key
    from eth_account import Account
    acc = Account.from_key(PRIVATE_KEY)
    signed_tx = w3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print(f"[DEPLOY] Transaction sent! TX Hash: {tx_hash.hex()}")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    
    contract_address = tx_receipt.contractAddress
    print(f"[DEPLOY] Contract deployed successfully!")
    print(f"[DEPLOY]   Contract Address : {contract_address}")
    print(f"[DEPLOY]   Block Number     : {tx_receipt.blockNumber}")
    print(f"[DEPLOY]   Gas Used         : {tx_receipt.gasUsed}")
except Exception as e:
    print(f"[DEPLOY] Deployment error: {e}")
    sys.exit(1)

# ── Update .env
print("[DEPLOY] Updating environment configuration file .env...")
try:
    env_content = f"""# ════════════════════════════════════════════════════════════════════
#  Cấu hình blockchain – ĐƯỢC CẬP NHẬT TỰ ĐỘNG BỞI DEPLOY.PY
# ════════════════════════════════════════════════════════════════════

# Private key của ví đầu tiên trên Ganache
WALLET_PRIVATE_KEY={PRIVATE_KEY}

# RPC URL kết nối tới Local Ganache Node
SEPOLIA_RPC_URL={RPC_URL}

# Địa chỉ smart contract vừa deploy tự động
CONTRACT_ADDRESS={contract_address}
"""
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    print("[DEPLOY] .env updated successfully!")
except Exception as e:
    print(f"[DEPLOY] Error updating .env: {e}")
    sys.exit(1)

print("[DEPLOY] Deployment finished! System is ready to connect to local Blockchain.")
