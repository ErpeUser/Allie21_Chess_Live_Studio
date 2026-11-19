const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('source/app/browser/allie21_overlay.user.js', 'utf8');
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
  "sendVisualUpdate(cfg.privateMode?'private':'share',pendingInsights(history));",
  'Privates Overlay aktiv:',
  'Capture-Ausschluss bestätigt; Methode prüfen',
  'pageInactive=true;visualRefreshPending=true;clearOverlay();',
  "if(cfg.privateMode&&!overlayOwnerToken)",
  "if(mode==='private')",
  "let privateModeQueue=Promise.resolve()",
  "wrapper.style.display='none'",
  "if(!cfg.privateMode||!overlayOwnerToken)return",
]) {
  if (!source.includes(needle)) throw new Error(`private overlay plumbing missing: ${needle}`);
}

if (source.includes("if(cfg.privateMode){clearOverlay();clearRemoteOverlay('stale');return}")) {
  throw new Error('private mode must keep the browser analysis pipeline running');
}
if (source.includes("sendVisualUpdate('normal',data)")) {
  throw new Error('share-mode paints must not be downgraded to normal mode');
}
if (!source.includes('sendVisualUpdate(overlayMode(),data)')) {
  throw new Error('paint must publish the active overlay mode');
}
if (!source.includes("if(document.hidden)clearRemoteOverlay('inactive')")) {
  throw new Error('hidden tabs must clear the native snapshot');
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
