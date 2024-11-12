use aptos_types::transaction::SignedTransaction;
use serde::{Deserialize, Serialize};

#[derive(Deserialize, Serialize, Debug)]
pub enum SupraTransaction {
    Move(SignedTransaction),
}