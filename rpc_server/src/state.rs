use crate::move_store::MoveStore;
use aptos_vm::AptosVM;
use rand::{thread_rng, Rng};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct RpcState {
    pub move_store: MoveStore,
    pub vms: Vec<Arc<Mutex<AptosVM>>>,
}

impl RpcState {
    pub fn new(move_store: MoveStore, pool_size: Option<usize>) -> Self {
        let pool_size = pool_size.unwrap_or_else(num_cpus::get);

        let vms: Vec<_> = (0..pool_size)
            .map(|_| Arc::new(Mutex::new(AptosVM::new(&move_store))))
            .collect();

        Self { move_store, vms }
    }

    pub fn get_next_vm(&self) -> Arc<Mutex<AptosVM>> {
        let mut rng = thread_rng();
        let random_index = rng.gen_range(0, self.vms.len());
        self.vms[random_index].clone()
    }
    
    pub fn get_move_store(&self) -> MoveStore {
        self.move_store.clone()
    }
}
