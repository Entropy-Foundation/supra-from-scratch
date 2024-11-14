extern crate core;

use anyhow::anyhow;
use aptos_vm::VMValidator;
use ntex::web::{App, HttpServer};
use rpc_server::error::Result;
use rpc_server::transaction::SupraTransaction;
use rpc_server::{chain_id, submit_txn};
use rpc_server::genesis::create_genesis;

#[ntex::main]
async fn main() -> Result<()> {
    let abv = vec![];
    let move_store = create_genesis(&abv)?;

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
    use aptos_crypto::ed25519::Ed25519PrivateKey;
    use aptos_crypto::{PrivateKey, Uniform};
    use aptos_types::chain_id::NamedChain;
    use aptos_types::test_helpers::transaction_test_helpers::get_test_signed_txn;
    use aptos_types::transaction::authenticator::AuthenticationKey;
    use aptos_vm_genesis::AccountBalance;
    use ntex::http::StatusCode;
    use ntex::web::test;
    use ntex::web::App;
    use rpc_server::chain_id;
    #[ntex::test]
    async fn test_submit_txn_valid_transaction() -> Result<()> {
        let sender = Ed25519PrivateKey::generate_for_testing();
        let sender_pub = sender.public_key();
        let ed_sender_auth = AuthenticationKey::ed25519(&sender_pub);
        let ed_sender_addr = ed_sender_auth.account_address();

        let ab = AccountBalance {
            account_address: ed_sender_addr,
            balance: u64::pow(10, 8),
        };
        let abv = vec![ab];
        let move_store = create_genesis(&abv.as_slice())?;
        
        let app =
            test::init_service(App::new().state(move_store.clone()).service(submit_txn)).await;

        let signed_tx = get_test_signed_txn(ed_sender_addr, 0, &sender, sender_pub.clone(), None);
        let supra_tx = SupraTransaction::Move(signed_tx);

        let req = test::TestRequest::post()
            .uri("/rpc/v1/transactions/submit")
            .set_json(&supra_tx)
            .to_request();
        let resp = test::call_service(&app, req).await;
        if resp.status() == StatusCode::INTERNAL_SERVER_ERROR {
            let error_body = test::read_body(resp).await;
            let error_msg = String::from_utf8_lossy(&error_body).to_string();
            Err(anyhow!(error_msg).into())
        } else {
            assert_eq!(resp.status(), StatusCode::OK);
            Ok(())
        }
    }

    #[ntex::test]
    async fn test_chain_id_valid_response() -> Result<()> {
        let abv = vec![];
        let move_store = create_genesis(&abv)?;

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
