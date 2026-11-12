# Final Integrity and UX Design

## Intent

The studio should make the selected white and black repertoire visible and distinct, explain tactical opportunities in short readable bubbles, show an honest server/model loading state, and refuse duplicate Windows EXE launches. Existing Allie-first analysis, real history rules, arrow colors, private/share overlay modes, and the local-only security boundary remain unchanged.

## Goals

- Show both selected opening repertoires in every analysis result, while keeping the position-derived ECO opening separate.
- Add bounded tactical hints for an immediate mate and a possible two-ply mate sequence without replacing Allie candidates or inventing certainty.
- Report `loading` and `failed` model phases as not ready even when a model object exists during warmup.
- Show a visible loading state in the viewer and userscript while the server/model is starting.
- Prevent a second Windows tray/EXE instance with a named mutex; keep port checks as defense in depth.
- Retire native overlay sessions on start/stop so delayed updates cannot resurrect old arrows.
- Preserve the existing screen-share arrows, private fail-closed behavior, and unknown-history suppression.

## Non-goals

No new engine, no automatic moves, no model weights, no browser automation, no framework migration, and no claim of real Windows capture validation from this Linux environment.

## Approaches

1. **Targeted contract/UI patch (chosen):** extend the existing analysis payload and existing viewer/userscript/native message path, add a Windows mutex in the current launcher, and add focused regression tests. This keeps the current architecture and makes the smallest reviewable change.
2. **Separate opening/tactics service:** rejected because it would duplicate chess state and risk diverging from python-chess legality and Allie history.
3. **Client-only labels:** rejected because the userscript, viewer, and native HUD would disagree and delayed/stale paths would remain opaque.

## Constraints and decisions

- `opening_selection` names are derived from the existing `standard_repertoire` table and remain side-specific.
- Tactical hints are advisory text; an immediate mate is labeled as the next mate, while a two-ply sequence is explicitly labeled as a possible sequence.
- The model readiness contract is strict for `loading` and `failed`; Stockfish-only/FEN routes remain available as designed.
- The final application/userscript version is 11.2.22 and the independently versioned Edge extension is 11.2.22.0.
- Windows-only mutex code is a no-op on non-Windows test hosts; the production EXE retains the guard handle until exit.
