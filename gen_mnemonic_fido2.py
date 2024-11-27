import getpass
import hmac
import os

from bip_utils import Bip39MnemonicGenerator
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import modes, algorithms, Cipher
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from fido2.client import Fido2Client, UserInteraction
from fido2.hid import CtapHidDevice
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity, \
    PublicKeyCredentialCreationOptions, PublicKeyCredentialParameters, PublicKeyCredentialType, \
    PublicKeyCredentialDescriptor, PublicKeyCredentialRequestOptions, UserVerificationRequirement


class PinUserInteraction(UserInteraction):
    def request_pin(self, permissions, rp_id):
        return getpass.getpass("Enter PIN: ")


def create_client(origin: str = "https://supra.com"):
    devices = list(CtapHidDevice.list_devices())
    if not devices:
        raise RuntimeError("No FIDO2 device found")

    return Fido2Client(devices[0], origin, user_interaction=PinUserInteraction())

def create_credential_fido2(user_name: str = "my_name", user_display_name="Myself") -> bytes:
    client = create_client()
    rp = PublicKeyCredentialRpEntity(id="supra.com", name="Supra RP")
    user = PublicKeyCredentialUserEntity(id=b"user_id", name=user_name, display_name=user_display_name)

    # Create credential options with HMAC-Secret extension
    options = PublicKeyCredentialCreationOptions(
        rp=rp,
        user=user,
        challenge=os.urandom(32),
        pub_key_cred_params=[PublicKeyCredentialParameters(type=PublicKeyCredentialType.PUBLIC_KEY, alg=-7)],
        extensions={"hmacCreateSecret": True},
    )

    # Create a new credential
    auth_data = client.make_credential(options).attestation_object.auth_data
    return auth_data.credential_data.credential_id


def store_mnemonic_fido2(mnemonic: str, file_path: str, user_name: str = "my_name", user_display_name="Myself") -> None:
    if os.path.exists(file_path):
        raise FileExistsError(f"Error: The file '{file_path}' already exists. Choose a different file path.")

    devices = list(CtapHidDevice.list_devices())
    if not devices:
        raise RuntimeError("No FIDO2 device found")

    client = Fido2Client(devices[0], "https://supra.com", user_interaction=PinUserInteraction())
    rp = PublicKeyCredentialRpEntity(id="supra.com", name="Supra RP")
    user = PublicKeyCredentialUserEntity(id=b"user_id", name=user_name, display_name=user_display_name)

    # Create credential options with HMAC-Secret extension
    options = PublicKeyCredentialCreationOptions(
        rp=rp,
        user=user,
        challenge=os.urandom(32),
        pub_key_cred_params=[PublicKeyCredentialParameters(type=PublicKeyCredentialType.PUBLIC_KEY, alg=-7)],
        extensions={"hmacCreateSecret": True},
    )

    # Create a new credential
    auth_data = client.make_credential(options).attestation_object.auth_data

    # Prepare for assertion with HMAC-Secret extension
    allow_list = [PublicKeyCredentialDescriptor(type=PublicKeyCredentialType.PUBLIC_KEY,
                                                id=auth_data.credential_data.credential_id)]
    fido2_salt = os.urandom(32)
    assertion_options = PublicKeyCredentialRequestOptions(
        challenge=os.urandom(32),
        rp_id=rp.id,
        allow_credentials=allow_list,
        user_verification=UserVerificationRequirement.PREFERRED,
        extensions={"hmacGetSecret": {"salt1": fido2_salt}},
    )
    assertion = client.get_assertion(assertion_options).get_response(0)
    hmac_secret = assertion.extension_results["hmacGetSecret"]["output1"]

    password = getpass.getpass("Enter password to encrypt the mnemonic: ").encode()

    # Generate a salt
    password_salt = os.urandom(16)
    kdf = Scrypt(salt=password_salt, length=32, n=2 ** 14, r=8, p=1, backend=default_backend())
    password_key = kdf.derive(password)

    h = hmac.HMAC(hmac_secret, digestmod=hashes.SHA256().name)
    h.update(password_key)
    final_key = h.digest()

    nonce = os.urandom(12)  # 96-bit IV for AES-GCM
    cipher = Cipher(algorithms.AES(final_key), modes.GCM(nonce), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(mnemonic.encode()) + encryptor.finalize()
    tag = encryptor.tag

    # Store the salt, nonce, and encrypted mnemonic in a file
    with open(file_path, "wb") as f:
        f.write(fido2_salt + password_salt + nonce + tag + ciphertext)
    print(f"Mnemonic encrypted and stored in '{file_path}'.")


def load_mnemonic_fido2(file_path: str, user_name: str = "my_name", user_display_name="Myself") -> str:
    password = getpass.getpass("Enter password to decrypt the mnemonic: ").encode()

    with open(file_path, "rb") as f:
        fido2_salt = f.read(32)  # First 32 bytes: FIDO2 salt
        password_salt = f.read(16)  # Next 16 bytes: Password salt
        nonce = f.read(12)  # Next 12 bytes: Nonce
        tag = f.read(16)  # Next 16 bytes: Authentication tag
        ciphertext = f.read()  # Remaining bytes: Ciphertext

    kdf = Scrypt(salt=password_salt, length=32, n=2 ** 14, r=8, p=1, backend=default_backend())
    password_key = kdf.derive(password)

    devices = list(CtapHidDevice.list_devices())
    if not devices:
        raise RuntimeError("No FIDO2 device found")

    client = Fido2Client(devices[0], "https://supra.com", user_interaction=PinUserInteraction())
    rp = PublicKeyCredentialRpEntity(id="supra.com", name="Supra RP")
    user = PublicKeyCredentialUserEntity(id=b"user_id", name=user_name, display_name=user_display_name)
    options = PublicKeyCredentialCreationOptions(
        rp=rp,
        user=user,
        challenge=os.urandom(32),
        pub_key_cred_params=[PublicKeyCredentialParameters(type=PublicKeyCredentialType.PUBLIC_KEY, alg=-7)],
        extensions={"hmacCreateSecret": True},
    )
    auth_data = client.make_credential(options).attestation_object.auth_data
    allow_list = [PublicKeyCredentialDescriptor(type=PublicKeyCredentialType.PUBLIC_KEY,
                                                id=auth_data.credential_data.credential_id)]

    assertion_options = PublicKeyCredentialRequestOptions(
        challenge=os.urandom(32),
        rp_id=rp.id,
        allow_credentials=allow_list,
        user_verification=UserVerificationRequirement.PREFERRED,
        extensions={"hmacGetSecret": {"salt1": fido2_salt}},
    )
    assertion_result = client.get_assertion(assertion_options)
    assertion = assertion_result.get_response(0)
    hmac_secret = assertion.extension_results["hmacGetSecret"]["output1"]

    h = hmac.HMAC(hmac_secret, digestmod=hashes.SHA256().name)
    h.update(password_key)
    final_key = h.digest()

    cipher = Cipher(algorithms.AES(final_key), modes.GCM(nonce, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    return plaintext.decode()


if __name__ == "__main__":
    mnemonic_file = "mnemonic_new_multisig_fido2.enc"

    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12).ToStr()
    print("Mnemonic:", mnemonic)

    store_mnemonic_fido2(mnemonic, mnemonic_file)
    decrypted_mnemonic = load_mnemonic_fido2(mnemonic_file)
    print("Decrypted mnemonic:", decrypted_mnemonic)
