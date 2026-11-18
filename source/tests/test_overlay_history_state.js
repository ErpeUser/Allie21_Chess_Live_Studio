const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('source/app/browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('function shouldResetBoardSession');
const end = source.indexOf('function pieceCode', start);
assert.ok(start >= 0 && end > start, 'history cursor helpers must be exported in the source slice');

function move(ply, className = '', selected = false) {
  return {
    className,
    textContent: ply % 2 ? 'e5' : 'e4',
    getAttribute(name) {
      if (name === 'data-ply') return String(ply);
      if (name === 'aria-current') return selected ? 'true' : '';
      return '';
    },
    matches(selector) {
      return selector.split(',').some(part => part.trim() === `.${className}`);
    },
    closest(selector) {
      return this.matches(selector) ? this : null;
    },
  };
}

const context = {};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

context.nodes = [move(0), move(1, 'selected', true), move(2), move(3)];
vm.runInContext('result = historyCursor(nodes);', context);
assert.deepEqual({
  selectedPly: context.result.selectedPly,
  lastPly: context.result.lastPly,
  atEnd: context.result.atEnd,
}, {selectedPly: 1, lastPly: 3, atEnd: false});

context.nodes = [move(0), move(1), move(2, 'active', true)];
vm.runInContext('result = historyCursor(nodes);', context);
assert.equal(context.result.atEnd, true);

const customNodes = [
  {className: '', textContent: 'e4', getAttribute: () => '', matches: () => false, closest: () => null},
  {className: 'a1t', textContent: 'e5', getAttribute: () => '', matches: selector => selector.includes('.a1t'), closest: () => null},
  {className: '', textContent: 'Nf3', getAttribute: () => '', matches: () => false, closest: () => null},
];
context.nodes = customNodes;
vm.runInContext('result = historyCursor(nodes);', context);
assert.deepEqual({selectedPly: context.result.selectedPly, lastPly: context.result.lastPly, atEnd: context.result.atEnd}, {
  selectedPly: 1,
  lastPly: 2,
  atEnd: false,
});

assert.equal(context.shouldResetBoardSession('lichess:gW1oBGF2OQyM', 'lichess:gW1oBGF2OQyM'), false);
assert.equal(context.shouldResetBoardSession('lichess:gW1oBGF2OQyM', 'lichess:another'), true);
assert.doesNotMatch(source, /hashchange',\(\)=>resetBoardSession/);
assert.match(source, /const handleNavigation=/);

console.log('overlay history state tests passed');
