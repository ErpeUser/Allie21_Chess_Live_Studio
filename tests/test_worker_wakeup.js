'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '..', 'browser/background.js'), 'utf8');
function worker() {
  let message, clicked, alarm, requests = 0;
  const event = () => ({addListener() {}});
  const chrome = {
    runtime: {id: 'owned', getManifest: () => ({version: '11.2.18.0'}),
      openOptionsPage: async () => {}, onInstalled: event(), onStartup: event(),
      onMessage: {addListener(fn) {message = fn;}}},
    storage: {local: {get(defaults, callback) {callback({...defaults, port: 18765});}}, onChanged: event()},
    action: {setBadgeText: async () => {}, setBadgeBackgroundColor: async () => {}, setTitle: async () => {},
      onClicked: {addListener(fn) {clicked = fn;}}},
    alarms: {get(_name, cb) {cb({name: 'allie-health'});}, create() {throw Error('alarm was reset');},
      onAlarm: {addListener(fn) {alarm = fn;}}},
  };
  const context = {chrome, importScripts() {}, AllieUpdates: {check: async () => ({state: 'current'})},
    AllieConnection: {DEFAULT_PORT: 8765, parsePort: Number, healthStatus: () => ({text: 'OK'})},
    AbortController, setTimeout, clearTimeout,
    fetch: async url => {
      if (url.endsWith('/api/pairing')) { requests++; return {ok: true, json: async () => ({pairing_code: '12345678'})}; }
      if (url.endsWith('/api/capability')) return {ok: true, json: async () => ({token:'token', instance_id:'instance', api_version:2, schema_version:1})};
      return {ok: false, status:404, json: async () => ({})};
    },
  };
  vm.createContext(context); vm.runInContext(source, context);
  const send = (type, id = 'owned') => new Promise(resolve => {
    if (!message({type}, {id}, resolve)) resolve(null);
  });
  return {send, clicked, alarm, requests: () => requests};
}
test('a cold worker replies without installation/startup events', async () => {
  for (let n = 0; n < 2; n++) {
    const w = worker(); const reply = await w.send('allie21:ping');
    assert.equal(reply.ok, true); assert.equal(reply.port, 18765); assert.equal(reply.version, '11.2.18.0');
  }
});
test('worker rejects foreign senders', async () => {
  assert.equal(await worker().send('allie21:ping', 'foreign'), null);
});
test('concurrent pairing messages use one request and both receive a valid code', async () => {
  const w = worker(); const responses = await Promise.all([w.send('allie21:get-pairing'), w.send('allie21:get-pairing')]);
  assert.deepEqual(responses.map(x => x.pairing_code), ['12345678', '12345678']); assert.equal(w.requests(), 1);
});
test('worker completes the capability handshake with the pairing code', async () => {
  const w = worker(); const reply = await w.send('allie21:get-capability');
  assert.deepEqual(reply, {token:'token', instance_id:'instance', api_version:2, schema_version:1});
});
test('toolbar handler and persisted alarm are available after every start', async () => {
  const w = worker(); assert.equal(typeof w.clicked, 'function');
  w.alarm({name: 'allie-health'}); await w.clicked();
});
