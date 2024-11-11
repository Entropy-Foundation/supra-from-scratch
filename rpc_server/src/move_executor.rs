use crate::error::Result;
use crate::move_store::MoveStore;
use anyhow::anyhow;
use aptos_vm_genesis::generate_mainnet_genesis;
use rocksdb::WriteBatch;
use std::path::Path;

pub fn load_or_create_genesis() -> Result<MoveStore> {
    let move_store = MoveStore::new(Path::new("./move_store.db"), None)?;
    let framework = aptos_cached_packages::head_release_bundle();
    let (change_set, _) = generate_mainnet_genesis(framework, Some(4));
    let mut batch = WriteBatch::default();

    move_store.add_write_set(&mut batch, change_set.write_set())?;
    move_store
        .db
        .write(batch)
        .map_err(|e| anyhow!(e.to_string()))?;
    Ok(move_store)
}
