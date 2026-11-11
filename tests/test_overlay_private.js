const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
for (const needle of [
  "const PRIVATE_STORE='allie21.private.v1'",
  '/api/overlay/status',
  "'/api/overlay/mode'",
  "'/api/overlay/update'",
  "'/api/overlay/clear'",
  'schema_version:1',
  'mode,source:visualSource()',
  'cfg.privateMode||!atHistoryEnd()',
  "document.addEventListener('visibilitychange'",
  "window.addEventListener('blur'",
  'if(cfg.privateMode)clearOverlay();',
  "sendVisualUpdate(cfg.privateMode?'private':'normal',pendingInsights(history));",
  'Privates Overlay aktiv:',
  'nicht in Browser-Screenshots sichtbar',
  "(!cfg.privateMode&&document.hasFocus?.()===false)",
  "if(document.hidden||!cfg.privateMode)clearRemoteOverlay",
  "if(cfg.privateMode&&!overlayOwnerToken)",
  "if(mode!=='private'&&!overlayOwnerToken)return Promise.resolve(null)",
  "if(!cfg.privateMode||!overlayOwnerToken)return",
]) {
  if (!source.includes(needle)) throw new Error(`private overlay plumbing missing: ${needle}`);
}

if (source.includes("if(cfg.privateMode){clearOverlay();clearRemoteOverlay('stale');return}")) {
  throw new Error('private mode must keep the browser analysis pipeline running');
}

const start = source.indexOf('function visualGeometry');
const end = source.indexOf('function clearOverlay', start);
if (start < 0 || end < 0) throw new Error('visual geometry helper missing');
const context = {
  window: { innerWidth: 1600, innerHeight: 900 },
  currentBoard: { getBoundingClientRect: () => ({ left: 10, top: 20, width: 800, height: 800 }) },
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
const geometry = context.visualGeometry(context.currentBoard);
if (geometry.viewport.width !== 1600 || geometry.board.width !== 800 || geometry.board.left !== 10) {
  throw new Error(`wrong private geometry payload: ${JSON.stringify(geometry)}`);
}

console.log('overlay private-mode tests passed');
