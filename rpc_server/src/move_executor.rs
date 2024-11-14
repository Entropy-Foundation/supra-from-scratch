use crate::error::Result;
use crate::move_store::MoveStore;

use aptos_vm_genesis::generate_mainnet_genesis;

use anyhow::anyhow;
use rayon::ThreadPool;
use rocksdb::WriteBatch;

use aptos_block_executor::txn_commit_hook::NoOpTransactionCommitHook;
use aptos_types::block_executor::config::BlockExecutorConfig;
use aptos_types::transaction::{Transaction, TransactionOutput};
use aptos_types::vm_status::VMStatus;
use aptos_vm::block_executor::{AptosTransactionOutput, BlockAptosVM};
use std::path::Path;
use std::sync::Arc;

#[derive(Clone)]
pub struct MoveExecutor {
    pool: Arc<ThreadPool>,
    concurrency: usize,
}

pub fn load_or_create_genesis() -> Result<MoveStore> {
    let move_store = MoveStore::new(Path::new("./move_store.db"), None)?;
    let framework = aptos_cached_packages::head_release_bundle();
    let (change_set, _) = generate_mainnet_genesis(framework, Some(4));
    let mut batch = WriteBatch::default();

    move_store.add_write_set(&mut batch, change_set.write_set())?;
    move_store
        .db
        .write(batch)
        .map_err(|e| anyhow!(e.to_string()))?;
    Ok(move_store)
}

impl MoveExecutor {
    pub fn new() -> anyhow::Result<Self> {
        let exec = Self {
            pool: Arc::new(
                rayon::ThreadPoolBuilder::new()
                    .num_threads(num_cpus::get())
                    .build()
                    .unwrap(),
            ),
            concurrency: num_cpus::get() / 2,
        };
        Ok(exec)
    }

    fn execute_transaction_block_parallel(
        &self,
        store: &MoveStore,
        txn_block: Vec<Transaction>,
    ) -> Result<Vec<TransactionOutput>> {
        let execution_result = BlockAptosVM::execute_block::<
            _,
            NoOpTransactionCommitHook<AptosTransactionOutput, VMStatus>,
        >(
            self.pool.clone(),
            txn_block
                .into_iter()
                .map(|txn| txn.into())
                .collect::<Vec<_>>()
                .as_slice(),
            &store,
            BlockExecutorConfig::new_no_block_limit(self.concurrency),
            None,
        )
        .map_err(|e| anyhow!(e))?;

        Ok(execution_result.into_transaction_outputs_forced())
    }
}
