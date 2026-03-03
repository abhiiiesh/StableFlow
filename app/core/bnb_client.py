from web3 import Web3
from app.core.config import settings

BEP20_ABI = [
    {"inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [],
     "name": "decimals", "outputs": [{"name": "", "type": "uint8"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}],
     "stateMutability": "nonpayable", "type": "function"},
    {"anonymous": False,
     "inputs": [
         {"indexed": True, "name": "from", "type": "address"},
         {"indexed": True, "name": "to", "type": "address"},
         {"indexed": False, "name": "value", "type": "uint256"},
     ],
     "name": "Transfer", "type": "event"},
]

STABLECOIN_CONTRACTS = {
    "USDT": settings.USDT_CONTRACT,
    "USDC": settings.USDC_CONTRACT,
}


def get_web3() -> Web3:
    return Web3(Web3.HTTPProvider(settings.BNB_RPC_URL))


def get_token_contract(token: str):
    w3 = get_web3()
    address = STABLECOIN_CONTRACTS.get(token.upper())
    if not address:
        raise ValueError(f"Unsupported token: {token}")
    return w3.eth.contract(address=Web3.to_checksum_address(address), abi=BEP20_ABI)


def get_token_balance(wallet: str, token: str) -> float:
    contract = get_token_contract(token)
    decimals = contract.functions.decimals().call()
    raw = contract.functions.balanceOf(Web3.to_checksum_address(wallet)).call()
    return raw / (10 ** decimals)
