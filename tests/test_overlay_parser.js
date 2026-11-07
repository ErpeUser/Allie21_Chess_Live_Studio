const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('const sanPattern=');
const end = source.indexOf('function movesFromRoot', start);
if (start < 0 || end < 0) throw new Error('move parser not found');

function moveNode(text, ply, piece = '', dataSan = '', dataNode = '') {
  const icon = {
    className: piece ? `icon-font-chess ${piece}` : '',
    getAttribute() { return ''; },
  };
  const owner = {
    className: 'move',
    getAttribute() { return ''; },
    querySelectorAll() { return piece ? [icon] : []; },
  };
  return {
    textContent: text,
    className: 'move-san',
    getAttribute(name) {
      if (name === 'data-ply') return String(ply);
      if (name === 'data-san') return dataSan;
      if (name === 'data-node') return dataNode;
      return '';
    },
    querySelectorAll() { return []; },
    closest() { return owner; },
  };
}

const nodes = [
  moveNode('e4', 0), moveNode('a6', 1, 'knight-black'),
  moveNode('f3', 2, 'knight-white'), moveNode('d5', 3),
  moveNode('c3', 4, 'knight-white'), moveNode('c6', 5),
  moveNode('a4', 6, 'knight-white'), moveNode('d7', 7, 'king-black'),
  moveNode('exd5', 8), moveNode('e8', 9, 'queen-black'),
];
const context = { result: [], nodes };
vm.runInNewContext(source.slice(start, end) + '\nresult=movesFromNodes(nodes);', context);
const actual = JSON.stringify(Array.from(context.result));
const expected = JSON.stringify(['e4', 'Na6', 'Nf3', 'd5', 'Nc3', 'c6', 'Na4', 'Kd7', 'exd5', 'Qe8']);
if (actual !== expected) throw new Error(`expected ${expected}, got ${actual}`);

context.result = [];
context.nodes = [moveNode('♞ f6 0.8s', 0, '', 'Nf6')];
vm.runInNewContext('result=movesFromNodes(nodes);', context);
if (JSON.stringify(Array.from(context.result)) !== JSON.stringify(['Nf6'])) {
  throw new Error('data-san must win over decorated visible text');
}

context.result = [];
context.nodes = [moveNode('♘f3', 0), moveNode('♞c6', 1)];
vm.runInNewContext('result=movesFromNodes(nodes);', context);
if (JSON.stringify(Array.from(context.result)) !== JSON.stringify(['Nf3', 'Nc6'])) {
  throw new Error('Lichess figurine SAN must be normalized');
}

context.result = [];
context.nodes = [moveNode('c5', '', '', '', '0-1'), moveNode('e4', '', '', '', '0-0')];
vm.runInNewContext('result=movesFromNodes(nodes);', context);
if (JSON.stringify(Array.from(context.result)) !== JSON.stringify(['e4', 'c5'])) {
  throw new Error('Chess.com data-node ply order must be honored');
}
