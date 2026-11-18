'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..', 'app', 'browser');
const healthy = {alive:true, ready:true, api_version:2, instance_id:'a'.repeat(32), model_loaded:true, stockfish_available:true, model_phase:'ready'};
const tick = () => new Promise(resolve => setImmediate(resolve));
const reply = (body, ok=true) => ({ok, status:ok?200:503, json:async()=>body});
function worker() {
  const state={port:8765,text:'',title:'',fetcher:async()=>reply(healthy),onChanged:[],events:[]};
  const event = list => ({addListener:fn=>list.push(fn)});
  const sandbox={console,Promise,AbortController,URL,
    setTimeout:(fn,ms)=>setTimeout(fn,Math.min(ms,35)),clearTimeout,
    fetch:(url,opts)=>state.fetcher(url,opts),
    chrome:{runtime:{id:'same-extension',lastError:null,onMessage:event([]),onStartup:event([]),onInstalled:event([])},
      storage:{local:{get:(_defaults,callback)=>callback({port:state.port})},onChanged:event(state.onChanged)},
      action:{setBadgeText:async v=>{state.text=v.text;state.events.push(v.text);},setBadgeBackgroundColor:async()=>{},setTitle:async v=>{state.title=v.title;}},
      alarms:{get:(_name,callback)=>callback({name:'allie-health'}),create:()=>{},onAlarm:event([])}}};
  const context=vm.createContext(sandbox);
  sandbox.importScripts = (...files) => files.forEach(file=>vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),context));
  vm.runInContext(fs.readFileSync(path.join(root,'background.js'),'utf8'),context);
  return {state,context};
}

test('HTTP 200 from an unrelated service is not a healthy Allie server',async()=>{
  const {state,context}=worker();await tick();
  state.fetcher=async()=>reply({hello:'not Allie'});
  await context.refreshBadge();
  assert.notEqual(state.text,'OK');
});
test('model loading is not reported as ready',async()=>{
  const {state,context}=worker();await tick();
  state.fetcher=async()=>reply({...healthy,ready:false,model_loaded:false,model_phase:'loading',phase:'model_loading'});
  await context.refreshBadge();
  assert.notEqual(state.text,'OK');
  assert.match(state.title,/lad/i);
});
test('Stockfish fallback is distinguishable from full Allie readiness',async()=>{
  const {state,context}=worker();await tick();
  state.fetcher=async()=>reply({...healthy,ready:false,model_loaded:false,model_phase:'failed',phase:'model_failed'});
  await context.refreshBadge();
  assert.equal(state.text,'SF');
});
test('a hanging health request is aborted rather than leaving the old OK badge',async()=>{
  const {state,context}=worker();await tick();
  let aborted=false;
  state.fetcher=(_url,options)=>new Promise((_resolve,reject)=>options.signal?.addEventListener('abort',()=>{aborted=true;reject(new Error('aborted'));}));
  const finished=await Promise.race([context.refreshBadge().then(()=>true),new Promise(resolve=>setTimeout(()=>resolve(false),150))]);
  assert.equal(finished,true);assert.equal(aborted,true);assert.equal(state.text,'!');
});
test('late old-port response cannot replace a newer port result',async()=>{
  const {state,context}=worker();await tick();
  let oldResolve;
  state.fetcher=url=>url.includes(':8765/')?new Promise(resolve=>{oldResolve=resolve;}):Promise.resolve(reply({},false));
  const old=context.refreshBadge();await tick();state.port=18765;
  const recent=context.refreshBadge();await recent;assert.equal(state.text,'!');
  oldResolve(reply(healthy));await old;assert.equal(state.text,'!');
});
test('storage port changes refresh the badge immediately',async()=>{
  const {state}=worker();await tick();let called='';
  state.port=18765;state.fetcher=async url=>{called=url;return reply(healthy);};
  for(const listener of state.onChanged)listener({port:{oldValue:8765,newValue:18765}},'local');
  await tick();assert.equal(called,'http://127.0.0.1:18765/health');
});
