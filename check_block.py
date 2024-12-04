from check_balance import get_json


def get_block_by_height(base_url: str, height: int, with_txs: bool = False) -> dict:
    with_txs = "true" if with_txs else "false"
    return get_json(f"{base_url}/rpc/v1/block/height/{height}?with_finalized_transactions={with_txs}")


def get_block_round_by_height(base_url: str, height: int) -> int:
    d = get_block_by_height(base_url, height)
    return int(d['header']['view']['round'])


if __name__ == "__main__":
    is_testnet = False
    base_url = "https://rpc-testnet.supra.com" if is_testnet else "https://rpc-mainnet.supra.com"
    block_height = 3296634
    round = get_block_round_by_height(base_url, block_height)
    print(f"Block height: {block_height}, round: {round}")
