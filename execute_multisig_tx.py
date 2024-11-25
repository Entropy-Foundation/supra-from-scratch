from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import EntryFunction

from check_balance import get_account_supra_coin_balance
from check_transaction import wait_for_tx
from derive_keys import load_multiple_private_keys
from propose_multisig_tx import compute_multisig_account_addr
from transaction_payload import Multisig, MultiSigTransactionPayload
from transfer_supra import create_transfer_supra_entry_func, send_tx, create_entry_func
from view_multisig_tx import invoke_module_view_function, get_multisig_account_owners, \
    get_multisig_account_last_resolved_seq, get_multisig_account_next_sequence_number, \
    get_multisig_num_signatures_required, get_multisig_tx_can_be_executed, get_multisig_tx_vote


def create_multisig(multisig_addr: AccountAddress, entry_func: EntryFunction) -> Multisig:
    return Multisig(multisig_addr, MultiSigTransactionPayload(entry_func))


def create_remove_multisig_tx_entry_func(
        multisig_account_addr: AccountAddress,
) -> EntryFunction:
    return create_entry_func(
        "multisig_account",
        "execute_rejected_transaction",
        [
            multisig_account_addr,
        ],
        [
            Serializer.struct,
        ])


if __name__ == "__main__":
    is_testnet = True
    base_url = "https://rpc-testnet1.supra.com/" if is_testnet else "https://rpc-mainnet.supra.com"
    mnemonic_file = "mnemonic_multisig.enc" if is_testnet else "mnemonic_multisig_mainnet.enc"

    private_keys = load_multiple_private_keys(mnemonic_file, 5)
    owners = [Account.load_key(private_keys[i].hex()) for i in range(len(private_keys))]
    owner_addrs = [str(owner.address()) for owner in owners]
    sender_account, sender_addr = owners[0], owner_addrs[0]

    multisig_addr = compute_multisig_account_addr(sender_addr, 1)
    print("Multisig address:", str(multisig_addr))
    multisig_owners = get_multisig_account_owners(base_url, multisig_addr)
    print("Multisig account owners:", multisig_owners)
    print("Owners:", owner_addrs)

    last_resolved_seq = get_multisig_account_last_resolved_seq(base_url, multisig_addr)
    print("Multisig last resolved seq:", last_resolved_seq)
    multisig_seq = get_multisig_account_next_sequence_number(base_url, multisig_addr) - 1
    print("Multisig current sequence number:", multisig_seq)

    threshold = get_multisig_num_signatures_required(base_url, multisig_addr)
    print("Multisig threshold:", threshold)

    print("Multisig tx can be executed:",
          get_multisig_tx_can_be_executed(base_url, multisig_addr, last_resolved_seq + 1))

    for addr in multisig_owners:
        voted, vote = get_multisig_tx_vote(base_url, multisig_addr, last_resolved_seq + 1,
                                           AccountAddress.from_str_relaxed(addr))
        print(f"Voted: {voted}, vote: {vote}")

    # entry_func = create_remove_multisig_tx_entry_func(multisig_addr)
    # tx_hash = send_tx(base_url, owners[0], entry_func)
    # print("Transaction submitted with hash:", tx_hash)
    # wait_for_tx(base_url, tx_hash, 3, 5)
    # exit(0)

    recipient_addr = "0xb8922417130785087f9c7926e76542531b703693fdc74c9386b65cf4427f4e80"
    amount = 20
    entry_func, _ = create_transfer_supra_entry_func(base_url, recipient_addr, amount)

    multisig = create_multisig(multisig_addr, entry_func)

    print("Multisig balance before transfer:", get_account_supra_coin_balance(base_url, str(multisig_addr)))
    print("Recipient balance before transfer:", get_account_supra_coin_balance(base_url, recipient_addr))

    tx_hash = send_tx(base_url, sender_account, multisig)
    print("Transaction submitted with hash:", tx_hash)

    wait_for_tx(base_url, tx_hash, 3, 5)

    print("Multisig balance after transfer:", get_account_supra_coin_balance(base_url, str(multisig_addr)))
    print("Recipient balance after transfer:", get_account_supra_coin_balance(base_url, recipient_addr))
