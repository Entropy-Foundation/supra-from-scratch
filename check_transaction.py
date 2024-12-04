import time
from datetime import datetime, timezone

from check_balance import get_json
from check_block import get_block_round_by_height


def get_transaction_info(base_url: str, tx_hash: str) -> dict:
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


def get_transaction_block_height(base_url: str, tx_hash: str) -> int:
    d = get_transaction_info(base_url, tx_hash)
    return int(d["block_header"]["height"])


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
    base_url = "https://rpc-testnet.supra.com" if is_testnet else "https://rpc-mainnet.supra.com"

    tx_hash = "0xdf33c5493e5b8cf694b1c59a3f9add67433fbe6cc33983eb4f415e39ba2f0a3b"

    wait_for_tx(base_url, tx_hash, 3, 1, True)

    block_time = get_transaction_block_time(base_url, tx_hash) // 1_000_000
    elapsed_time = int(time.time()) - block_time
    print(f"Elapsed time: {elapsed_time // 3600}h {(elapsed_time % 3600) // 60}m {elapsed_time % 60}s")

    block_height = get_transaction_block_height(base_url, tx_hash)
    rnd = get_block_round_by_height(base_url, block_height)
    previous_rnd = get_block_round_by_height(base_url, block_height - 1)
    print(f"timeout rounds: {rnd - previous_rnd - 1}")
