import requests


def account_exists(base_url: str, account_addr: str) -> bool:
    return get_account(base_url, account_addr) is not None


def get_account(base_url: str, account_addr: str) -> dict:
    return requests.get(f"{base_url}/rpc/v1/accounts/{account_addr}").json()


def get_resource_data(base_url: str, account_addr: str, resource_type: str) -> dict:
    response = requests.get(f"{base_url}/rpc/v1/accounts/{account_addr}/resources/{resource_type}")
    res_data = response.json()
    return res_data["result"][0]


def get_account_supra_coin_balance(base_url: str, account_addr: str) -> int:
    if not account_exists(base_url, account_addr):
        return 0
    res_data = get_resource_data(base_url, account_addr, "0x1::coin::CoinStore<0x1::supra_coin::SupraCoin>")
    return int(res_data["coin"]["value"])


if __name__ == "__main__":
    is_testnet = False
    base_url = "https://rpc-testnet.supra.com/" if is_testnet else "https://rpc-mainnet.supra.com"

    # account_addr = "e3948c9e3a24c51c4006ef2acc44606055117d021158f320062df099c4a94150" # DORA
    account_addr = "429d89b7df74384ee5ead8c9487d6e1f4dcdec86ade77c2fc29c3e6ace649ec1"  # foundation multi-sig
    print("Balance:", get_account_supra_coin_balance(base_url, account_addr))
