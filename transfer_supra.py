from types import MethodType
from typing import List, Any, Callable

import requests
import time
import hashlib
from aptos_sdk.account import Account
from aptos_sdk.authenticator import AccountAuthenticator, Ed25519Authenticator, Authenticator
from aptos_sdk.ed25519 import Signature, PublicKey
from aptos_sdk.bcs import Serializer
from aptos_sdk.transactions import RawTransaction, TypeTag, ModuleId, AccountAddress, EntryFunction, \
    TransactionArgument, Script, MultiAgentRawTransaction

from airdrop import get_account_addr
from check_balance import get_account_supra_coin_balance, get_account, account_exists
from check_transaction import wait_for_tx
from transaction_payload import TransactionPayload, payload_to_dict, Multisig


def get_account_seq_num(base_url: str, account_addr: str) -> int:
    return int(get_account(base_url, account_addr)["sequence_number"])


def simulate_and_submit_tx(base_url: str, send_tx_dict: dict) -> str:
    res_data = requests.post(f"{base_url}/rpc/v1/transactions/simulate", json=send_tx_dict).json()
    print("Simulation result:", res_data["output"]["Move"]["vm_status"])
    return requests.post(f"{base_url}/rpc/v1/transactions/submit", json=send_tx_dict).json()


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
        tx_expiry_time: int = int(time.time()) + 300,
        chain_id: int = None,
        base_url: str = None,
) -> RawTransaction:
    chain_id = chain_id or requests.get(f"{base_url}/rpc/v1/transactions/chain_id").json()
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


def create_send_tx_dict(sender_account: Account, raw_txn: RawTransaction) -> dict:
    sig = sender_account.sign(raw_txn.keyed())
    auth = Authenticator(Ed25519Authenticator(sender_account.public_key(), sig))

    return {
        "Move": {
            "raw_txn": payload_to_dict(raw_txn),
            "authenticator": auth_to_dict(auth),
        }
    }


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
    send_tx_dict = create_send_tx_dict(sender_account, raw_txn)
    return simulate_and_submit_tx(base_url, send_tx_dict)


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
    # base_url = "https://rpc-testnet.supra.com/" if is_testnet else "https://rpc-mainnet.supra.com"
    base_url = "https://rpc-wallet-testnet.supra.com/" if is_testnet else "https://rpc-wallet-mainnet.supra.com/"

    mnemonic_file = "mnemonic_multisig.enc"
    sender_account, sender_addr = get_account_addr(mnemonic_file)

    recipient_addr = "0xb8922417130785087f9c7926e76542531b703693fdc74c9386b65cf4427f4e80"
    amount = 10
    print(f"Transferring {amount} quants from {sender_addr} to {recipient_addr}.")

    print("Sender balance before transfer:", get_account_supra_coin_balance(base_url, sender_addr))
    print("Recipient balance before transfer:", get_account_supra_coin_balance(base_url, recipient_addr))

    entry_func, max_gas = create_transfer_supra_entry_func(base_url, recipient_addr, amount)
    tx_hash = send_tx(base_url, sender_account, entry_func, max_gas)
    print("Transaction submitted with hash:", tx_hash)

    wait_for_tx(base_url, tx_hash, 3, 5)

    print("Sender balance after transfer:", get_account_supra_coin_balance(base_url, sender_addr))
    print("Recipient balance after transfer:", get_account_supra_coin_balance(base_url, recipient_addr))
