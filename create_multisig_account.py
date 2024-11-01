from typing import List
from aptos_sdk.account import Account
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import AccountAddress, EntryFunction

from check_balance import get_account_supra_coin_balance
from check_transaction import wait_for_tx
from derive_keys import load_multiple_private_keys
from transfer_supra import create_entry_func, send_tx


def create_create_multisig_account_entry_func(
        additional_owners: List[AccountAddress],
        num_signatures_required: int,
        metadata_keys: List[str],
        metadata_values: List[bytes],
        timeout_duration: int,
) -> EntryFunction:
    return create_entry_func(
        "multisig_account",
        "create_with_owners",
        [
            additional_owners,
            num_signatures_required,
            metadata_keys,
            metadata_values,
            timeout_duration,
        ],
        [
            Serializer.sequence_serializer(Serializer.struct),
            Serializer.u64,
            Serializer.sequence_serializer(Serializer.str),
            Serializer.sequence_serializer(Serializer.to_bytes),
            Serializer.u64,
        ])


if __name__ == "__main__":
    is_testnet = True
    base_url = "https://rpc-testnet.supra.com/" if is_testnet else "https://rpc-mainnet.supra.com"
    mnemonic_file = "mnemonic_multisig.enc"
    num_signers, threshold = 5, 3

    private_keys = load_multiple_private_keys(mnemonic_file, num_signers)
    sender_account = Account.load_key(private_keys[0].hex())
    sender_addr = str(sender_account.address())
    other_owners = [Account.load_key(private_keys[i].hex()).address() for i in range(1, len(private_keys))]

    print("Sender balance:", get_account_supra_coin_balance(base_url, sender_addr))
    entry_func = create_create_multisig_account_entry_func(other_owners, threshold, [], [], 600)
    tx_hash = send_tx(base_url, sender_account, entry_func)
    print("Transaction submitted with hash:", tx_hash)

    wait_for_tx(base_url, tx_hash, 3, 5)
