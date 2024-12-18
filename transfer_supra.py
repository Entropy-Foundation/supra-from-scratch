from types import MethodType
from typing import List, Any, Callable

import requests
import time
import hashlib
from aptos_sdk.account import Account
from aptos_sdk.authenticator import Ed25519Authenticator, Authenticator
from aptos_sdk.ed25519 import Signature, PublicKey, PrivateKey
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import RawTransaction, TypeTag, ModuleId, AccountAddress, EntryFunction, \
    TransactionArgument, Script, MultiAgentRawTransaction

from airdrop import get_account_addr
from check_balance import get_account_supra_coin_balance, get_account, account_exists, get_json
from check_block import get_block_round_by_height
from check_transaction import wait_for_tx, get_transaction_block_time, get_transaction_block_height
from transaction_payload import TransactionPayload, payload_to_dict, Multisig


def get_account_seq_num(base_url: str, account_addr: str) -> int:
    return int(get_account(base_url, account_addr)["sequence_number"])


def post_json(url: str, d: dict) -> dict:
    resp = requests.post(url, json=d)
    try:
        return resp.json()
    except:
        print(f"post_json: error decoding JSON {resp}, with error text: {resp.text}")
        return {}


def simulate_tx_json(base_url: str, simulate_tx_dict: dict):
    res_data = post_json(f"{base_url}/rpc/v1/transactions/simulate", simulate_tx_dict)
    try:
        res = res_data["output"]["Move"]["vm_status"]
    except:
        print(res_data)
        res = "Error"
    print("Simulation result:", res)


def submit_tx_json(base_url: str, send_tx_dict: dict) -> str:
    return str(post_json(f"{base_url}/rpc/v1/transactions/submit", send_tx_dict))


def supra_prehash(self: RawTransaction | MultiAgentRawTransaction) -> bytes:
    salt = b"SUPRA::RawTransactionWithData" if isinstance(self,
                                                          MultiAgentRawTransaction) else b"SUPRA::RawTransaction"
    return hashlib.sha3_256(salt).digest()


def create_entry_func(
        module_name: str,
        function_name,
        function_args: [any],
        function_args_encoders: [[Callable[[Serializer, Any], None]]],
        module_addr: AccountAddress = AccountAddress.from_str_relaxed("1"),
        type_args: List[TypeTag] = [],
) -> EntryFunction:
    args = [TransactionArgument(arg, function_args_encoders[i]) for i, arg in enumerate(function_args)]
    return EntryFunction.natural(str(ModuleId(module_addr, module_name)), function_name, type_args, args)


def create_raw_tx(
        sender_addr: AccountAddress,
        sender_sequence_number: int,
        payload_content: EntryFunction | Multisig | Script,
        max_gas: int = 500_000,
        gas_unit_price: int = 100,
        tx_expiry_timespan: int = 300,
        chain_id: int = None,
        base_url: str = None,
) -> RawTransaction:
    tx_expiry_time = int(time.time()) + tx_expiry_timespan
    chain_id = chain_id or get_json(f"{base_url}/rpc/v1/transactions/chain_id")
    payload = TransactionPayload(payload_content)
    raw_tx = RawTransaction(sender_addr, sender_sequence_number, payload, max_gas, gas_unit_price,
                            tx_expiry_time, chain_id)
    raw_tx.prehash = MethodType(supra_prehash, raw_tx)
    return raw_tx


def auth_to_dict(obj: Any) -> dict[str, Any]:
    result = {}
    if isinstance(obj, Authenticator):
        if obj.variant == Authenticator.ED25519:
            result["Ed25519"] = auth_to_dict(obj.authenticator)
        else:
            raise NotImplementedError
    else:
        for k, v in obj.__dict__.items():
            if isinstance(v, PublicKey) or isinstance(v, Signature):
                result[k] = str(v)
            elif hasattr(v, "__dict__"):
                result[k] = auth_to_dict(v)  # Recursively handle nested objects
            else:
                result[k] = v
    return result


def create_tx_dict(pub_key: PublicKey, sig: Signature, raw_txn: RawTransaction) -> dict:
    auth = Authenticator(Ed25519Authenticator(pub_key, sig))

    return {
        "Move": {
            "raw_txn": payload_to_dict(raw_txn),
            "authenticator": auth_to_dict(auth),
        }
    }


def create_send_tx_dict(sender_account: Account, raw_txn: RawTransaction) -> dict:
    sig = sender_account.sign(raw_txn.keyed())
    return create_tx_dict(sender_account.public_key(), sig, raw_txn)


def create_simulate_tx_dict(sender_pub_key: PublicKey, raw_txn: RawTransaction) -> dict:
    private_key = PrivateKey.random()
    sig = private_key.sign(raw_txn.keyed())
    return create_tx_dict(sender_pub_key, sig, raw_txn)


def send_tx(base_url: str,
            sender_account: Account,
            payload_content: EntryFunction | Multisig | Script,
            max_gas: int = 500_000,
            gas_price: int = 100) -> str:
    raw_txn = create_raw_tx(
        sender_account.address(),
        get_account_seq_num(base_url, str(sender_account.address())),
        payload_content,
        max_gas,
        gas_price,
        base_url=base_url,
    )
    sim_tx_dict = create_simulate_tx_dict(sender_account.public_key(), raw_txn)
    simulate_tx_json(base_url, sim_tx_dict)
    send_tx_dict = create_send_tx_dict(sender_account, raw_txn)
    return submit_tx_json(base_url, send_tx_dict)


def create_transfer_supra_entry_func(
        base_url: str,
        rcpt_account_addr: str,
        amount: int):
    max_gas = 10 if account_exists(base_url, rcpt_account_addr) else 1020
    entry_func = create_entry_func(
        "supra_account",
        "transfer",
        [AccountAddress.from_str_relaxed(rcpt_account_addr), amount],
        [Serializer.struct, Serializer.u64])
    return entry_func, max_gas


if __name__ == "__main__":
    is_testnet = True
    base_url = "https://rpc-testnet1.supra.com" if is_testnet else "https://rpc-mainnet.supra.com"
    mnemonic_file = "mnemonic_multisig.enc" if is_testnet else "mnemonic_multisig_mainnet.enc"
    repeat = 1000 if is_testnet else 1

    sender_account, sender_addr = get_account_addr(mnemonic_file)

    recipient_addr = "e3948c9e3a24c51c4006ef2acc44606055117d021158f320062df099c4a94150"
    amount = 1000000000
    print(f"Transferring {amount} quants from {sender_addr} to {recipient_addr}.")

    entry_func, max_gas = create_transfer_supra_entry_func(base_url, recipient_addr, amount)

    for i in range(repeat):
        sender_balance_before = get_account_supra_coin_balance(base_url, sender_addr)
        rcpt_balance_before = get_account_supra_coin_balance(base_url, recipient_addr)

        start_time = int(time.time())
        tx_hash = send_tx(base_url, sender_account, entry_func, max_gas)
        submit_time = int(time.time())
        print("Transaction submitted with hash:", tx_hash)

        wait_for_tx(base_url, tx_hash, 30, 1)

        block_time = get_transaction_block_time(base_url, tx_hash) // 1_000_000
        current_time = int(time.time())

        block_height = get_transaction_block_height(base_url, tx_hash)
        rnd = get_block_round_by_height(base_url, block_height)
        previous_rnd = get_block_round_by_height(base_url, block_height - 1)

        print(
            f"Submission: {submit_time - start_time}s, Pre-block: {block_time - submit_time}s, Block: {current_time - block_time}s, Timeout rounds: {rnd - previous_rnd - 1}")
        print(
            f"Sender: {get_account_supra_coin_balance(base_url, sender_addr) - sender_balance_before}, Recipient: {get_account_supra_coin_balance(base_url, recipient_addr) - rcpt_balance_before}")
