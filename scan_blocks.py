from check_block import get_block_by_height
from check_transaction import get_transaction_block_height


def get_block_txs(base_url: str, height: int) -> list[dict]:
    d = get_block_by_height(base_url, height, True)
    return d['transactions']


if __name__ == "__main__":
    is_testnet = True
    base_url = "https://rpc-testnet1.supra.com" if is_testnet else "https://rpc-mainnet.supra.com"

    start_tx_hash = "0x1af2f5ee78f4f7708c7915c8d9f7929b98de68652af2f75c6e92ef4ac9b6bcf9"
    end_tx_hash = "0x4658eb4afb7dcb3fb04e826e30c8e71d63c1f74fb6dd867600fb3b0b3fb7cb0b"
    start_block_height = get_transaction_block_height(base_url, start_tx_hash)
    end_block_height = get_transaction_block_height(base_url, end_tx_hash)

    print(
        f"Start block height: {start_block_height}, end block height: {end_block_height}, number of blocks: {end_block_height - start_block_height}")

    target_tx_hash = "0xdf33c5493e5b8cf694b1c59a3f9add67433fbe6cc33983eb4f415e39ba2f0a3b"
    # 632092
    for h in range(637230, end_block_height + 1):
        txs = get_block_txs(base_url, h)
        print(f"Block height: {h}:")
        for tx in txs:
            tx_hash = tx['hash']
            if tx_hash == target_tx_hash:
                print("Found target!")
                exit(0)
            print(tx_hash)
