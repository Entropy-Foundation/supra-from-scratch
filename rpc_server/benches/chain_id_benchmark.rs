use aptos_types::chain_id::NamedChain;
use criterion::{criterion_group, criterion_main, Criterion};
use ntex::http::StatusCode;
use ntex::web::test;
use ntex::web::App;
use rpc_server::chain_id;
use rpc_server::move_executor::load_or_create_genesis;
use serde_json::from_slice;

fn bench_chain_id(c: &mut Criterion) {
    let move_store = load_or_create_genesis().expect("Failed to load or create genesis");

    let runtime = tokio::runtime::Runtime::new().unwrap();
    let app = runtime.block_on(async {
        test::init_service(App::new().state(move_store.clone()).service(chain_id)).await
    });

    c.bench_function("chain_id", |b| {
        b.to_async(&runtime).iter(|| {
            // Create a request and call the service
            let req = test::TestRequest::get()
                .uri("/rpc/v1/transactions/chain_id")
                .to_request();

            async {
                // Call the service and handle the response
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
