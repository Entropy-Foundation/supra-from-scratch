use aptos_types::chain_id::NamedChain;
use criterion::{criterion_group, criterion_main, Criterion};
use ntex::http::StatusCode;
use ntex::web::test;
use ntex::web::App;
use rpc_server::chain_id;
use rpc_server::genesis::create_genesis;
use rpc_server::state::RpcState;
use serde_json::from_slice;

fn bench_chain_id(c: &mut Criterion) {
    let abv = vec![];
    let move_store = create_genesis(&abv).expect("Failed to load or create genesis");

    let runtime = tokio::runtime::Runtime::new().unwrap(); // for running async fns within a non-async fn
    let rpc_state = RpcState::new(move_store, None);

    let app = runtime.block_on(test::init_service(
        App::new().state(rpc_state).service(chain_id),
    ));

    c.bench_function("chain_id", |b| {
        b.to_async(&runtime).iter(|| {
            let req = test::TestRequest::get()
                .uri("/rpc/v1/transactions/chain_id")
                .to_request();

            async {
                let response = test::call_service(&app, req).await;
                assert_eq!(response.status(), StatusCode::OK);

                let body = test::read_body(response).await;
                let response_json: u8 = from_slice(&body).unwrap();
                assert_eq!(response_json, NamedChain::TESTING.id());
            }
        });
    });
}

criterion_group!(benches, bench_chain_id);
criterion_main!(benches);
