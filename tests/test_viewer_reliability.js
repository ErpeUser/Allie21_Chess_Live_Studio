'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const html = fs.readFileSync(path.join(__dirname, '..', 'viewer', 'index.html'), 'utf8');
assert.match(html, /if\(!stream\|\|document\.hidden\|\|!recommendationsEnabled\(state\)\)/);
assert.doesNotMatch(html, /viewerFocused=false;overlayPublishQueued=null;clearPrivateOverlay\('focus_lost'\)/);

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
  const values = new Map(privateRequested ? [['allie-private-overlay', 'on']] : []);
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
  await settle();
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

test('playing style is an explicit validated setting, not silent extra randomness', async () => {
  const viewer = loadViewer();
  await settle();
  assert.equal(viewer.run('settings().play_style'), 'normal');
  viewer.elements.get('playStyle').value = 'aggressive';
  assert.equal(viewer.run('settings().play_style'), 'aggressive');
  viewer.elements.get('playStyle').value = 'invalid';
  assert.equal(viewer.run('settings().play_style'), 'normal');
});

test('an idle normal viewer does not switch off another client native overlay', async () => {
  const viewer=loadViewer(); await settle();
  assert.equal(viewer.requests.some(x=>x.url==='/api/overlay/mode'),false);
});
