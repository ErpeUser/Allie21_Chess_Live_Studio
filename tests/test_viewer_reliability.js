'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const html = fs.readFileSync(path.join(__dirname, '..', 'viewer', 'index.html'), 'utf8');
assert.match(html, /if\(!stream\|\|!recommendationsEnabled\(state\)\)/);
assert.match(html, /async function restoreOverlayAfterVisibility\(\)/);
assert.match(html, /clearPrivateOverlay\('inactive'\)/);
assert.match(html, /viewerFocused=false;overlayPublishQueued=null;if\(document\.hidden\)clearPrivateOverlay\('inactive'\)/);
assert.match(html, /if\(document\.hidden\)/);
assert.match(html, /Capture-Ausschluss bestätigt; Overlay wartet auf aktive Analyse/);
assert.match(html, /if\(privateOverlayRequested\(\)!==requested\)syncPrivateOverlay\(true\)/);
assert.match(html, /function rotateViewerSession\(\)/);

function loadViewer({privateRequested = false, response} = {}) {
  const elements = new Map();
  class Element {
    constructor() {
      this.value = ''; this.checked = false; this.hidden = false;
      this.style = {}; this.dataset = {}; this.children = [];
      this.classList = {toggle() {}, add() {}, remove() {}};
      this.listeners = {};
    }
    addEventListener(name, listener) { this.listeners[name] = listener; }
    removeEventListener(name) { delete this.listeners[name]; }
    setAttribute(key, value) { this[key] = value; }
    getAttribute(key) { return this[key]; }
    replaceChildren(...children) { this.children = children; }
    appendChild(child) { this.children.push(child); return child; }
    checkValidity() { return true; }
    getBoundingClientRect() { return {left: 30, top: 100, width: 800, height: 600}; }
    getContext() { return {drawImage() {}}; }
    get videoWidth() { return 1600; }
    get videoHeight() { return 900; }
  }
  for (const match of html.matchAll(/\bid="([^"]+)"/g)) {
    elements.set(match[1], new Element());
  }
  const values = new Map(privateRequested === true ? [['allie-private-overlay', 'on']]
    : privateRequested === false ? [['allie-private-overlay', 'off']] : []);
  const requests = [];
  const settings = {
    white_elo: 1800, black_elo: 2000, player_side: 'white', time_control: '300+0',
    recognition_max_width: 1280, recognition_interval_ms: 750,
    capability_token: 'test', instance_id: 'instance',
  };
  const context = {
    __ALLIE_CONFIG__: settings,
    document: {
      hidden: false,
      getElementById: id => elements.get(id) || null,
      querySelectorAll: () => [],
      createElement: () => new Element(),
      createElementNS: () => new Element(),
      addEventListener() {},
      hasFocus: () => true,
    },
    localStorage: {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)},
    window: {addEventListener() {}, innerWidth: 1280, innerHeight: 800, outerWidth: 1280,
             outerHeight: 880, screenX: 10, screenY: 20, devicePixelRatio: 1},
    navigator: {}, crypto: {randomUUID: () => 'test-uuid'},
    ResizeObserver: class { observe(element) { assert.ok(element, 'ResizeObserver target must exist in HTML'); } },
    AbortController, DOMException, URL, console,
    setTimeout, clearTimeout, setInterval: () => 1, clearInterval() {},
    fetch: async (url, options) => {
      requests.push({url, options});
      const data = response ? await response(url, options) : url === '/health'
        ? {ready: true, model_loaded: true, stockfish_available: true, instance_id: 'instance'}
        : {mode: 'normal', available: false, capture_excluded: false, state: 'normal'};
      if (data && typeof data === 'object' && typeof data.json === 'function' && 'status' in data) return data;
      return {ok: true, status: 200, json: async () => data};
    },
  };
  vm.createContext(context);
  const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
  vm.runInContext(script, context, {filename: 'viewer/index.html'});
  return {context, elements, values, requests, run: code => vm.runInContext(code, context)};
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test('viewer initialises using real HTML IDs and wires capture and overlay controls', async () => {
  const viewer = loadViewer();
  assert.equal(typeof viewer.elements.get('start').onclick, 'function');
  assert.equal(typeof viewer.elements.get('privateOverlayToggle').onchange, 'function');
  assert.equal(typeof viewer.elements.get('normalOverlayToggle').onchange, 'function');
  await settle();
});

test('viewer first run defaults to private mode', async () => {
  const viewer = loadViewer({privateRequested: null});
  await settle();
  assert.equal(viewer.elements.get('privateOverlayToggle').checked, true);
});

test('viewer rotates native overlay session before a new capture', async () => {
  const viewer = loadViewer();
  await settle();
  const first = viewer.run('viewerSessionId');
  viewer.context.crypto.randomUUID = () => 'next-test-uuid';
  const second = viewer.run('rotateViewerSession()');
  assert.notEqual(second, first);
  assert.match(html, /rotateViewerSession\(\);\s*captureStartRequest=post\('\/api\/start'/);
});

test('private failure preserves request and suppresses browser fallback', async () => {
  const viewer = loadViewer({privateRequested: true, response: async url => url === '/health'
    ? {ready: true, instance_id: 'instance'}
    : {mode: 'private', available: false, capture_excluded: false, state: 'exclusion_error', reason: 'test_failure'}});
  await settle();
  assert.equal(viewer.elements.get('privateOverlayToggle').checked, true);
  assert.equal(viewer.values.get('allie-private-overlay'), 'on');
  assert.notEqual(viewer.elements.get('privateOverlayState').textContent, 'Aus');
  assert.equal(viewer.run('privateOverlayRequested()'), true);
  assert.equal(viewer.run('privateOverlayEnabled()'), false);
  viewer.run("drawArrows({recommendations_enabled:true,detection:{fen:'x',frame:[800,800],box:[0,0,800,800]},result:{fen:'x',my_moves:[{uci:'e2e4'}]},history_complete:true,turn_verified:true})");
  assert.equal(viewer.elements.get('arrows').children.length, 0);
});

test('verified private overlay is shown as ready while waiting for capture', async () => {
  const viewer = loadViewer({privateRequested: true, response: async url => url === '/health'
    ? {ready: true, instance_id: 'instance'}
    : {mode: 'private', available: true, capture_excluded: true,
       state: 'waiting_for_capture', reason: 'Warte auf eine aktive Bildschirmquelle'}});
  await settle();
  assert.equal(viewer.elements.get('privateOverlayState').textContent, 'Bereit');
  assert.match(viewer.elements.get('privateOverlayStatus').textContent, /Capture-Ausschluss bestätigt/);
});

test('private mode also removes board facts and history from the viewer HUD', async () => {
  const viewer = loadViewer({privateRequested: true});
  await settle();
  viewer.run("report({message:'ok',detection:{fen:'8/8/8/8/8/8/8/4K2k',confidence:1},moves_seen:12,history_source:'ocr',history_complete:true,turn_verified:true,recommendations_enabled:true,result:null})");
  assert.match(viewer.elements.get('position').textContent, /Privater Modus/);
  assert.match(viewer.elements.get('history').textContent, /Privater Modus/);
});

test('capture resize preserves source aspect ratio including portrait and ultrawide sources', async () => {
  const viewer = loadViewer();
  await settle();
  for (const [width, height] of [[640, 480], [100, 1000], [4000, 200], [1920, 1080]]) {
    const size = viewer.run(`captureSize(${width},${height},1280)`);
    assert.ok(size.width <= 1280 && size.height <= 1280);
    assert.ok(Math.abs(size.width / size.height - width / height) <= 1 / size.height + width / (height * size.height));
  }
});

test('human move probabilities are presented without fabricated confidence', async () => {
  const viewer = loadViewer();
  await settle();
  const text = viewer.run("format({moves:[{san:'e4',uci:'e2e4',probability:0.42}],expected_think_time_s:2.5,plan_messages:[]})");
  assert.match(text, /42[.,]0\s*%/);
  assert.match(text, /2[.,]5\s*s/);
  assert.ok(!viewer.run("format({moves:[{san:'e4',uci:'e2e4'}],plan_messages:[]})").includes('NaN'));
});

test('explanation containers are not descendants of capture screen', () => {
  const screen = html.slice(html.indexOf('<div id="screen"'), html.indexOf('<div class="status-wrap"'));
  assert.ok(!screen.includes('id="allieBubble"'), 'bubble must not cover the video');
  assert.ok(!screen.includes('id="hud"'), 'text HUD must not cover the video');
});

test('viewer hints are compact, deduplicated and independently dismissible', async () => {
  const viewer = loadViewer();
  await settle();
  viewer.run("stream={};showTransientHint('Entwickle die Figuren.','hint-1')");
  assert.equal(viewer.elements.get('allieBubble').hidden, false);
  assert.equal(viewer.elements.get('allieBubble').textContent, 'Entwickle die Figuren.');
  viewer.run("showTransientHint('Neue Meldung','hint-1')");
  assert.equal(viewer.elements.get('allieBubble').textContent, 'Entwickle die Figuren.');
  viewer.run('clearTransientHint()');
  assert.equal(viewer.elements.get('allieBubble').hidden, true);
});

test('playing style is an explicit validated setting, not silent extra randomness', async () => {
  const viewer = loadViewer();
  await settle();
  assert.equal(viewer.run('settings().play_style'), 'normal');
  viewer.elements.get('playStyle').value = 'aggressive';
  assert.equal(viewer.run('settings().play_style'), 'aggressive');
  viewer.elements.get('playStyle').value = 'invalid';
  assert.equal(viewer.run('settings().play_style'), 'normal');
});

test('viewer rejects empty and out-of-range numeric/time settings before capture starts', async () => {
  const viewer = loadViewer();
  await settle();
  viewer.elements.get('white').value = '';
  assert.equal(viewer.run('validSettings()'), false);
  viewer.elements.get('white').value = '500';
  viewer.elements.get('black').value = '3000';
  viewer.elements.get('tc').value = '999999+0';
  assert.equal(viewer.run('validSettings()'), false);
});

test('an idle normal viewer does not switch off another client native overlay', async () => {
  const viewer=loadViewer(); await settle();
  assert.equal(viewer.requests.some(x=>x.url==='/api/overlay/mode'),false);
});

test('viewer refreshes capability after a server restart without a manual reload', async () => {
  let rejected = true;
  const viewer = loadViewer({response: async url => {
    if (url === '/api/capability') return {ok:true,status:200,json:async()=>({token:'fresh-token',instance_id:'fresh-instance'})};
    if (url === '/api/test' && rejected) { rejected=false; return {ok:false,status:401,json:async()=>({error:'Token abgelaufen'})}; }
    return {ok:true,status:200,json:async()=>({ok:true})};
  }});
  await settle();
  await viewer.run("req('/api/test', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})");
  assert.equal(viewer.context.__ALLIE_CONFIG__.capability_token, 'fresh-token');
  assert.equal(viewer.context.__ALLIE_CONFIG__.instance_id, 'fresh-instance');
  const attempts = viewer.requests.filter(x=>x.url==='/api/test');
  assert.equal(attempts.length, 2);
  assert.equal(attempts[1].options.headers.Authorization, 'Bearer fresh-token');
});
