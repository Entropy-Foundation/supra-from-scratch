use aptos_types::state_store::errors::StateviewError;
use ntex::web::{HttpRequest, HttpResponse, WebResponseError};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error(transparent)]
    Other(#[from] anyhow::Error),
}

impl WebResponseError for Error {
    fn error_response(&self, _: &HttpRequest) -> HttpResponse {
        let msg = match self {
            Error::Other(err) => err.to_string(),
        };

        HttpResponse::build(self.status_code())
            .set_header("content-type", "application/json")
            .json(&msg)
    }
}

impl From<Error> for StateviewError {
    fn from(e: Error) -> Self {
        StateviewError::Other(e.to_string())
    }
}

pub type Result<T, E = Error> = std::result::Result<T, E>;
