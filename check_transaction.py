import time
from datetime import datetime, timezone

from check_balance import get_json


def get_transaction_info(base_url: str, tx_hash: str):
    return get_json(f"{base_url}/rpc/v1/transactions/{tx_hash}")


def get_transaction_status(base_url: str, tx_hash: str) -> str:
    res_data = get_transaction_info(base_url, tx_hash)
    try:
        return res_data["output"]["Move"]["vm_status"] if res_data["status"] == "Fail" else res_data["status"]
    except:
        return f"Failed to get status of transaction {tx_hash}, with response {res_data}"


def get_transaction_block_time(base_url: str, tx_hash: str) -> int:
    d = get_transaction_info(base_url, tx_hash)
    return int(d["block_header"]["timestamp"]["microseconds_since_unix_epoch"])


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

    # tx_hash = "0xfd937da4f737151d5289a2bcd7c09af9feb7d680dee701f0281eec8c7de82126"
    tx_hash = "0xb7f387c873c0b0bccd765c31dd05139800eb0e48c9e9343751af1a12f76308c9"

    wait_for_tx(base_url, tx_hash, 3, 5, True)

    block_time = get_transaction_block_time(base_url, tx_hash) // 1_000_000
    elapsed_time = int(time.time()) - block_time
    print(f"Elapsed time: {elapsed_time // 3600}h {(elapsed_time % 3600) // 60}m {elapsed_time % 60}s")
