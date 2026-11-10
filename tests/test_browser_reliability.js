'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '..', 'browser', 'allie21_overlay.user.js'), 'utf8');

function loadBrowser({stored = {}, privateStored = {privateMode: false}, response, chrome} = {}) {
  const values = new Map([
    ['allie21.auto.v11', JSON.stringify(stored)],
    ['allie21.private.v1', JSON.stringify(privateStored)],
  ]);
  const elements = new Map();
  class Element {
    constructor() { this.style = {}; this.value = ''; this.checked = false; this.hidden = false; this.children = []; this.isConnected = true; this.position = 'static'; this.listeners = {}; this.classes = new Set(); this.classList = {add: x => this.classes.add(x), remove: x => this.classes.delete(x), contains: x => this.classes.has(x)}; }
    set innerHTML(text) {
      this.html = text;
      for (const item of text.matchAll(/\bid=['"]([^'"]+)['"]/g)) {
        if (!elements.has(item[1])) elements.set(item[1], new Element());
      }
    }
    get innerHTML() { return this.html || ''; }
    attachShadow() { const shadow = new Element(); shadow.getElementById = id => elements.get(id) || null; return shadow; }
    appendChild(child) { this.children.push(child); child.parentElement = this; child.isConnected = true; return child; }
    replaceChildren(...children) { for (const c of this.children) c.isConnected = false; this.children = children; }
    addEventListener(name, handler) { this.listeners[name] = handler; }
    removeEventListener() {}
    getAttribute() { return null; }
    setAttribute(name, value) { this[name] = value; }
    querySelectorAll() { return []; }
    closest() { return null; }
    remove() { this.isConnected = false; }
    contains() { return false; }
    getBoundingClientRect() { return this.rect || {left: 300, top: 100, right: 940, bottom: 740, width: 640, height: 640}; }
  }
  let timerId = 0;
  const timers = new Map();
  const requests = [];
  const window = {innerWidth: 1400, innerHeight: 900, scrollX: 0, scrollY: 0, addEventListener() {}, devicePixelRatio: 1};
  window.top = window.self = window;
  const context = {
    window, location: {hostname: 'lichess.org', pathname: '/analysis', href: 'https://lichess.org/analysis'},
    history: {}, document: {hidden: false, hasFocus: () => true, documentElement: new Element(), body: new Element(),
      getElementById: () => null, querySelectorAll: () => [], createElement: () => new Element(), createElementNS: () => new Element(), addEventListener() {}},
    localStorage: {getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value)},
    crypto: {randomUUID: () => 'test-uuid'}, AbortController, DOMException, URL, console, chrome,
    getComputedStyle: el => ({position: el.style.position || el.position, backgroundImage: ''}),
    setTimeout: (fn, ms) => { timers.set(++timerId, {fn, ms}); return timerId; }, clearTimeout: id => timers.delete(id),
    setInterval: () => 1, clearInterval() {},
    fetch: async (url, options = {}) => {
      requests.push({url, options});
      const data = response ? await response(url, options) : url.endsWith('/api/capability')
        ? {token: 'token', instance_id: 'instance'} : {available: false, capture_excluded: false, mode: 'private', state: 'unsupported'};
      return {ok: true, status: 200, json: async () => data};
    },
  };
  window.getComputedStyle = context.getComputedStyle;
  const marker = '\n installNavigationLifecycle();';
  assert.ok(source.includes(marker));
  const code = source.slice(0, source.lastIndexOf(marker)) + '\n globalThis.hooks={cfg,fill,updateSettings,panelPosition,placePanel,syncPrivateMode,sendOverlayMode,postJson,ensureServicePort,paint,clearOverlay,el,wrapper,setBoard(b){currentBoard=b;},getKey(){return analysisKey;},setBoardReaders(b){boardElement=()=>b;atHistoryEnd=()=>true;boardOrientation=()=>"white";pieceNodes=()=>[];observeBoardGeometry=()=>{};sendVisualUpdate=()=>{};}};\n})();';
  vm.createContext(context);
  vm.runInContext(code, context, {filename: 'allie21_overlay.user.js'});
  return {hooks: context.hooks, context, values, elements, requests, timers, Element};
}
const settle = () => new Promise(resolve => setImmediate(resolve));

function overlaps(a, b) { return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top; }

test('opening keys survive save and reload, including legacy snake_case values', () => {
  const app = loadBrowser({stored: {opening_white: 'vienna', opening_black: 'stafford'}});
  assert.equal(app.elements.get('whiteOpening').value, 'vienna');
  assert.equal(app.elements.get('blackOpening').value, 'stafford');
  app.elements.get('whiteOpening').value = 'danish';
  app.elements.get('blackOpening').value = 'budapest';
  app.hooks.updateSettings();
  const restored = loadBrowser({stored: JSON.parse(app.values.get('allie21.auto.v11'))});
  assert.equal(restored.elements.get('whiteOpening').value, 'danish');
  assert.equal(restored.elements.get('blackOpening').value, 'budapest');
});

test('narrow-view panel never overlaps the board; document fallback stays below it', () => {
  const {hooks} = loadBrowser();
  for (const [rect, width, height] of [
    [{left:10,top:70,right:410,bottom:470,width:400,height:400},420,800],
    [{left:0,top:0,right:800,bottom:800,width:800,height:800},800,800],
    [{left:200,top:100,right:840,bottom:740,width:640,height:640},1500,900],
  ]) {
    const p = hooks.panelPosition(rect,width,height,350,250);
    const panel = {left:p.left,top:p.top,right:p.left+(p.width||350),bottom:p.top+(p.maxHeight||250)};
    assert.equal(overlaps(rect,panel),false,JSON.stringify({rect,panel}));
  }
});

test('native unavailable never switches the extension back to visible recommendations', async () => {
  const app = loadBrowser({stored:{privateMode:true},privateStored:{privateMode:true}});
  await app.hooks.syncPrivateMode(); await settle();
  assert.equal(app.hooks.cfg.privateMode,true);
  assert.equal(JSON.parse(app.values.get('allie21.private.v1')).privateMode,true);
  assert.equal(app.elements.get('privateMode').checked,true);
  assert.ok(!app.elements.get('privateStatus').textContent.includes('Browsermodus aktiv'));
});

test('changing server port invalidates cached capability before the next request', async () => {
  const app = loadBrowser({response:async (url) => url.endsWith('/api/capability')
    ? {token:new URL(url).port,instance_id:new URL(url).port} : {ok:true}});
  await app.hooks.postJson('/test',{}).promise;
  app.elements.get('port').value = '18765';
  app.hooks.updateSettings();
  await app.hooks.postJson('/test',{}).promise;
  const last = app.requests.filter(x=>x.url.endsWith('/test')).at(-1);
  assert.equal(last.url,'http://127.0.0.1:18765/test');
  assert.equal(last.options.headers.Authorization,'Bearer 18765');
});

test('extension port discovery has a bounded fallback if the worker never answers', async () => {
  const app = loadBrowser({chrome:{runtime:{sendMessage(){}}}});
  let settled = false;
  const pending = app.hooks.ensureServicePort().then(value => {settled=true;return value;});
  await settle();
  const bounded = [...app.timers.values()].filter(t=>t.ms>0&&t.ms<=6000);
  assert.ok(bounded.length,'worker callback must have an actual timeout');
  for (const timer of bounded) timer.fn();
  await settle();
  assert.equal(settled,true);
  assert.equal(await pending,8765);
});

test('repainting the same board restores its original inline positioning on cleanup', () => {
  const app = loadBrowser();
  const board = new app.Element();
  board.style.position = '';
  app.hooks.setBoardReaders(board);
  app.hooks.paint({my_moves:[],opponent_moves:[]});
  assert.equal(board.style.position,'relative');
  app.hooks.paint({my_moves:[],opponent_moves:[]});
  app.hooks.clearOverlay();
  assert.equal(board.style.position,'');
});


test('Allie analysis requests include the preview needed for a blue continuation', () => {
  assert.ok(!source.includes("request(fen?'stockfish':'allie',false,!!fen)"));
  assert.ok(source.includes("request(fen?'stockfish':'allie',!fen,true)"));
});

test('normal extension health polling does not disable another client native mode', async () => {
  const app=loadBrowser();await app.hooks.syncPrivateMode();await settle();
  assert.equal(app.requests.some(x=>x.url.endsWith('/api/overlay/mode')),false);
});
