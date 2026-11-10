'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..','browser');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function page() {
  const state={stored:{port:8741},error:null,listeners:{},elements:{},fetcher:async()=>({ok:true,json:async()=>({alive:true,ready:true,model_loaded:true,stockfish_available:true,api_version:2,instance_id:'a'.repeat(32)})})};
  const html=fs.readFileSync(path.join(root,'options.html'),'utf8');
  for(const match of html.matchAll(/\bid=["']([^"']+)["']/g))state.elements[match[1]]={value:'',textContent:'',href:'',disabled:false,dataset:{},setAttribute(k,v){this[k]=v;},addEventListener(event,fn){state.listeners[match[1]+':'+event]=fn;}};
  const context=vm.createContext({console,Promise,AbortController,URL,setTimeout,clearTimeout,
    document:{getElementById:id=>state.elements[id]},
    fetch:(url,opts)=>state.fetcher(url,opts),
    chrome:{runtime:{lastError:null},storage:{local:{get:(_defaults,callback)=>callback({...state.stored}),set:(value,callback)=>{
      context.chrome.runtime.lastError=state.error;
      if(!state.error)Object.assign(state.stored,value);
      callback();context.chrome.runtime.lastError=null;
    }}}}});
  // MV3 permits packaged scripts, not inline JS. Load the exact referenced
  // production files in order, rather than manually selecting a function.
  for(const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)){
    const src=/\bsrc=["']([^"']+)["']/.exec(match[1]);
    if(!src)continue;
    assert.ok(!src[1].includes('://')&&!src[1].includes('..'));
    vm.runInContext(fs.readFileSync(path.join(root,src[1]),'utf8'),context,{filename:src[1]});
  }
  const click=async id=>{const fn=state.listeners[id+':click'];assert.ok(fn,`${id} must have a handler under MV3 CSP`);await fn({preventDefault(){}});await tick();};
  return {state,click};
}
test('port is restored from storage under MV3 script policy',async()=>{const{state}=page();await tick();assert.equal(Number(state.elements.port.value),8741);});
test('saving port updates persistent storage and reports success',async()=>{const{state,click}=page();await tick();state.elements.port.value='18765';await click('save');assert.equal(state.stored.port,18765);assert.match(state.elements.status.textContent,/18765/);});
test('invalid port is not persisted',async()=>{const{state,click}=page();await tick();state.elements.port.value='80';await click('save');assert.equal(state.stored.port,8741);assert.match(state.elements.status.textContent,/1024/);});
test('storage failure is not presented as success',async()=>{const{state,click}=page();await tick();state.elements.port.value='18765';state.error={message:'storage unavailable'};await click('save');assert.equal(state.stored.port,8741);assert.doesNotMatch(state.elements.status.textContent,/Gespeichert\./);assert.ok(state.elements.status.textContent);});
test('connection test rejects an unrelated service instead of claiming success',async()=>{
  const {state,click}=page();await tick();
  state.fetcher=async()=>({ok:true,json:async()=>({hello:'wrong service'})});
  await click('test');
  assert.match(state.elements.status.textContent,/fehlgeschlagen/);
  assert.equal(state.elements.status.dataset.kind,'error');
});
test('connection test reports loading while keeping the viewer link on the chosen loopback port',async()=>{
  const {state,click}=page();await tick();state.elements.port.value='18765';
  let called='';state.fetcher=async url=>{called=url;return {ok:true,json:async()=>({alive:true,ready:false,model_loaded:false,stockfish_available:true,api_version:2,instance_id:'b'.repeat(32),model_phase:'loading'})};};
  await state.listeners['port:input']();await click('test');
  assert.equal(called,'http://127.0.0.1:18765/health');
  assert.equal(state.elements.viewer.href,'http://127.0.0.1:18765/viewer');
  assert.match(state.elements.status.textContent,/geladen/);
  assert.notEqual(state.elements.status.dataset.kind,'good');
});
