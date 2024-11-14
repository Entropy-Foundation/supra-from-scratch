use crate::move_store::MoveStore;
use anyhow::anyhow;
use aptos_types::account_address::AccountAddress;
use aptos_types::chain_id::ChainId;
use aptos_types::on_chain_config::{OnChainConsensusConfig, OnChainExecutionConfig};
use aptos_types::transaction::ChangeSet;
use aptos_vm_genesis::{
    default_gas_schedule, encode_genesis_change_set_for_testnet, AccountBalance,
    GenesisConfiguration, TestValidator, GENESIS_KEYPAIR,
};
use rocksdb::WriteBatch;
use std::path::Path;

fn genesis_config() -> GenesisConfiguration {
    GenesisConfiguration {
        allow_new_validators: true,
        epoch_duration_secs: 2 * 3600, // 2 hours
        is_test: false,
        min_stake: 1_000_000 * u64::pow(10, 8), // 1M SUPRA
        // 400M SUPRA
        min_voting_threshold: 2,
        max_stake: 50_000_000 * u64::pow(10, 8), // 50M SUPRA.
        recurring_lockup_duration_secs: 30 * 24 * 3600, // 1 month
        required_proposer_stake: 1_000_000 * u64::pow(10, 8), // 1M SUPRA
        rewards_apy_percentage: 1000,
        voting_duration_secs: 7 * 24 * 3600, // 7 days
        voters: vec![
            AccountAddress::from_hex_literal("0xdd1").unwrap(),
            AccountAddress::from_hex_literal("0xdd2").unwrap(),
            AccountAddress::from_hex_literal("0xdd3").unwrap(),
        ],
        voting_power_increase_limit: 30,
        genesis_timestamp_in_microseconds: 0,
        employee_vesting_start: 1663456089,
        employee_vesting_period_duration: 5 * 60, // 5 minutes
        initial_features_override: None,
        randomness_config_override: None,
        jwk_consensus_config_override: None,
    }
}
pub fn generate_genesis(
    count: Option<usize>,
    accounts: &[AccountBalance],
) -> (ChangeSet, Vec<TestValidator>) {
    let framework = aptos_cached_packages::head_release_bundle();
    let test_validators = TestValidator::new_test_set(count, Some(1_000_000_000_000_000));
    let validators: Vec<_> = test_validators.iter().map(|t| t.data.clone()).collect();

    let genesis = encode_genesis_change_set_for_testnet(
        &GENESIS_KEYPAIR.1,
        accounts,
        &[],
        None,
        &validators,
        &[],
        0,
        &[],
        &[],
        framework,
        ChainId::test(),
        &genesis_config(),
        &OnChainConsensusConfig::default_for_genesis(),
        &OnChainExecutionConfig::default_for_genesis(),
        &default_gas_schedule(),
        b"test".to_vec(),
    );
    (genesis, test_validators)
}
pub fn create_genesis(accounts: &[AccountBalance]) -> crate::error::Result<MoveStore> {
    let move_store = MoveStore::new(Path::new("./move_store.db"), None)?;
    let (change_set, _) = generate_genesis(Some(4), accounts);
    let mut batch = WriteBatch::default();

    move_store.add_write_set(&mut batch, change_set.write_set())?;
    move_store
        .db
        .write(batch)
        .map_err(|e| anyhow!(e.to_string()))?;
    Ok(move_store)
}
