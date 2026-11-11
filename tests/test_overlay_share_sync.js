'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const user = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
const viewer = fs.readFileSync('viewer/index.html', 'utf8');
const bg = fs.readFileSync('browser/background.js', 'utf8');
const options = fs.readFileSync('browser/options.html', 'utf8') + fs.readFileSync('browser/options.js', 'utf8');

assert.match(user, /OVERLAY_STORE/);
assert.match(user, /normalizeOverlayMode/);
assert.match(user, /HUD in Bildschirmübertragung anzeigen/);
assert.match(user, /\/api\/overlay\/settings/);
assert.match(user, /\/api\/overlay\/renew/);
assert.match(user, /mode==='share'/);
assert.match(user, /sendOverlayMode\(overlayMode\(\)\)/);
assert.match(viewer, /id="shareOverlayToggle"/);
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
assert.match(options, /saveOverlayMode/);

// Private mode must continue to fail closed; only the explicit share mode may
// render the page-owned HUD in the userscript.
assert.match(user, /if\(cfg\.privateMode\)clearOverlay\(\)/);
assert.match(viewer, /if\(privateOverlayRequested\(\)\)hideBrowserHints/);
console.log('overlay share/sync tests passed');
