import hashlib
import time

import requests
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import EntryFunction

from airdrop import get_account_addr, print_balance, fund_account_with_faucet, watch_balance
from check_transaction import wait_for_tx
from transaction_payload import MultiSigTransactionPayload
from transfer_supra import create_transfer_supra_entry_func, create_entry_func, send_tx


def compute_multisig_account_addr(account_owner_addr: str, sequence_number: int) -> AccountAddress:
    u64_serializer = Serializer()
    u64_serializer.u64(sequence_number)
    multisig_account_seed = (str.encode("supra_framework::multisig_account") + u64_serializer.output())
    owner_account = AccountAddress.from_str_relaxed(account_owner_addr)
    return AccountAddress.for_resource_account(owner_account, multisig_account_seed)


def compute_multisig_tx_payload_hash(entry_func: EntryFunction) -> bytes:
    payload = MultiSigTransactionPayload(entry_func)
    struct_serializer = Serializer()
    struct_serializer.struct(payload)
    serialized_payload = struct_serializer.output()
    return hashlib.sha3_256(serialized_payload).digest()


def create_propose_multisig_tx_entry_func(
        multisig_account_address: AccountAddress,
        multisig_transaction_payload_hash: bytes,
) -> EntryFunction:
    return create_entry_func(
        "multisig_account",
        "create_transaction_with_hash",
        [
            multisig_account_address,
            multisig_transaction_payload_hash,
        ],
        [
            Serializer.struct,
            Serializer.to_bytes,
        ])


def get_multisig_tx_sequence_from_tx_hash(tx_hash: str) -> int:
    tx_data = requests.get(f"{base_url}/rpc/v1/transactions/{tx_hash}").json()
    if tx_data["status"] != "Success":
        raise Exception("transaction is not successfully executed")
    for event in tx_data["output"]["Move"]["events"]:
        if event["type"] == "0x1::multisig_account::CreateTransactionEvent":
            return int(event["data"]["sequence_number"])
    raise Exception("something went wrong")


if __name__ == "__main__":
    base_url = "https://rpc-testnet.supra.com/"
    mnemonic_file = "mnemonic_multisig.enc"
    sender_account, sender_addr = get_account_addr(mnemonic_file)
    multisig_addr = compute_multisig_account_addr(sender_addr, 1)
    print("Multisig address:", str(multisig_addr))

    recipient_addr = "0xb8922417130785087f9c7926e76542531b703693fdc74c9386b65cf4427f4e80"
    amount = 20
    entry_func, max_gas = create_transfer_supra_entry_func(base_url, recipient_addr, amount)

    # Step 1: fund the multisig account through airdrop
    balance = print_balance(base_url, str(multisig_addr))
    if balance < amount + max_gas:
        tx_hash = fund_account_with_faucet(base_url, str(multisig_addr))
        print("Airdrop transaction hash:", tx_hash)
        watch_balance(base_url, str(multisig_addr), repeat=10, interval_sec=5)

    # Step 2: create multisig proposal
    entry_func_hash = compute_multisig_tx_payload_hash(entry_func)
    entry_func = create_propose_multisig_tx_entry_func(multisig_addr, entry_func_hash)
    tx_hash = send_tx(base_url, sender_account, entry_func)
    print("Transaction submitted with hash:", tx_hash)

    wait_for_tx(base_url, tx_hash, 3, 5)
    time.sleep(5)
    print("Multisig sequence number:", get_multisig_tx_sequence_from_tx_hash(tx_hash))
