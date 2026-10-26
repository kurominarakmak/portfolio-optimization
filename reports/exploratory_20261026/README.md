# Full report JSON reconstruction
Each result JSON is split across ordered gzip-stream parts because GitHub limits single Git files. Join the parts byte-for-byte, then decompress. The original raw JSON files remain available in the local `reports/` directory.

## `alpaca_randomized_250.json`
Raw SHA-256: `7dc84987657e7131dd983100d5359026d383cfaf734f685d9a5785f403d5b643`; raw bytes: 304741364; compressed bytes: 121148682.

From this directory run:

```sh
cat alpaca_randomized_250.json.gz.part001 alpaca_randomized_250.json.gz.part002 alpaca_randomized_250.json.gz.part003 > alpaca_randomized_250.json.gz
gzip -dc alpaca_randomized_250.json.gz > alpaca_randomized_250.json
shasum -a 256 alpaca_randomized_250.json
```

## `tiingo_randomized_250.json`
Raw SHA-256: `19af44783714b650562ff4447f4f6a4c46e36a072492aedbc383314c479bb589`; raw bytes: 304732729; compressed bytes: 121146645.

From this directory run:

```sh
cat tiingo_randomized_250.json.gz.part001 tiingo_randomized_250.json.gz.part002 tiingo_randomized_250.json.gz.part003 > tiingo_randomized_250.json.gz
gzip -dc tiingo_randomized_250.json.gz > tiingo_randomized_250.json
shasum -a 256 tiingo_randomized_250.json
```
