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

assert.match(source, /function structuralMoveRoot\(\)[\s\S]*movesFromRoot\(root\)/);
console.log('lichess arrow tests passed');
