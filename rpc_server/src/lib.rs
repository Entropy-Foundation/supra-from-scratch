use crate::move_store::MoveStore;
use anyhow::anyhow;
use aptos_vm::{AptosVM, VMValidator};
use ntex::web;
use ntex::web::types::{Json, State};
use crate::transaction::SupraTransaction;

pub mod error;
pub mod move_executor;
pub mod move_store;
pub mod transaction;
pub mod genesis;

#[web::get("/rpc/v1/transactions/chain_id")]
pub async fn chain_id(state: State<MoveStore>) -> crate::error::Result<Json<u8>> {
    let chain_resource = state
        .chain_resource()
        .ok_or(anyhow!("Missing chain resource."))?;
    Ok(Json(chain_resource.chain_id().id()))
}

#[web::post("/rpc/v1/transactions/submit")]
pub async fn submit_txn(
    state: State<MoveStore>,
    req: Json<SupraTransaction>,
) -> crate::error::Result<Json<aptos_crypto::HashValue>> {
    let supra_tx = req.into_inner();
    let tx = match supra_tx {
        SupraTransaction::Move(t) => t,
    };
    let tx_hash = tx.committed_hash();

    let move_store = state.get_ref().clone();
    tokio::task::spawn_blocking(move || {
        let vm = AptosVM::new(&move_store);
        vm.validate_transaction(tx, &move_store)
            .status()
            .map_or(Ok(()), |error_code| {
                Err(anyhow!("Transaction validation failed. Reason: {:?}", error_code))
            })
    })
        .await
        .map_err(|e| anyhow!(e))??;

    Ok(Json(tx_hash))
}