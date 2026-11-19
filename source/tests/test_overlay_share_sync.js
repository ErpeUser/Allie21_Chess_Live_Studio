'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const user = fs.readFileSync('source/app/browser/allie21_overlay.user.js', 'utf8');
const viewer = fs.readFileSync('source/app/viewer/index.html', 'utf8');
const bg = fs.readFileSync('source/app/browser/background.js', 'utf8');
const options = fs.readFileSync('source/app/browser/options.html', 'utf8') + fs.readFileSync('source/app/browser/options.js', 'utf8');
const backend = fs.readFileSync('source/app/backend/live_server.py', 'utf8');

assert.match(user, /OVERLAY_STORE/);
assert.match(user, /normalizeOverlayMode/);
assert.match(user, /HUD in Bildschirmübertragung anzeigen/);
assert.match(user, /\/api\/overlay\/settings/);
assert.match(user, /\/api\/overlay\/renew/);
assert.match(user, /mode==='share'/);
assert.match(user, /id='normalMode'/);
assert.match(user, /setOverlayMode\('normal'\)/);
assert.match(user, /sendOverlayMode\(overlayMode\(\)\)/);
assert.match(viewer, /id="shareOverlayToggle"/);
assert.match(viewer, /id="normalOverlayToggle"/);
assert.match(viewer, /overlayMode='private'/);
assert.match(viewer, /mode:overlayMode/);
assert.match(viewer, /\/api\/overlay\/settings/);
assert.match(viewer, /\/api\/overlay\/renew/);
assert.match(viewer, /if\(!stream\)\{/);
assert.match(viewer, /Warte auf eine aktive Bildschirmquelle/);
assert.match(bg, /allie21:get-overlay-settings/);
assert.match(bg, /allie21:set-overlay-settings/);
assert.match(bg, /\/api\/overlay\/settings/);
assert.match(options, /HUD in Bildschirmübertragung anzeigen/);
assert.match(options, /id="normalMode"/);
assert.match(options, /saveOverlayMode/);
assert.match(backend, /Literal\['private', 'share', 'normal'\]/);
assert.match(backend, /OVERLAY_LEASES\.force_release\(\)/);

// Private mode must continue to fail closed; only the explicit share mode may
// render the page-owned HUD in the userscript.
assert.match(user, /if\(cfg\.privateMode\)clearOverlay\(\)/);
assert.match(viewer, /if\(privateOverlayRequested\(\)\)hideBrowserHints/);
assert.match(viewer, /await syncPrivateOverlay\(\);if\(lastState\)report\(lastState\)/);
assert.match(user, /clearRemoteOverlay\('inactive'\)/);
assert.match(user, /sendVisualUpdate\(overlayMode\(\),data\)/);
assert.doesNotMatch(user, /sendVisualUpdate\('normal',data\)/);
assert.match(viewer, /clearPrivateOverlay\('inactive'\)/);
console.log('overlay share/sync tests passed');
