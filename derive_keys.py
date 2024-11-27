import hashlib
from typing import List

from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from nacl.signing import SigningKey

from gen_mnemonic import load_mnemonic


def generate_bip44_account(mnemonic: str, account_number: int) -> bytes:
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
    bip44_mst = Bip44.FromSeed(seed_bytes, Bip44Coins.APTOS)
    bip44_acc = bip44_mst.Purpose().Coin().Account(account_number).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
    return bip44_acc.PrivateKey().Raw().ToBytes()


def load_private_key(file_path: str) -> bytes:
    mnemonic = load_mnemonic(file_path)
    account_number = int(input("Enter account number: "))
    return generate_bip44_account(mnemonic, account_number)


def load_multiple_private_keys(file_path: str, num_accounts: int) -> List[bytes]:
    mnemonic = load_mnemonic(file_path)
    private_keys = [generate_bip44_account(mnemonic, account_number) for account_number in range(num_accounts)]
    return private_keys

def print_keys(private_key_bytes: bytes):
    signing_key = SigningKey(private_key_bytes)
    public_key_bytes = signing_key.verify_key.encode()

    sha3_256 = hashlib.sha3_256()
    sha3_256.update(public_key_bytes + b'\x00')  # append 0x00 as the single-signature scheme identifier
    account_address = sha3_256.hexdigest()

    print("Private Key:", private_key_bytes.hex())
    print("Public Key:", public_key_bytes.hex())
    print("Supra Address:", account_address)

if __name__ == "__main__":
    # Print single private key details
    private_key_bytes = load_private_key("mnemonic_mainnet.enc")
    print_keys(private_key_bytes)

    # Print details for the first 5 accounts
    private_keys = load_multiple_private_keys("mnemonic_multisig.enc", 5)
    for i, private_key in enumerate(private_keys):
        print(f"\nAccount {i}:")
        print_keys(private_key)