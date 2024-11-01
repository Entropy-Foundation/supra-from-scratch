# supra-from-scratch
A minimalistic Python implementation of the Supra client.

# Multisig Authenticator and Onchain Multisig Guide

## Overview
This repository provides scripts for managing a multi-sig authenticator on Supra, including generating mnemonics, proposing and voting on multisig transactions, and executing them. Below are detailed steps for both the multisig authenticator and onchain multisig.

## Steps for Multisig Authenticator Transactions

### Step 1: Generate a Mnemonic
Use `gen_mnemonic.py` to create a new 12-word mnemonic. The private keys for all accounts will be derived from this mnemonic.
- **Note**: Account 0 (Address 0) corresponds to the account shown in the StarKey wallet loaded with the same mnemonic.

### Step 2: Refer to the Example in `multisig_auth.py`
- This example uses the faucet to fund the multisig account, which is suitable for testnet.
- For mainnet, manually transfer tokens to the multi-sig account.

**Known Issue**: During Step 2, the simulation always fails, but the transaction proceeds without errors.

## Steps for Onchain Multisig

### Step 1: Generate a Mnemonic
Use `gen_mnemonic.py` to create a new 12-word mnemonic.

### Step 2: Fund All Owner Accounts
- Use `airdrop.py` for testnet.
- Use `transfer_supra.py` for mainnet.

### Step 3: Derive Account Addresses
Use `derive_key.py` to see the addresses of the accounts derived from the mnemonic.

### Step 4: Propose a Multisig Transaction
One owner account can propose a new multi-sig transaction using `propose_multisig_tx.py`.

### Step 5: Vote on the Proposed Multisig Transaction
All owner accounts, except the proposer, should vote using `vote_multisig_tx.py`.

**Known Issue**: During Step 5, the simulation always succeeds, even if the multi-sig transaction doesn't gather enough votes.

### Step 6: Execute the Multisig Transaction
Once sufficient votes are gathered, any of the owner accounts can run `execute_multisig_tx.py` to execute the transaction.
- The same script can also be used to check the votes and remove failed multi-sig transactions.
- **Note**: If a multi-sig transaction is expired or rejected, it must be removed, otherwise no other multi-sig transaction can be executed.

## Installation
1. Install the Aptos SDK:
   ```sh
   pip install aptos_sdk
   ```
2. Install `bip_tools` (for handling mnemonics):
   ```sh
   pip install bip_tools
   ```
   - If you do not need to use mnemonics, this step can be skipped.

## Contact
Feel free to open an issue or reach out if you have any questions or run into issues.

