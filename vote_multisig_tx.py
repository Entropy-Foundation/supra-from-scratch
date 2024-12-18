from aptos_sdk.account_address import AccountAddress
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import EntryFunction

from airdrop import get_account_addr
from check_transaction import wait_for_tx
from transfer_supra import create_entry_func, send_tx


def create_vote_multisig_tx_entry_func(
        multisig_account_addr: AccountAddress,
        multisig_seq_num: int,
        approved: bool,
) -> EntryFunction:
    return create_entry_func(
        "multisig_account",
        "vote_transanction",
        [
            multisig_account_addr,
            multisig_seq_num,
            approved,
        ],
        [
            Serializer.struct,
            Serializer.u64,
            Serializer.bool,
        ])


if __name__ == "__main__":
    is_testnet = False
    base_url = "https://rpc-testnet1.supra.com/" if is_testnet else "https://rpc-mainnet.supra.com"
    mnemonic_file = "mnemonic_multisig.enc" if is_testnet else "mnemonic_multisig_mainnet.enc"

    sender_account, sender_addr = get_account_addr(mnemonic_file)
    # multisig_addr = AccountAddress.from_str_relaxed(
    #     "0xbcfe584c9689f532f7dc58234a96f42e384ef7f1d4d2ac0b57fb7fd1de449579")
    multisig_addr = AccountAddress.from_str_relaxed(
        "0xadf39402c164a372a788358b7c8e695ae794d8f787ad36464708c8eb1f3a64a9")

    multisig_tx_seq = 2
    entry_func = create_vote_multisig_tx_entry_func(multisig_addr, multisig_tx_seq, True)
    tx_hash = send_tx(base_url, sender_account, entry_func)
    print("Transaction submitted with hash:", tx_hash)

    wait_for_tx(base_url, tx_hash, 3, 5)
