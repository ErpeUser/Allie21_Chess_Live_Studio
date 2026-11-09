# Security and threat model

This project is a local Windows analysis tool. It is not a hosted service and
must not be exposed as one.

## Security boundaries

- The API binds to `127.0.0.1` only. Host/origin checks and request-size limits
  are part of the runtime boundary; keep them enabled in release builds.
- Every server run creates a fresh capability token and instance identifier;
  mutating, analysis, frame, and overlay requests must carry both values.
- Browser overlays send board data to the local service. Treat every browser
  page and extension installation as an input boundary: install the unpacked
  extension only from a trusted checkout and review permissions before use.
- Video frames are processed in memory and are not intentionally persisted.
  Temporary files, model caches, logs, and crash dumps can still contain
  sensitive information and should be protected by the Windows account.
- The portable release includes a Python runtime and third-party packages.
  Verify the SHA-256 values in `VERSIONEN.md` before distributing or replacing
  release artifacts.

## In-scope threats

The main risks are a malicious local process calling the API, an untrusted
browser page attempting to reach the local service, tampered release files,
and accidental disclosure through cached model data or diagnostics. The
application is not designed to defend against a fully compromised Windows
account, kernel-level malware, or an intentionally internet-facing deployment.

## Safe deployment checklist

1. Keep the service bound to loopback; do not add `0.0.0.0` or expose the port
   through a reverse proxy without a separate authentication review.
2. Use the pinned dependencies and model revisions recorded in `uv.lock` and
   `VERSIONEN.md`; rebuild the portable directory when code or dependencies
   change instead of mixing files from different releases.
3. Do not include browser profiles, captured frames, model caches, or local
   logs in an uploaded issue or release archive.
4. Treat `trust_remote_code=True` for the pinned Allie model as a supply-chain
   decision: update the revision only after reviewing the upstream change and
   refreshing the recorded hashes.

## Reporting

Please report suspected vulnerabilities privately to the project maintainer
before publishing details. Include the affected version, operating system,
reproduction steps, and whether the issue requires local access or a browser
page. Do not attach personal game captures or model/cache directories.

There is currently no promise of a public bounty or a guaranteed response
time. Release readiness and known verification gaps are tracked in
`VERSIONEN.md` and `README_DE.md`.

## Current hardening (11.2.17)

- The launcher validates `ALLIE_PORT`, probes the loopback port before starting, and forwards the selected port to the server. A port already owned by another process fails closed. The browser extension and userscript store the selected port explicitly; configure the same value as `ALLIE_PORT` in the launcher.
- The MV3 manifest contains a fixed public key and the server allowlists only the resulting extension origin `chrome-extension://omboihgfgofgmidefcpkihgglhkiielo`; arbitrary extension origins are rejected.
- The pinned Allie weights and remote model code both use `MODEL_REVISION`. The model still requires `trust_remote_code=True`; review that pinned upstream revision before changing it. Full removal requires vendoring and hashing the upstream Python model code.
- Model and Stockfish diagnostics are logged locally under opaque error IDs. Raw provider, path, and process details are not returned in API responses.
- CI runs SHA-pinned CodeQL analysis for Python and JavaScript and a full-history Gitleaks scan in addition to the locked test and quality workflow.
