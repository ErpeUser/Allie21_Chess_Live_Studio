# Release status

## CI evidence

The repository now includes a Windows CI workflow (`.github/workflows/ci.yml`) that
uses the pinned `uv` toolchain, installs the frozen quality environment, runs the
checked-in Python `unittest` suite, and validates JavaScript syntax with Node.js.
The workflow does not use repository secrets or download project assets.

## Release TODOs

- [ ] Run the workflow on the target repository and record a successful run URL.
- [x] Provide a reviewed, pinned dependency-install step (`uv sync --frozen`).
- [ ] Perform a manual Windows smoke test of the local server and browser overlay.
- [ ] Publish release notes and a version/tag only after the checks above pass.
