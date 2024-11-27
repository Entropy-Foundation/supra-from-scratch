from aptos_sdk.account_address import AccountAddress

from transfer_supra import post_json


def invoke_module_view_function(base_url: str,
                                full_function_name: str,
                                args: [str],
                                type_args: [str] = []) -> dict:
    d = {
        "function": full_function_name,
        "type_arguments": type_args,
        "arguments": args,
    }
    res = post_json(f"{base_url}/rpc/v1/view", d)
    try:
        return res["result"]
    except:
        print("Error in invoke_module_view_function:", res)
        return {}


def get_multisig_account_owners(base_url: str, account_addr: AccountAddress) -> [str]:
    res_data = invoke_module_view_function(
        base_url,
        "0x1::multisig_account::owners",
        [str(account_addr)],
    )
    return res_data[0]


def get_multisig_account_last_resolved_seq(base_url: str, account_addr: AccountAddress) -> int:
    res_data = invoke_module_view_function(
        base_url,
        "0x1::multisig_account::last_resolved_sequence_number",
        [str(account_addr)],
    )
    return int(res_data[0])


def get_multisig_account_next_sequence_number(base_url: str, account_addr: AccountAddress) -> int:
    res_data = invoke_module_view_function(
        base_url,
        "0x1::multisig_account::next_sequence_number",
        [str(account_addr)],
    )
    return int(res_data[0])


def get_multisig_num_signatures_required(base_url: str, account_addr: AccountAddress) -> int:
    res_data = invoke_module_view_function(
        base_url,
        "0x1::multisig_account::num_signatures_required",
        [str(account_addr)],
    )
    return int(res_data[0])


def get_multisig_tx_can_be_executed(base_url: str, account_addr: AccountAddress, seq_num: int) -> bool:
    res_data = invoke_module_view_function(
        base_url,
        "0x1::multisig_account::can_be_executed",
        [str(account_addr), str(seq_num)],
    )
    return bool(res_data[0])


def get_multisig_tx_vote(base_url: str, account_addr: AccountAddress, seq_num: int, voter_addr: AccountAddress) -> (
        bool, bool):
    res_data = invoke_module_view_function(
        base_url,
        "0x1::multisig_account::vote",
        [str(account_addr), str(seq_num), str(voter_addr)],
    )
    return res_data


if __name__ == "__main__":
    is_testnet = False
    base_url = "https://rpc-testnet1.supra.com/" if is_testnet else "https://rpc-mainnet.supra.com"
    mnemonic_file = "mnemonic_multisig.enc" if is_testnet else "mnemonic_multisig_mainnet.enc"

    multisig_addr = AccountAddress.from_str_relaxed(
        "0xadf39402c164a372a788358b7c8e695ae794d8f787ad36464708c8eb1f3a64a9")
    multisig_owners = get_multisig_account_owners(base_url, multisig_addr)
    print("Multisig account owners:", get_multisig_account_owners(base_url, multisig_addr))

    last_resolved_seq = get_multisig_account_last_resolved_seq(base_url, multisig_addr)
    print("Multisig last resolved seq:", last_resolved_seq)
    multisig_seq = get_multisig_account_next_sequence_number(base_url, multisig_addr) - 1
    print("Multisig current sequence number:", multisig_seq)

    threshold = get_multisig_num_signatures_required(base_url, multisig_addr)
    print("Multisig threshold:", threshold)

    for addr in multisig_owners:
        voted, vote = get_multisig_tx_vote(base_url, multisig_addr, 2, AccountAddress.from_str_relaxed(addr))
        print(f"{addr} voted: {voted}, vote: {vote}")

    print("Multisig tx can be executed:",
          get_multisig_tx_can_be_executed(base_url, multisig_addr, 2))
