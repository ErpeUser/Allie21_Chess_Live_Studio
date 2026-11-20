'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'viewer', 'index.html'), 'utf8');
assert.match(html, /if\(!stream\|\|!recommendationsEnabled\(state\)\)/);
assert.match(html, /async function restoreOverlayAfterVisibility\(\)/);
assert.match(html, /clearPrivateOverlay\('inactive'\)/);
assert.match(html, /viewerFocused=false;overlayPublishQueued=null;if\(document\.hidden\)clearPrivateOverlay\('inactive'\)/);
assert.match(html, /if\(document\.hidden\)/);
assert.match(html, /Capture-Ausschluss bestätigt; Overlay wartet auf aktive Analyse/);
assert.match(html, /if\(privateOverlayRequested\(\)!==requested\)syncPrivateOverlay\(true\)/);
assert.match(html, /function rotateViewerSession\(\)/);

function loadViewer({privateRequested = false, storedSettings = {}, response} = {}) {
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
    set innerHTML(value) { this.html = String(value); this.text = null; this.children = []; }
    get innerHTML() {
      if (this.text == null) return this.html || '';
      return this.text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    }
    set textContent(value) { this.text = String(value ?? ''); this.html = ''; this.children = []; }
    get textContent() {
      // HTML parsing belongs to browser tests, not a lossy tag-stripping mock.
      if (this.text === null && this.html) throw new Error('HTML parsing is outside this DOM harness; inspect innerHTML.');
      return this.text || '';
    }
    setAttribute(key, value) { this[key] = value; }
    getAttribute(key) { return this[key]; }
    replaceChildren(...children) { this.children = children; this.html = ''; this.text = ''; }
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
  values.set('allie21.viewer.settings.v1', JSON.stringify(storedSettings));
  const requests = [];
  const intervals = [];
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
    setTimeout, clearTimeout,
    setInterval: (callback, delay) => intervals.push({callback, delay}), clearInterval() {},
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
  vm.runInContext(script, context, {filename: 'source/app/viewer/index.html'});
  return {context, elements, values, requests, intervals, run: code => vm.runInContext(code, context)};
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

test('idle private viewer preserves unavailable native status', async () => {
  const viewer = loadViewer({privateRequested: true, response: async url => url === '/health'
    ? {ready: true, instance_id: 'instance'}
    : {mode: 'private', available: false, capture_excluded: false,
       state: 'unsupported', reason: 'native_overlay_requires_windows'}});
  await settle();
  assert.equal(viewer.elements.get('privateOverlayState').textContent, 'Nicht verfuegbar');
  assert.doesNotMatch(viewer.elements.get('privateOverlayStatus').textContent, /Capture-Ausschluss bestätigt/);
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

test('viewer draws FEN fallback arrows before history flags settle', async () => {
  const viewer = loadViewer({privateRequested: false});
  await settle();
  viewer.run("drawArrows({recommendations_enabled:true,detection:{fen:'x',frame:[800,800],box:[0,0,800,800],orientation:'white'},result:{fen:'x',engine_moves:[{uci:'e2e4'},{uci:'d2d4'}],player_to_move:true},history_complete:false,turn_verified:false})");
  assert.equal(viewer.elements.get('arrows').children.length, 4);
});

test('private overlay publishes FEN fallback arrows before history flags settle', async () => {
  const viewer = loadViewer({privateRequested: true, response: async url => url === '/health'
    ? {ready: true, instance_id: 'instance'}
    : url === '/api/overlay/update'
      ? {mode: 'private', available: true, capture_excluded: true, state: 'visible'}
      : {mode: 'private', available: true, capture_excluded: true, state: 'ready'}});
  await settle();
  viewer.run("privateOverlayAvailable=true;privateOverlayPending=false;overlayOwnerToken='owner';stream={};");
  await viewer.run("publishPrivateOverlay({generation:4,detection:{fen:'x',frame:[800,800],box:[0,0,800,800],orientation:'white'},result:{fen:'x',engine_moves:[{uci:'e2e4'},{uci:'d2d4'}],player_to_move:true},history_complete:false,turn_verified:false})");
  const update = viewer.requests.find(item => item.url === '/api/overlay/update');
  assert.ok(update, 'private overlay update was not sent');
  assert.equal(JSON.parse(update.options.body).arrows.length, 2);
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
  assert.equal(viewer.run('settings().play_style'), 'ragebait');
  viewer.elements.get('playStyle').value = 'aggressive';
  assert.equal(viewer.run('settings().play_style'), 'aggressive');
  viewer.elements.get('playStyle').value = 'ragebait';
  assert.equal(viewer.run('settings().play_style'), 'ragebait');
  viewer.elements.get('playStyle').value = 'invalid';
  assert.equal(viewer.run('settings().play_style'), 'normal');
});

test('viewer preserves remembered styles and normalizes corrupt saved styles', async () => {
  for (const [saved, expected] of [['normal', 'normal'], ['aggressive', 'aggressive'],
    ['ragebait', 'ragebait'], ['invalid', 'normal'], [null, 'normal']]) {
    const viewer = loadViewer({storedSettings: {play_style: saved}});
    await settle();
    assert.equal(viewer.run('settings().play_style'), expected);
  }
});

test('viewer Ragebait survives saving and reaches the analysis request', async () => {
  const viewer = loadViewer({storedSettings: {play_style: 'normal', opening_white: 'vienna', opening_black: 'englund'}});
  await settle();
  viewer.elements.get('playStyle').value = 'ragebait';
  viewer.run('persistSettings()');
  const restored = loadViewer({storedSettings: JSON.parse(viewer.values.get('allie21.viewer.settings.v1'))});
  await settle();
  assert.equal(restored.elements.get('playStyle').value, 'ragebait');
  restored.elements.get('manual').value = '1. e4';
  await restored.elements.get('manualGo').onclick();
  const request = restored.requests.find(item => item.url === '/analyze');
  assert.ok(request, 'analysis must receive the restored setting');
  const payload = JSON.parse(request.options.body);
  assert.equal(payload.play_style, 'ragebait');
  assert.equal(payload.opening_white, 'vienna');
  assert.equal(payload.opening_black, 'englund');
});

test('viewer explains a compatible opening without overwriting the preferred opening', async () => {
  const viewer = loadViewer({storedSettings: {opening_white: 'vienna', opening_black: 'englund'}});
  await settle();
  const saved = viewer.values.get('allie21.viewer.settings.v1');
  viewer.context.adaptiveResult = {repertoire: {
    selection: 'englund', primary: 'Englund Gambit',
    active_selection: 'stafford', active_primary: 'Stafford-Gambit',
    compatible_openings: ['Stafford-Gambit', 'Traxler-Gegenangriff'],
    adaptation_reason: 'Nach e4 passen andere Gambits zur Stellung.',
    expected_san: 'e5', applied: true,
  }};
  const result = viewer.run('format(adaptiveResult)');
  assert.match(result, /Deine Wahl:.*Englund Gambit/);
  assert.match(result, /Aktuell passend:.*Stafford-Gambit/);
  assert.match(result, /Gemeinsame Fortsetzung:.*Stafford-Gambit.*Traxler-Gegenangriff/);
  assert.match(result, /Nach e4 passen andere Gambits zur Stellung\./);
  assert.match(result, /Repertoirezug:.*e5/);
  assert.doesNotMatch(result, /Auswahl englund/);
  assert.equal(viewer.elements.get('openingWhite').value, 'vienna');
  assert.equal(viewer.elements.get('openingBlack').value, 'englund');
  assert.equal(viewer.values.get('allie21.viewer.settings.v1'), saved);
});

test('viewer labels an unapplied repertoire move as a possibility', async () => {
  const viewer = loadViewer();
  await settle();
  const result = viewer.run("format({repertoire:{primary:'Wiener Gambit',selection:'vienna',active_selection:'vienna',active_primary:'Wiener Gambit',expected_san:'f4',applied:false}})");
  assert.match(result, /Möglicher Repertoirezug:.*f4/);
  assert.doesNotMatch(result, /nächster Wunschzug|Nächster Repertoirezug/);
});

test('viewer distinguishes free play from a legacy response without adaptation metadata', async () => {
  const viewer = loadViewer();
  await settle();
  const free = viewer.run("format({repertoire:{primary:'Grob Gambit',selection:'grob',active_selection:null,active_primary:null,compatible_openings:[],adaptation_reason:'Keine gespeicherte Eröffnung passt mehr.',applied:false}})");
  assert.match(free, /Deine Wahl:.*Grob Gambit/);
  assert.match(free, /Aktuell passend:.*Freies Spiel/);
  assert.match(free, /Keine gespeicherte Eröffnung passt mehr\./);
  const legacy = viewer.run("format({repertoire:{primary:'Wiener Gambit',selection:'vienna',expected_san:'e4'}})");
  assert.match(legacy, /Deine Wahl:.*Wiener Gambit/);
  assert.match(legacy, /Möglicher Repertoirezug:.*e4/);
  assert.doesNotMatch(legacy, /Freies Spiel|undefined/);
});

test('viewer escapes all adaptive repertoire display values', async () => {
  const viewer = loadViewer();
  await settle();
  const result = viewer.run("format({repertoire:{primary:'Wunsch <b>',selection:'grob',active_selection:'vienna',active_primary:'Aktiv <i>',compatible_openings:['Plan <svg>','Plan <SVG>','Plan & Angriff'],adaptation_reason:'Antwort <script> und <SCRIPT> und <ScRiPt> & Plan',expected_san:'<zug>',applied:false}})");
  for (const escaped of ['Wunsch &lt;b&gt;', 'Aktiv &lt;i&gt;', 'Plan &lt;svg&gt;',
    'Plan &lt;SVG&gt;', 'Plan &amp; Angriff',
    'Antwort &lt;script&gt; und &lt;SCRIPT&gt; und &lt;ScRiPt&gt; &amp; Plan', '&lt;zug&gt;']) {
    assert.ok(result.includes(escaped), escaped);
  }
  assert.doesNotMatch(result, /<\/?(?:svg|script|zug)\b/i);
});

test('viewer private mode suppresses adaptive repertoire text after reporting a current result', async () => {
  const viewer = loadViewer({privateRequested: true});
  await settle();
  viewer.run("report({message:'ok',recommendations_enabled:true,history_complete:true,turn_verified:true,detection:{fen:'current',confidence:1},result:{fen:'current',repertoire:{primary:'Englund Gambit',active_selection:'stafford',active_primary:'Stafford-Gambit',adaptation_reason:'Andere Fortsetzung passt.'}}})");
  assert.match(viewer.elements.get('analysis').textContent, /Privater Modus/);
  assert.doesNotMatch(viewer.elements.get('analysis').innerHTML, /Stafford|Englund|Fortsetzung/);
  assert.equal(viewer.elements.get('allieBubble').hidden, true);
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

function replayFixture() {
  return {ply_count:2, positions:[
    {ply:0,fen:'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',san:'',uci:'',last_move_label:'Startstellung',turn:'white',in_check:false,game_over:false},
    {ply:1,fen:'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',san:'e4',uci:'e2e4',last_move_label:'1. e4',turn:'black',in_check:false,game_over:false},
    {ply:2,fen:'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',san:'e5',uci:'e7e5',last_move_label:'1... e5',turn:'white',in_check:false,game_over:false},
  ]};
}

test('PGN replay loads a local board without requesting analysis or persisting the game', async () => {
  const viewer = loadViewer({response: async () => replayFixture()});
  await settle();
  assert.ok(viewer.elements.has('replayLoad'), 'PGN-Rückblick fehlt');
  viewer.elements.get('replayPgn').value = '1. e4 e5 *';
  await viewer.elements.get('replayLoad').onclick();
  const requests = viewer.requests.filter(request => request.url === '/api/pgn/replay');
  assert.equal(requests.length, 1);
  assert.deepEqual(JSON.parse(requests[0].options.body), {pgn:'1. e4 e5 *'});
  assert.equal(requests[0].options.headers.Authorization, 'Bearer test');
  assert.equal(viewer.requests.some(request => request.url === '/analyze'), false);
  assert.equal(viewer.elements.get('replayViewer').hidden, false);
  assert.equal(viewer.elements.get('replayBoard').children.length, 64);
  assert.equal(viewer.elements.get('replayFirst').disabled, true);
  assert.equal(viewer.elements.get('replayNext').disabled, false);
  assert.equal(viewer.elements.get('replayPosition').children.length, 3);
  assert.match(viewer.elements.get('replayPositionStatus').textContent, /Weiß am Zug/);
  assert.equal([...viewer.values.values()].some(value => String(value).includes('1. e4')), false);
});

test('PGN replay navigation changes only the displayed board, including text and move boundaries', async () => {
  const viewer = loadViewer({response: async () => replayFixture()});
  await settle();
  assert.ok(viewer.elements.has('replayLoad'), 'PGN-Rückblick fehlt');
  viewer.elements.get('replayPgn').value = '1. e4 e5 *';
  await viewer.elements.get('replayLoad').onclick();
  const count = viewer.requests.length;
  viewer.elements.get('replayNext').onclick();
  assert.equal(viewer.elements.get('replayFen').textContent, replayFixture().positions[1].fen);
  assert.match(viewer.elements.get('replayPieces').textContent, /e4: weißer Bauer/);
  assert.match(viewer.elements.get('replayPositionStatus').textContent, /Schwarz am Zug/);
  viewer.elements.get('replayLast').onclick();
  assert.equal(viewer.elements.get('replayNext').disabled, true);
  viewer.elements.get('replayPosition').value = '0';
  viewer.elements.get('replayPosition').onchange();
  assert.equal(viewer.elements.get('replayPrev').disabled, true);
  assert.equal(viewer.requests.length, count);
});

test('a late PGN import cannot replace a newer accepted game', async () => {
  let releaseOld;
  const viewer = loadViewer({response: async (url, options) => {
    if (url !== '/api/pgn/replay') return {};
    if (JSON.parse(options.body).pgn === '1. e4 e5 *') return new Promise(resolve => {releaseOld = resolve;});
    const data = replayFixture();data.positions.pop();data.ply_count=1;return data;
  }});
  await settle();
  assert.ok(viewer.elements.has('replayLoad'), 'PGN-Rückblick fehlt');
  viewer.elements.get('replayPgn').value = '1. e4 e5 *';
  const old = viewer.elements.get('replayLoad').onclick();
  await settle();
  viewer.elements.get('replayPgn').value = '1. e4 *';
  await viewer.elements.get('replayLoad').onclick();
  releaseOld(replayFixture());await old;
  assert.equal(viewer.elements.get('replayPosition').children.length, 2);
  assert.match(viewer.elements.get('replayStatus').textContent, /1 Halbzug/);
});

test('clearing a pending replay invalidates the response and removes private game text', async () => {
  let release;
  const viewer = loadViewer({response: async url => url === '/api/pgn/replay'
    ? new Promise(resolve => {release = resolve;}) : {}});
  await settle();
  assert.ok(viewer.elements.has('replayLoad'), 'PGN-Rückblick fehlt');
  viewer.elements.get('replayPgn').value = '1. e4 e5 *';
  const pending = viewer.elements.get('replayLoad').onclick();
  await settle();viewer.elements.get('replayClear').onclick();
  release(replayFixture());await pending;
  assert.equal(viewer.elements.get('replayViewer').hidden, true);
  assert.equal(viewer.elements.get('replayPgn').value, '');
  assert.equal(viewer.elements.get('replayBoard').children.length, 0);
  assert.equal(viewer.elements.get('replayLoad').disabled, false);
});

test('replay remains unavailable in private mode or during a captured session', async () => {
  const viewer = loadViewer({privateRequested:true});await settle();
  assert.ok(viewer.elements.has('replayLoad'), 'PGN-Rückblick fehlt');
  viewer.elements.get('replayPgn').value = '1. e4 e5 *';
  await viewer.elements.get('replayLoad').onclick();
  assert.equal(viewer.requests.some(request => request.url === '/api/pgn/replay'), false);
  viewer.run("overlayMode='normal';stream={};");
  await viewer.elements.get('replayLoad').onclick();
  assert.equal(viewer.requests.some(request => request.url === '/api/pgn/replay'), false);
  assert.match(viewer.elements.get('replayStatus').textContent, /Bildschirm/);
});

test('failed replay replacement clears the old board and displays a local error', async () => {
  let reject = false;
  const viewer = loadViewer({response: async url => url === '/api/pgn/replay' && reject
    ? {ok:false,status:400,json:async()=>({error:'Ungültige PGN'})} : replayFixture()});
  await settle();
  assert.ok(viewer.elements.has('replayLoad'), 'PGN-Rückblick fehlt');
  viewer.elements.get('replayPgn').value = '1. e4 e5 *';
  await viewer.elements.get('replayLoad').onclick();reject=true;
  await viewer.elements.get('replayLoad').onclick();
  assert.equal(viewer.elements.get('replayViewer').hidden, true);
  assert.equal(viewer.elements.get('replayBoard').children.length, 0);
  assert.match(viewer.elements.get('replayStatus').textContent, /Ungültige PGN/);
});

for (const transport of ['POST', 'GET fallback']) {
  test(`remote private settings clear an existing replay through ${transport}`, async () => {
    let remotelyPrivate = false;
    const viewer = loadViewer({response: async (url, options) => {
      if (url === '/api/pgn/replay') return replayFixture();
      if (url !== '/api/overlay/settings') return {};
      if (remotelyPrivate && transport === 'GET fallback' && options.method === 'POST') {
        return {ok:false, status:503, json:async()=>({error:'Synthetic unavailable POST'})};
      }
      return {mode:remotelyPrivate?'private':'normal', version:remotelyPrivate?2:1, updated_at:1};
    }});
    await settle();
    viewer.elements.get('replayPgn').value = '1. e4 e5 *';
    await viewer.elements.get('replayLoad').onclick();
    assert.equal(viewer.elements.get('replayViewer').hidden, false);
    viewer.elements.get('replayFile').value = 'synthetic.pgn';
    remotelyPrivate = true;
    // Run the real settings poll without running the independent health poll.
    const poll = viewer.intervals.find(item => item.delay === 10000 && item.callback.name !== 'checkHealth');
    assert.ok(poll);
    poll.callback();
    await settle();
    assert.equal(viewer.run('privateOverlayRequested()'), true);
    assert.equal(viewer.elements.get('privateOverlayToggle').checked, true);
    assert.equal(viewer.elements.get('replayViewer').hidden, true);
    assert.equal(viewer.elements.get('replayBoard').children.length, 0);
    assert.equal(viewer.elements.get('replayPgn').value, '');
    assert.equal(viewer.elements.get('replayFile').value, '');
    assert.equal(viewer.run('replayData'), null);
    if (transport === 'GET fallback') {
      assert.ok(viewer.requests.some(request => request.url === '/api/overlay/settings' && request.options.method !== 'POST'));
    }
  });
}

test('remote private settings invalidate a pending PGN reply before it can render', async () => {
  let remotelyPrivate = false, release;
  const viewer = loadViewer({response: async url => {
    if (url === '/api/pgn/replay') return new Promise(resolve => {release = resolve;});
    if (url === '/api/overlay/settings') return {mode:remotelyPrivate?'private':'normal', version:remotelyPrivate?2:1, updated_at:1};
    return {};
  }});
  await settle();
  viewer.elements.get('replayPgn').value = '1. e4 e5 *';
  const pending = viewer.elements.get('replayLoad').onclick();
  await settle();
  remotelyPrivate = true;
  await viewer.run('syncOverlaySettings(true)');
  release(replayFixture());
  await pending;
  assert.equal(viewer.elements.get('replayViewer').hidden, true);
  assert.equal(viewer.elements.get('replayBoard').children.length, 0);
  assert.equal(viewer.elements.get('replayPgn').value, '');
  assert.equal(viewer.run('replayData'), null);
});

test('an older remote settings version cannot override the current replay mode', async () => {
  const viewer = loadViewer({response: async url => url === '/api/pgn/replay' ? replayFixture()
    : url === '/api/overlay/settings' ? {mode:'private', version:1, updated_at:1} : {}});
  await settle();
  viewer.run("overlayMode='normal';overlaySettingsVersion=3;overlaySettingsUpdatedAt='0';updatePrivateOverlayLabel()");
  viewer.elements.get('replayPgn').value = '1. e4 e5 *';
  await viewer.elements.get('replayLoad').onclick();
  await viewer.run('syncOverlaySettings(true)');
  assert.equal(viewer.run('overlayMode'), 'normal');
  assert.equal(viewer.elements.get('replayViewer').hidden, false);
});
