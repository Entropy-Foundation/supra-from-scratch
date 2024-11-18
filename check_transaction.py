import time

from check_balance import get_json


def get_transaction_status(base_url: str, tx_hash: str) -> str:
    res_data = get_json(f"{base_url}/rpc/v1/transactions/{tx_hash}")
    try:
        return res_data["output"]["Move"]["vm_status"] if res_data["status"] == "Fail" else res_data["status"]
    except:
        return f"Failed to get status of transaction {tx_hash}, with response {res_data}"


def wait_for_tx(base_url: str, tx_hash: str, repeat: int, interval_sec: int, check_first=False) -> None:
    if check_first:
        status = get_transaction_status(base_url, tx_hash)
        print("Transaction status:", status)
        if status == "Success":
            return
    for i in range(repeat):
        time.sleep(interval_sec)
        status = get_transaction_status(base_url, tx_hash)
        print(f"Transaction status after {(i + 1) * interval_sec} seconds:", status)
        if status == "Success":
            break


if __name__ == "__main__":
    is_testnet = True
    base_url = "https://rpc-testnet.supra.com/" if is_testnet else "https://rpc-mainnet.supra.com"

    tx_hash = "0xfd937da4f737151d5289a2bcd7c09af9feb7d680dee701f0281eec8c7de82126"
    wait_for_tx(base_url, tx_hash, 3, 5, True)
