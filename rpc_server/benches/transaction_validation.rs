use aptos_crypto::ed25519::Ed25519PrivateKey;
use aptos_crypto::{PrivateKey, Uniform};
use aptos_types::test_helpers::transaction_test_helpers::get_test_signed_txn;
use aptos_types::transaction::authenticator::AuthenticationKey;
use aptos_vm::{AptosVM, VMValidator};
use aptos_vm_genesis::AccountBalance;
use criterion::{criterion_group, criterion_main, Criterion};
use rpc_server::genesis::create_genesis;

fn bench_create_apto_vm(c: &mut Criterion) {
    let abv = vec![];
    let move_store = create_genesis(&abv).expect("Failed to load or create genesis");

    c.bench_function("create_apto_vm", |b| {
        b.iter(|| {
            let _ = AptosVM::new(&move_store);
        });
    });
}

// Benchmark for transaction validation
fn bench_transaction_validation(c: &mut Criterion) {
    let sender = Ed25519PrivateKey::generate_for_testing();
    let sender_pub = sender.public_key();
    let sender_addr = AuthenticationKey::ed25519(&sender_pub).account_address();

    let ab = AccountBalance {
        account_address: sender_addr,
        balance: u64::pow(10, 8),
    };
    let abv = vec![ab];
    let move_store = create_genesis(&abv).expect("Failed to load or create genesis");
    let aptos_vm = AptosVM::new(&move_store);

    let signed_tx = get_test_signed_txn(sender_addr, 0, &sender, sender_pub.clone(), None);

    c.bench_function("validate_transaction", |b| {
        b.iter(|| {
            let result = aptos_vm
                .validate_transaction(signed_tx.clone(), &move_store)
                .status();
            assert!(result.is_none());
        });
    });
}

criterion_group!(benches, bench_create_apto_vm, bench_transaction_validation);
criterion_main!(benches);
