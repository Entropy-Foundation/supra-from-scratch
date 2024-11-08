from types import MethodType

from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.ed25519 import MultiPublicKey, MultiSignature

from airdrop import fund_account_with_faucet, watch_balance
from check_balance import get_account_supra_coin_balance
from check_transaction import wait_for_tx
from derive_keys import load_multiple_private_keys
from transaction_payload import payload_to_dict
from transfer_supra import create_transfer_supra_entry_func, create_raw_tx, get_account_seq_num, submit_tx_json


# Code copied from Aptos Python SDK's MultiSignature.serialize, except that we don't use a Serializer
def multisig_to_crypto_bytes(self: MultiSignature) -> bytes:
    signature_bytes = bytearray()
    bitmap = 0

    for signature in self.signatures:
        shift = 31 - signature[0]
        bitmap = bitmap | (1 << shift)
        signature_bytes.extend(signature[1].data())

    signature_bytes.extend(
        bitmap.to_bytes(MultiSignature.BITMAP_NUM_OF_BYTES, "big")
    )
    return signature_bytes


if __name__ == "__main__":
    is_testnet = True
    base_url = "https://rpc-testnet.supra.com/" if is_testnet else "https://rpc-mainnet.supra.com"
    mnemonic_file = "mnemonic_multisig.enc"
    num_signers, threshold = 3, 2

    private_keys = load_multiple_private_keys(mnemonic_file, num_signers)
    accounts = [Account.load_key(key.hex()) for key in private_keys]
    alice, bob, carol = accounts

    multisig_public_key = MultiPublicKey([alice.public_key(), bob.public_key(), carol.public_key()], threshold)
    multisig_addr = AccountAddress.from_key(multisig_public_key)

    print(f"Multisig account address: {multisig_addr}")

    recipient_addr = "0xb8922417130785087f9c7926e76542531b703693fdc74c9386b65cf4427f4e80"
    amount = 10
    entry_func, max_gas = create_transfer_supra_entry_func(base_url, recipient_addr, amount)

    # Step 1: fund the multisig account through airdrop. Note that airdrop is only possible for testnet.
    balance = get_account_supra_coin_balance(base_url, str(multisig_addr))
    print("Sender balance before transfer:", balance)
    print("Recipient balance before transfer:", get_account_supra_coin_balance(base_url, recipient_addr))
    if balance < amount + max_gas:
        tx_hash = fund_account_with_faucet(base_url, str(multisig_addr))
        print("Airdrop transaction hash:", tx_hash)
        watch_balance(base_url, str(multisig_addr), repeat=10, interval_sec=5)

    # Step 2: create and sign the multisig tx
    raw_tx = create_raw_tx(
        multisig_addr,
        get_account_seq_num(base_url, str(multisig_addr)),
        entry_func,
        max_gas,
        base_url=base_url,
    )

    alice_sig = alice.sign(raw_tx.keyed())
    bob_sig = bob.sign(raw_tx.keyed())
    carol_sig = carol.sign(raw_tx.keyed())
    # multisig_signature = MultiSignature([(1, bob_sig), (2, carol_sig)]) # Any two signatures should work
    multisig_signature = MultiSignature([(0, alice_sig), (2, carol_sig)])

    multisig_signature.to_crypto_bytes = MethodType(multisig_to_crypto_bytes, multisig_signature)
    assert multisig_public_key.verify(raw_tx.keyed(), multisig_signature)

    tx_hash = submit_tx_json(base_url, {
        "Move": {
            "raw_txn": payload_to_dict(raw_tx),
            "authenticator": {
                "MultiEd25519": {
                    "public_key": multisig_public_key.to_crypto_bytes().hex(),
                    "signature": multisig_signature.to_crypto_bytes().hex(),
                },
            },
        }
    })

    print("Transaction submitted with hash:", tx_hash)
    wait_for_tx(base_url, tx_hash, 3, 5)

    print("Sender balance after transfer:", get_account_supra_coin_balance(base_url, str(multisig_addr)))
    print("Recipient balance after transfer:", get_account_supra_coin_balance(base_url, recipient_addr))
