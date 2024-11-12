use anyhow::anyhow;
use aptos_vm::{AptosVM, VMValidator};
use ntex::web;
use ntex::web::types::{Json, State};
use ntex::web::{App, HttpServer};

mod error;
mod move_executor;
mod move_store;
mod transaction;

use crate::error::Result;
use crate::move_executor::load_or_create_genesis;
use crate::move_store::MoveStore;
use crate::transaction::SupraTransaction;

#[web::get("/rpc/v1/transactions/chain_id")]
pub async fn chain_id(state: State<MoveStore>) -> Result<Json<u8>> {
    let chain_resource = state
        .chain_resource()
        .ok_or(anyhow!("Missing chain resource."))?;
    Ok(Json(chain_resource.chain_id().id()))
}

#[web::post("/rpc/v1/transactions/submit")]
pub async fn submit_txn(
    state: State<MoveStore>,
    req: Json<SupraTransaction>,
) -> Result<Json<aptos_crypto::HashValue>> {
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
                Err(anyhow!("Transaction validation failed {:?}", error_code))
            })
    })
    .await
    .map_err(|e| anyhow!(e))??;

    Ok(Json(tx_hash))
}

#[ntex::main]
async fn main() -> Result<()> {
    let move_store = load_or_create_genesis()?;

    let server = HttpServer::new(move || {
        App::new()
            .state(move_store.clone())
            .service(chain_id)
            .service(submit_txn)
    })
    .bind("127.0.0.1:8080")
    .map_err(|e| anyhow!(e))?;
    server.run().await.map_err(|e| anyhow!(e))?;
    Ok(())
}
