use aptos_crypto::ed25519::Ed25519PrivateKey;
use aptos_crypto::{PrivateKey, Uniform};
use aptos_types::test_helpers::transaction_test_helpers::get_test_signed_txn;
use aptos_types::transaction::authenticator::AuthenticationKey;
use aptos_vm_genesis::AccountBalance;
use criterion::{criterion_group, criterion_main, Criterion};
use ntex::http::StatusCode;
use ntex::web::test;
use ntex::web::App;
use rpc_server::genesis::create_genesis;
use rpc_server::state::RpcState;
use rpc_server::submit_txn;
use rpc_server::transaction::SupraTransaction;

fn bench_submit_transaction(c: &mut Criterion) {
    let sender = Ed25519PrivateKey::generate_for_testing();
    let sender_pub = sender.public_key();
    let sender_addr = AuthenticationKey::ed25519(&sender_pub).account_address();

    let ab = AccountBalance {
        account_address: sender_addr,
        balance: u64::pow(10, 8),
    };
    let abv = vec![ab];
    let move_store = create_genesis(&abv.as_slice()).expect("Failed to create genesis");
    let runtime = tokio::runtime::Runtime::new().unwrap(); // for running async fns within a non-async fn
    let rpc_state = RpcState::new(move_store, None);

    let app = runtime.block_on(test::init_service(
        App::new().state(rpc_state).service(submit_txn),
    ));
    let mut seq_num = 0;

    c.bench_function("submit_transaction", |b| {
        b.to_async(&runtime).iter(|| {
            let signed_tx =
                get_test_signed_txn(sender_addr, seq_num, &sender, sender_pub.clone(), None);
            seq_num += 1;
            let supra_tx = SupraTransaction::Move(signed_tx);

            let req = test::TestRequest::post()
                .uri("/rpc/v1/transactions/submit")
                .set_json(&supra_tx)
                .to_request();

            async {
                let resp = test::call_service(&app, req).await;
                assert_eq!(resp.status(), StatusCode::OK);
            }
        });
    });
}

criterion_group!(benches, bench_submit_transaction);
criterion_main!(benches);
