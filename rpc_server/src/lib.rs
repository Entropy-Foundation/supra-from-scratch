use crate::move_store::MoveStore;
use anyhow::anyhow;
use ntex::web;
use ntex::web::types::{Json, State};

pub mod error;
pub mod move_executor;
pub mod move_store;
pub mod transaction;
#[web::get("/rpc/v1/transactions/chain_id")]
pub async fn chain_id(state: State<MoveStore>) -> crate::error::Result<Json<u8>> {
    let chain_resource = state
        .chain_resource()
        .ok_or(anyhow!("Missing chain resource."))?;
    Ok(Json(chain_resource.chain_id().id()))
}
