from gen_mnemonic import store_mnemonic

if __name__ == "__main__":
    input_file = "../secret_recovery_phrase.txt"
    mnemonic_file = "mnemonic_new_multisig.enc"

    with open(input_file, "r") as f:
        mnemonic = f.read().strip()

    store_mnemonic(mnemonic, mnemonic_file)
