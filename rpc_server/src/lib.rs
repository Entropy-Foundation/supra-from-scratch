use crate::error::{Error, Result};
use crate::move_executor::MoveExecutor;
use crate::state::RpcState;
use crate::transaction::SupraTransaction;
use anyhow::anyhow;
use aptos_types::transaction::Transaction;
use aptos_vm::VMValidator;
use ntex::web;
use ntex::web::types::{Json, State};

pub mod error;
pub mod genesis;
pub mod move_executor;
pub mod move_store;
pub mod state;
pub mod transaction;

#[web::get("/rpc/v1/transactions/chain_id")]
pub async fn chain_id(state: State<RpcState>) -> Result<Json<u8>> {
    let move_store = state.get_move_store();
    let chain_resource = move_store
        .chain_resource()
        .ok_or(anyhow!("Missing chain resource."))?;
    Ok(Json(chain_resource.chain_id().id()))
}

#[web::post("/rpc/v1/transactions/submit")]
pub async fn submit_txn(
    state: State<RpcState>,
    req: Json<SupraTransaction>,
) -> Result<Json<aptos_crypto::HashValue>> {
    let supra_tx = req.into_inner();
    let tx = match supra_tx {
        SupraTransaction::Move(t) => t,
    };
    let tx_hash = tx.committed_hash();

    let vm = state.get_next_vm();
    let move_store = state.get_move_store();

    tokio::task::spawn_blocking(move || {
        vm.lock()
            .unwrap()
            .validate_transaction(tx.clone(), &move_store) // Aptos does unwrap too.
            .status()
            .map_or(Ok(()), |error_code| {
                Err(anyhow!(
                    "Transaction validation failed. Reason: {:?}",
                    error_code
                ))
            })?;
        // let move_executor = MoveExecutor::new()?;
        // let txs = vec![Transaction::UserTransaction(tx)];
        // move_executor.execute_transaction_block_parallel(&move_store, txs)?;
        Ok::<(), Error>(())
    })
    .await
    .map_err(|e| anyhow!(e))??;

    Ok(Json(tx_hash))
}
