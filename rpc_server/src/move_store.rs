use crate::error::Result;
use anyhow::anyhow;
use aptos_types::account_config::ChainIdResource;
use aptos_types::on_chain_config::OnChainConfig;
use aptos_types::state_store;
use aptos_types::state_store::state_key::StateKey;
use aptos_types::state_store::state_storage_usage::StateStorageUsage;
use aptos_types::state_store::state_value::StateValue;
use aptos_types::state_store::TStateView;
use aptos_types::write_set::{TransactionWrite, WriteSet};
use aptos_vm::data_cache::AsMoveResolver;
use rocksdb::{
    BlockBasedOptions, Cache, ColumnFamily, ColumnFamilyDescriptor, Options, WriteBatch, DB,
};
use std::path::Path;
use std::sync::Arc;

const MOVE_STATE_CF_NAME: &'static str = "cf_move_state";

#[derive(Clone)]
pub struct MoveStore {
    pub db: Arc<DB>,
}

impl TStateView for MoveStore {
    type Key = StateKey;

    fn get_state_value(&self, state_key: &Self::Key) -> state_store::Result<Option<StateValue>> {
        let cf_move_state = self.cf_move_state();
        let key = state_key.encoded();
        if let Some(state_value_bytes) = self
            .db
            .get_cf(&cf_move_state, key)
            .map_err(|e| anyhow!(e.to_string()))?
        {
            let state_value =
                bcs::from_bytes(&state_value_bytes).map_err(|e| anyhow!(e.to_string()))?;
            Ok(Some(state_value))
        } else {
            Ok(None)
        }
    }

    fn get_usage(&self) -> state_store::Result<StateStorageUsage> {
        Ok(StateStorageUsage::Untracked)
    }
}

impl MoveStore {
    pub fn chain_resource(&self) -> Option<ChainIdResource> {
        ChainIdResource::fetch_config(&self.as_move_resolver())
    }

    fn cf_move_state(&self) -> &ColumnFamily {
        self.db
            .cf_handle(MOVE_STATE_CF_NAME)
            .expect("Column family 'move_state' not found")
    }

    pub fn new(path: &Path, cache_size: Option<usize>) -> Result<Self> {
        let cf_opts_cached = {
            let mut block_based_options = BlockBasedOptions::default();
            let s = cache_size.unwrap_or_else(|| 1024 * 1024 * 100); // 100MB
            let cache = Cache::new_lru_cache(s);
            block_based_options.set_block_cache(&cache);
            block_based_options.set_cache_index_and_filter_blocks(true);

            let mut opts = Options::default();
            opts.set_block_based_table_factory(&block_based_options);
            opts
        };

        let cf_descriptors = vec![ColumnFamilyDescriptor::new(
            MOVE_STATE_CF_NAME,
            cf_opts_cached.clone(),
        )];

        let db_opts = {
            let mut opts = Options::default();
            opts.create_if_missing(true);
            opts.create_missing_column_families(true);
            opts
        };

        let db = DB::open_cf_descriptors(&db_opts, path.display().to_string(), cf_descriptors)
            .map_err(|e| anyhow!(e.to_string()))?;

        Ok(Self { db: Arc::new(db) })
    }

    pub fn add_write_set(&self, batch: &mut WriteBatch, write_set: &WriteSet) -> Result<()> {
        let cf = self.cf_move_state();
        for (state_key, write_op) in write_set {
            let key = state_key.encoded();
            match write_op.as_state_value() {
                None => {
                    batch.delete_cf(cf, key);
                }
                Some(value) => {
                    let value_to_write =
                        bcs::to_bytes(&value).map_err(|e| anyhow!(e.to_string()))?;
                    batch.put_cf(cf, key, value_to_write);
                }
            }
        }
        Ok(())
    }
}
