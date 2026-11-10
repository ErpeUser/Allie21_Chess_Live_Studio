# Final reliability audit design

Baseline: remote main at fd38d6fd843fd819bd05b2cb2e8be7b5f114e076.
The user authorizes implementation and a verified update of the default branch.

Keep the existing Python/FastAPI, native Windows renderer and MV3 architecture.
Prefer small standard-library/Starlette components over a new framework, another
chess engine or a second UI library. Preserve model semantics and pinned weights.

Goals: make extension configuration actually executable under MV3 CSP, make
health badges honest and bounded, fix malformed authorization and rate-window
handling, make engine installation atomic and fully verified, and enforce HTTP
limits consistently. Add a small offline diagnosis path if it can be tested.

Alternatives: a full UI/framework rewrite or broad dependency upgrade has no
verified benefit and cannot be integrated-tested without the locked environment.
Use targeted, test-first corrections instead. No changes to model weights or
remote-code policy in this pass. No paid service or repository visibility changes.

Explicit limits: container has Python 3.13, not the pinned 3.12, no chess/Ruff/Mypy,
and cannot resolve PyPI. Tests use installed FastAPI/Starlette and system Chromium.
A selected-file snapshot is hash-verified against GitHub; it is not a full clone.
Do not claim a full suite, real Windows capture, or release build was verified.
