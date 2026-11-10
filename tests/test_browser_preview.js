'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '..', 'browser', 'allie21_overlay.user.js'), 'utf8');
const start = source.indexOf('function analyze(');
const end = source.indexOf("el('now').onclick", start);
assert.ok(start >= 0 && end > start, 'Production analysis handler must be present');

function load() {
  const requests = [];
  const context = {
    pending:false, cfg:{enabled:true,elo:1850,tc:'300+0',playStyle:'normal'},
    analysisSerial:0, analysisKey:'', activeRequest:null,
    selectedOpeningSettings:()=>({opening_white:'vienna',opening_black:'stafford'}),
    el:()=>({textContent:''}),
    postJson:(url,data,timeout)=>{requests.push({url,data,timeout});return {promise:new Promise(()=>{}),abort(){}};},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start,end), context);
  return {context,requests};
}

test('PGN requests the real preview needed for blue continuation and applied openings', () => {
  const app = load();
  app.context.analyze('*','','','black');
  assert.equal(app.requests.length,1);
  const sent = app.requests[0];
  assert.equal(sent.url,'/analyze');
  assert.equal(sent.data.preview,true);
  assert.equal(sent.data.analysis_source,'allie');
  assert.equal(sent.data.opening_white,'vienna');
  assert.equal(sent.data.opening_black,'stafford');
  assert.equal(sent.data.player_side,'black');
});

test('FEN without history remains Stockfish without fabricated Allie preview', () => {
  const app = load();
  app.context.analyze('','','8/8/8/3k4/8/8/4K3/8 w - - 0 1');
  assert.equal(app.requests[0].data.analysis_source,'stockfish');
  assert.equal(app.requests[0].data.preview,false);
});

test('disabled recommendations never issue an analysis request', () => {
  const app = load();
  app.context.cfg.enabled=false;
  app.context.analyze('*');
  assert.equal(app.requests.length,0);
});
