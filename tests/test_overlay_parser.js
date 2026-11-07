const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('const figurines=');
const end = source.indexOf('function movesFromNodes', start);
if (start < 0 || end < 0) throw new Error('move parser not found');

const icon = {
  className: 'icon-font-chess knight-white',
  getAttribute(name) { return name === 'data-figurine' ? '♘' : ''; },
};
const owner = {
  className: 'move',
  getAttribute() { return ''; },
  querySelectorAll() { return [icon]; },
};
const san = {
  className: 'move-san',
  getAttribute() { return ''; },
  querySelectorAll() { return []; },
  closest() { return owner; },
};
const context = { result: '', san };
vm.runInNewContext(source.slice(start, end) + "\nresult=cleanMove('f3', san);", context);
if (context.result !== 'Nf3') {
  throw new Error(`expected Nf3, got ${context.result}`);
}
