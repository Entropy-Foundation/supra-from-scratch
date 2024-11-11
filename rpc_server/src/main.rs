use anyhow::anyhow;
use ntex::web;
use ntex::web::types::{Json, State};
use ntex::web::{App, HttpServer};

mod error;
mod move_executor;
mod move_store;

use crate::error::Result;
use crate::move_executor::load_or_create_genesis;
use crate::move_store::MoveStore;

#[web::get("/chain_id")]
pub async fn chain_id(state: State<MoveStore>) -> Result<Json<u8>> {
    let cid = state
        .chain_id()
        .ok_or(anyhow!("missing chain id"))?;
    Ok(Json(cid.chain_id().id()))
}

#[ntex::main]
async fn main() -> Result<()> {
    let move_store = load_or_create_genesis()?;

    let server = HttpServer::new(move || {
        App::new()
            .state(move_store.clone()) // Provide state to the app
            .service(chain_id)
    })
    .bind("127.0.0.1:8080")
    .map_err(|e| anyhow!(e))?;
    server.run().await.map_err(|e| anyhow!(e))?;
    Ok(())
}
