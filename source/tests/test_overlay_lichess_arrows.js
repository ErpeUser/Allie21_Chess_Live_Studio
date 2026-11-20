'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('source/app/browser/allie21_overlay.user.js', 'utf8');
const parserStart = source.indexOf('const figurines=');
const parserEnd = source.indexOf('function movesFromNodes', parserStart);
assert.ok(parserStart >= 0 && parserEnd > parserStart);
const parser = {};
vm.createContext(parser);
vm.runInContext(source.slice(parserStart, parserEnd) + '\nresult=cleanMove("1 e4");', parser);
assert.equal(parser.result, 'e4');
vm.runInContext('result=cleanMove("2 ♞c6");', parser);
assert.equal(parser.result, 'Nc6');

const arrowStart = source.indexOf('function center(');
const arrowEnd = source.indexOf('function atHistoryEnd', arrowStart);
const nodes = [];
const context = {
  document: {createElementNS(_ns, tag) {
    const node = {tag, attrs:{}, setAttribute(key, value){this.attrs[key]=String(value)}};
    nodes.push(node); return node;
  }},
  svg: {appendChild(node){nodes.push(node)}},
};
vm.createContext(context);
vm.runInContext(source.slice(arrowStart, arrowEnd) + '\nresult=drawArrow(svg, {left:0,top:0,width:800,height:800}, "black", "e2e4", "#16c784");', context);
assert.ok(nodes.some(node => node.tag === 'line'));
assert.ok(nodes.some(node => node.tag === 'polygon'));

const visualStart = source.indexOf('function visualArrows(data)');
const visualEnd = source.indexOf('function overlayMode()', visualStart);
assert.ok(visualStart >= 0 && visualEnd > visualStart);
const visualContext = {
  ARROW_COLORS: {
    ownTop1: '#16c784', ownTop2: '#7ee2b8',
    opponentTop1: '#ef3340', opponentTop2: '#ff9299', premove: '#2f80ed',
  },
};
vm.createContext(visualContext);
vm.runInContext(source.slice(visualStart, visualEnd) + `
result=visualArrows({
  fen_only:true, show_moves:false, history_complete:false, turn_verified:false,
  my_moves:[], opponent_moves:[], engine_moves:[{uci:'e2e4'}],
  player_to_move:true, premove:null,
});
resultBlack=visualArrows({
  fen_only:true, show_moves:false, history_complete:false, turn_verified:false,
  my_moves:[], opponent_moves:[], engine_moves:[{uci:'e7e5'}],
  player_to_move:false, premove:null,
});
`, visualContext);
assert.deepEqual(JSON.parse(JSON.stringify(visualContext.result)).map(item => item.uci), ['e2e4']);
assert.deepEqual(JSON.parse(JSON.stringify(visualContext.resultBlack)).map(item => item.uci), ['e7e5']);

assert.match(source, /function structuralMoveRoot\(\)[\s\S]*movesFromRoot\(root\)/);
console.log('lichess arrow tests passed');
