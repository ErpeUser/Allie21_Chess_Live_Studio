const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('function isTransientPieceNode');
const end = source.indexOf('function placementFromBoard', start);
if (start < 0 || end < 0) throw new Error('authoritative board adapter missing');

const context = {};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

if (!context.isTransientPieceNode({className: 'piece black pawn fading'})) {
  throw new Error('Chessground fading capture must not count as a live piece');
}

const board = {
  tagName: 'WC-CHESS-BOARD',
  getBoundingClientRect: () => ({width: 800, height: 800}),
};
const chessComPawn = {
  tagName: 'DIV', className: 'piece wp square-74',
  getAttribute: () => '',
};
const chessCom = context.authoritativePieceSquare(chessComPawn, board, 'white');
if (JSON.stringify(chessCom) !== JSON.stringify({file: 6, rank: 3})) {
  throw new Error(`Chess.com square-74 must be g4, got ${JSON.stringify(chessCom)}`);
}

const lichessBoard = {
  tagName: 'CG-BOARD',
  getBoundingClientRect: () => ({width: 800, height: 800}),
};
const lichessPawn = {
  tagName: 'PIECE', className: 'white pawn',
  getAttribute: name => name === 'style' ? 'transform: translate(600px, 400px);' : '',
};
const lichess = context.authoritativePieceSquare(lichessPawn, lichessBoard, 'white');
if (JSON.stringify(lichess) !== JSON.stringify({file: 6, rank: 3})) {
  throw new Error(`Chessground transform must be g4, got ${JSON.stringify(lichess)}`);
}
const lichessPercentPawn = {
  tagName: 'PIECE', className: 'white pawn',
  getAttribute: name => name === 'style' ? 'transform: translate(600%, 400%);' : '',
};
const lichessPercent = context.authoritativePieceSquare(lichessPercentPawn, lichessBoard, 'white');
if (JSON.stringify(lichessPercent) !== JSON.stringify({file: 6, rank: 3})) {
  throw new Error(`percent Chessground transform must be g4, got ${JSON.stringify(lichessPercent)}`);
}

const genericPiece = {tagName: 'DIV', className: 'white pawn', getAttribute: () => ''};
if (context.authoritativePieceSquare(genericPiece, board, 'white') !== null) {
  throw new Error('unknown boards must retain the stabilized geometry fallback');
}

if (context.boardFrameIsStable('position-a', 1000)) {
  throw new Error('first generic frame must wait for animation completion');
}
if (context.boardFrameIsStable('position-a', 1100)) {
  throw new Error('generic frame became stable too early');
}
if (!context.boardFrameIsStable('position-a', 1240)) {
  throw new Error('unchanged generic frame must become stable after 220ms');
}
if (context.boardFrameIsStable('position-b', 1250)) {
  throw new Error('a changed generic frame must restart stabilization');
}

console.log('overlay board adapter tests passed');
