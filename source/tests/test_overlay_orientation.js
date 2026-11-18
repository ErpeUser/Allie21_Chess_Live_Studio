const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('source/app/browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('function boardOrientation');
const end = source.indexOf('function placementFromBoard', start);
if (start < 0 || end < 0) throw new Error('orientation resolver missing');

function resolve(board, pieces, globalBlack = false) {
  const context = {
    cfg: {orientation: 'auto'},
    document: {querySelector: () => globalBlack ? {} : null},
    pieceCode: piece => piece.code,
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return context.boardOrientation(board, pieces);
}

const board = {
  className: 'board', parentElement: {className: ''},
  getAttribute: () => '', closest: () => null,
};
const pieces = [
  {code: 'wk', getBoundingClientRect: () => ({top: 700, height: 80})},
  {code: 'bk', getBoundingClientRect: () => ({top: 100, height: 80})},
];

if (resolve(board, pieces, true) !== 'white') {
  throw new Error('hidden unrelated black board changed visible board orientation');
}

const blackBoard = {...board, closest: selector => selector.includes('orientation-black') ? {className: 'orientation-black'} : null};
if (resolve(blackBoard, pieces, false) !== 'black') {
  throw new Error('visible board black ancestor was ignored');
}

console.log('overlay orientation tests passed');
