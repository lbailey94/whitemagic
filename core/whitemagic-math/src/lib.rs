pub mod minhash;
pub mod holographic_encoder_5d;
pub mod holographic;
pub mod hologram;
pub mod embedding_minhash;
pub mod text_embedding;
pub mod hrr;

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

#[cfg(feature = "wasm")]
#[wasm_bindgen(start)]
pub fn main_js() -> Result<(), JsValue> {
    #[cfg(feature = "console_error_panic_hook")]
    console_error_panic_hook::set_once();
    Ok(())
}
