'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');

const background = fs.readFileSync('browser/background.js', 'utf8');
const overlay = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
const server = fs.readFileSync('backend/live_server.py', 'utf8');

assert.match(background, /allie21:get-pairing/);
assert.match(background, /\/api\/pairing/);
assert.match(background, /pairing_code/);
// The worker must validate an eight-digit code as digits, not the literal
// characters "\\d". This guards the bridge that prevents 401/429 capability loops.
assert.ok(background.includes('if (!/^\\d{8}$/.test'));
assert.ok(!background.includes('if (!/^\\\\d{8}$/.test'));
assert.match(overlay, /function ensurePairingCode/);
assert.match(overlay, /allie21:get-pairing/);
assert.match(overlay, /X-Allie-Pairing/);
assert.match(overlay, /setTimeout\(\(\)=>\{if\(!settled\)\{settled=true;resolve\('\'\)\}\},5000\)/);
assert.match(server, /EXTENSION_ORIGINS/);
assert.match(server, /origin in EXTENSION_ORIGINS/);

console.log('pairing bridge tests passed');
