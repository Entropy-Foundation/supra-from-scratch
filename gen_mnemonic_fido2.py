import getpass
import hmac
import os

from bip_utils import Bip39MnemonicGenerator
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
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


def create_credential_fido2(client: Fido2Client, rp: PublicKeyCredentialRpEntity, user_name: str = "my_name",
                            user_display_name="Myself") -> bytes:
    user = PublicKeyCredentialUserEntity(id=b"user_id", name=user_name, display_name=user_display_name)

    # Create credential options with HMAC-Secret extension
    options = PublicKeyCredentialCreationOptions(
        rp=rp,
        user=user,
        challenge=os.urandom(32),
        pub_key_cred_params=[PublicKeyCredentialParameters(type=PublicKeyCredentialType.PUBLIC_KEY, alg=-7)],
        extensions={"hmacCreateSecret": True},
    )

    auth_data = client.make_credential(options).attestation_object.auth_data
    return auth_data.credential_data.credential_id


def store_mnemonic_fido2(mnemonic: str, file_path: str, crediential_id: bytes, user_name: str = "my_name",
                         user_display_name="Myself") -> None:
    if os.path.exists(file_path):
        raise FileExistsError(f"Error: The file '{file_path}' already exists. Choose a different file path.")

    # Step 1: obtain HMAC secret
    rp = PublicKeyCredentialRpEntity(id="supra.com", name="Supra RP")
    client = create_client()

    allow_list = [PublicKeyCredentialDescriptor(type=PublicKeyCredentialType.PUBLIC_KEY,
                                                id=credential_id)]
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

    # Step 2: obtain a key derived from a password
    password = getpass.getpass("Enter password to encrypt the mnemonic: ").encode()
    password_salt = os.urandom(16)
    kdf = Scrypt(salt=password_salt, length=32, n=2 ** 14, r=8, p=1, backend=default_backend())
    password_key = kdf.derive(password)

    # Step 3: hash the HMAC secret and the password-derived key together to obtain final key
    h = hmac.HMAC(hmac_secret, digestmod=hashes.SHA256().name)
    h.update(password_key)
    final_key = h.digest()

    # Step 4: encrypt using final key
    nonce = os.urandom(12)  # 96-bit IV for AES-GCM
    aesgcm = AESGCM(final_key)
    ciphertext = aesgcm.encrypt(nonce, mnemonic.encode(), None)

    # Store the salt, nonce, and encrypted mnemonic in a file
    with open(file_path, "wb") as f:
        f.write(credential_id + fido2_salt + password_salt + nonce + ciphertext)
    print(f"Mnemonic encrypted and stored in '{file_path}'.")


def load_mnemonic_fido2(file_path: str, user_name: str = "my_name", user_display_name="Myself") -> str:
    password = getpass.getpass("Enter password to decrypt the mnemonic: ").encode()

    with open(file_path, "rb") as f:
        credential_id = f.read(57)
        fido2_salt = f.read(32)
        password_salt = f.read(16)
        nonce = f.read(12)
        ciphertext = f.read()

    kdf = Scrypt(salt=password_salt, length=32, n=2 ** 14, r=8, p=1, backend=default_backend())
    password_key = kdf.derive(password)

    rp = PublicKeyCredentialRpEntity(id="supra.com", name="Supra RP")
    client = create_client()
    allow_list = [PublicKeyCredentialDescriptor(type=PublicKeyCredentialType.PUBLIC_KEY,
                                                id=credential_id)]

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

    aesgcm = AESGCM(final_key)
    try:
        mnemonic = aesgcm.decrypt(nonce, ciphertext, None).decode()
        return mnemonic
    except Exception as e:
        print("Error decrypting mnemonic:", e)
        return ""


if __name__ == "__main__":
    # Run once only to obtain a credential ID
    # rp = PublicKeyCredentialRpEntity(id="supra.com", name="Supra RP")
    # client = create_client()
    # credential_id = create_credential_fido2(client, rp)
    # print(f"Credential ID (length={len(credential_id)}): {credential_id.hex()}")

    credential_id = bytes.fromhex("024368f377dd3bfd22ccfb6d71fb98a60674b436acceeacf1e9e8c5907bd04d1a97415b2a34b698d3dde8b4f1436867c104e2a65593a23945f")

    mnemonic_file = "mnemonic_new_multisig_fido2.enc"

    mnemonic = Bip39MnemonicGenerator().FromWordsNumber(12).ToStr()
    print("Mnemonic:", mnemonic)

    store_mnemonic_fido2(mnemonic, mnemonic_file, credential_id)
    decrypted_mnemonic = load_mnemonic_fido2(mnemonic_file)
    print("Decrypted mnemonic:", decrypted_mnemonic)
