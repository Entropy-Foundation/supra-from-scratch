from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from bip_utils import Bip39MnemonicGenerator
import os
import getpass


def store_mnemonic(mnemonic: str, file_path: str) -> None:
    if os.path.exists(file_path):
        raise FileExistsError(f"Error: The file '{file_path}' already exists. Choose a different file path.")

    password = getpass.getpass("Enter password to encrypt the mnemonic: ").encode()

    # Generate a salt
    salt = os.urandom(16)
    kdf = Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1, backend=default_backend())
    key = kdf.derive(password)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, mnemonic.encode(), None)

    # Store the salt, nonce, and encrypted mnemonic in a file
    with open(file_path, "wb") as f:
        f.write(salt + nonce + ciphertext)
    print(f"Mnemonic encrypted and stored in '{file_path}'.")


def load_mnemonic(file_path: str) -> str:
    password = getpass.getpass("Enter password to decrypt the mnemonic: ").encode()

    with open(file_path, "rb") as f:
        data = f.read()

    salt, nonce, ciphertext = data[:16], data[16:28], data[28:]
    kdf = Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1, backend=default_backend())
    key = kdf.derive(password)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


if __name__ == "__main__":
    mnemonic_file = "mnemonic_multisig.enc"

    # Generate the mnemonic
    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12).ToStr()
    print("Mnemonic:", mnemonic)

    store_mnemonic(mnemonic, mnemonic_file)

    decrypted_mnemonic = load_mnemonic(mnemonic_file)
    print("Decrypted mnemonic:", decrypted_mnemonic)
