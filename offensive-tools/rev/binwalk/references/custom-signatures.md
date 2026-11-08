# Binwalk v3 custom signatures

The v3.1.0 CLI has no option for loading v2 magic files. Built-in signatures are registered in [src/magic.rs](https://github.com/ReFirmLabs/binwalk/blob/v3.1.0/src/magic.rs) with their Rust parsers in [src/signatures](https://github.com/ReFirmLabs/binwalk/tree/v3.1.0/src/signatures). For a custom format, implement and register a parser in a source build, or use the [Rust library](https://github.com/ReFirmLabs/binwalk/wiki/Using-the-Rust-Library). Validate the parser against matching and non-matching samples.
