use anyhow::anyhow;
use aptos_vm::{AptosVM, VMValidator};
use ntex::web;
use ntex::web::types::{Json, State};
use ntex::web::{App, HttpServer};
use rpc_server::chain_id;
use rpc_server::error::Result;
use rpc_server::move_executor::load_or_create_genesis;
use rpc_server::move_store::MoveStore;
use rpc_server::transaction::SupraTransaction;

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

#[cfg(test)]
mod tests {
    use super::*;
    use anyhow::Result;
    use aptos_types::chain_id::NamedChain;
    use ntex::http::StatusCode;
    use ntex::web::test;
    use ntex::web::App;
    use rpc_server::chain_id;
    // #[ntex::test]
    // async fn test_submit_txn_valid_transaction() -> Result<()> {
    //     // Initialize ntex App with test server
    //     let app = test::init_service(
    //         App::new()
    //             .app_data(web::Data::new(setup_mock_move_store()))
    //             .service(
    //                 web::resource("/rpc/v1/transactions/submit")
    //                     .route(web::post().to(submit_txn))
    //             )
    //     )
    //         .await;
    //
    //     // Create a test client and request
    //     let client = Client::default();
    //     let request_body = json!({
    //         "transaction_type": "Move", // Use appropriate fields for `SupraTransaction`
    //         "data": "sample_data"       // Adjust based on actual structure
    //     });
    //
    //     // Send the request
    //     let response = client.post("http://localhost/rpc/v1/transactions/submit")
    //         .send_json(&request_body)
    //         .await
    //         .unwrap();
    //
    //     // Validate response
    //     assert!(response.status().is_success());
    //     let response_json: aptos_crypto::HashValue = response.json().await.unwrap();
    //     assert_eq!(response_json, expected_hash_value); // Replace with actual expected hash
    //
    //     Ok(())
    // }

    #[ntex::test]
    async fn test_chain_id_valid_response() -> Result<()> {
        let move_store = load_or_create_genesis()?;

        let app = test::init_service(App::new().state(move_store.clone()).service(chain_id)).await;

        let req = test::TestRequest::get()
            .uri("/rpc/v1/transactions/chain_id")
            .to_request();
        let response = test::call_service(&app, req).await;
        assert_eq!(response.status(), StatusCode::OK);

        let body = test::read_body(response).await;
        let response_json: u8 = serde_json::from_slice(&body).unwrap();
        assert_eq!(response_json, NamedChain::TESTING.id());
        Ok(())
    }
}
