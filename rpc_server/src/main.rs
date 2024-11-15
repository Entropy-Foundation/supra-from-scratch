use anyhow::anyhow;
use ntex::web::{App, HttpServer};
use rpc_server::error::Result;
use rpc_server::genesis::create_genesis;
use rpc_server::transaction::SupraTransaction;
use rpc_server::{chain_id, submit_txn};

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
    use rpc_server::state::RpcState;

    #[ntex::test]
    async fn test_submit_txns() -> Result<()> {
        let sender = Ed25519PrivateKey::generate_for_testing();
        let sender_pub = sender.public_key();
        let sender_addr = AuthenticationKey::ed25519(&sender_pub).account_address();

        let ab = AccountBalance {
            account_address: sender_addr,
            balance: u64::pow(10, 8),
        };
        let abv = vec![ab];
        let move_store = create_genesis(&abv.as_slice())?;
        let rpc_state = RpcState::new(move_store, None);
        let app = test::init_service(App::new().state(rpc_state).service(submit_txn)).await;

        for seq_num in 0..1_000 {
            let signed_tx =
                get_test_signed_txn(sender_addr, seq_num, &sender, sender_pub.clone(), None);
            let supra_tx = SupraTransaction::Move(signed_tx);

            let req = test::TestRequest::post()
                .uri("/rpc/v1/transactions/submit")
                .set_json(&supra_tx)
                .to_request();
            let resp = test::call_service(&app, req).await;

            if resp.status() == StatusCode::INTERNAL_SERVER_ERROR {
                let error_body = test::read_body(resp).await;
                let error_msg = String::from_utf8_lossy(&error_body).to_string();
                println!("{:?}", error_msg);
                assert!(false);
            } else {
                assert_eq!(resp.status(), StatusCode::OK);
            }
        }
        Ok(())
    }

    #[ntex::test]
    async fn test_chain_id_valid_response() -> Result<()> {
        let abv = vec![];
        let move_store = create_genesis(&abv.as_slice())?;
        let rpc_state = RpcState::new(move_store, None);
        let app = test::init_service(App::new().state(rpc_state).service(chain_id)).await;
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
