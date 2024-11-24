from check_balance import get_json


def get_block_by_height(base_url: str, height: int) -> dict:
    return get_json(f"{base_url}/rpc/v1/block/height/{height}?with_finalized_transactions=false")


def get_block_round_by_height(base_url: str, height: int) -> int:
    d = get_block_by_height(base_url, height)
    return int(d['header']['view']['round'])


if __name__ == "__main__":
    is_testnet = True
    base_url = "https://rpc-testnet.supra.com" if is_testnet else "https://rpc-mainnet.supra.com"
    block_height = 3296634
    round = get_block_round_by_height(base_url, block_height)
    print(f"Block height: {block_height}, round: {round}")
