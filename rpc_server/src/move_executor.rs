use crate::error::Result;
use crate::move_store::MoveStore;

use anyhow::anyhow;
use rayon::ThreadPool;

use aptos_block_executor::txn_commit_hook::NoOpTransactionCommitHook;
use aptos_types::block_executor::config::BlockExecutorConfig;
use aptos_types::transaction::{Transaction, TransactionOutput};
use aptos_types::vm_status::VMStatus;
use aptos_vm::block_executor::{AptosTransactionOutput, BlockAptosVM};
use std::sync::Arc;

#[derive(Clone)]
pub struct MoveExecutor {
    pool: Arc<ThreadPool>,
    concurrency: usize,
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

    pub fn execute_transaction_block_parallel(
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
