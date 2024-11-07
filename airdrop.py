import requests
import time
from aptos_sdk.account import Account as Account

from check_balance import get_account_supra_coin_balance, account_exists
from derive_keys import load_private_key


def fund_account_with_faucet(base_url: str, account_addr: str) -> str:
    response = requests.get(f"{base_url}/rpc/v1/wallet/faucet/{account_addr}")
    res_data = response.json()
    try:
        return res_data["Accepted"]
    except Exception as e:
        print("Faucet error with message:", res_data)
        return ""


def get_account_addr(mnemonic_file: str) -> (Account, str):
    private_key = load_private_key(mnemonic_file).hex()
    sender_account = Account.load_key(private_key)
    account_addr = str(sender_account.address())
    return sender_account, account_addr


def print_balance(base_url: str, account_addr: str) -> int:
    if account_exists(base_url, account_addr):
        balance = get_account_supra_coin_balance(base_url, account_addr)
        print(f"Current balance for account {account_addr} in Supra quants:", balance)
        return balance
    else:
        print(f"New account {account_addr} with 0 balance.")
        return 0


def watch_balance(base_url: str, account_addr: str, repeat: int, interval_sec: int) -> None:
    for i in range(repeat):
        time.sleep(interval_sec)
        try:
            print_balance(base_url, account_addr)
        finally:
            print("Try again in 5 seconds.")
            pass


if __name__ == "__main__":
    # base_url = "https://rpc-testnet.supra.com/"
    base_url = "https://rpc-wallet-testnet.supra.com/"

    mnemonic_file = "mnemonic_multisig.enc"
    _, account_addr = get_account_addr(mnemonic_file)

    balance = print_balance(base_url, account_addr)

    tx_hash = fund_account_with_faucet(base_url, account_addr)
    print("Airdrop transaction hash:", tx_hash)
    watch_balance(base_url, account_addr, repeat=10, interval_sec=5)
