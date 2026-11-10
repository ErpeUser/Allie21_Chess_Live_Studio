'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '..', 'browser', 'updates.js'), 'utf8');
function load({session = {}, version = '11.2.18.0', disk = '11.2.18.0', revision = 'a'.repeat(64), stampVersion, kind = 'development', enabled = true, broken = false, management = true} = {}) {
  let reloads = 0;
  const context = {
    chrome: {
      runtime: {getManifest: () => ({version}), getURL: p => p, reload: () => {reloads++;}},
      storage: {local: {get: async () => ({autoReloadUnpacked: enabled})}, session: {
        get: async () => ({...session}), set: async value => Object.assign(session, value),
      }},
    },
    fetch: async url => {
      if (broken) throw new Error('temporary read failure');
      return {ok: true, json: async () => url === 'manifest.json' ? {version: disk} : {revision, version: stampVersion ?? disk}};
    },
  };
  if (management) context.chrome.management = {getSelf: async () => ({installType: kind})};
  vm.createContext(context); vm.runInContext(source, context);
  return {check: () => context.AllieUpdates.check(), count: () => reloads, session};
}
test('unchanged unpacked extension does not reload', async () => {
  const w = load(); await w.check(); await w.check(); assert.equal(w.count(), 0);
});
test('new version reloads once despite concurrent checks', async () => {
  const w = load({disk: '11.2.19.0'}); await Promise.all([w.check(), w.check()]); assert.equal(w.count(), 1);
});
test('revision survives worker suspension and detects next deployment', async () => {
  const session = {}; await load({session}).check();
  const w = load({session, revision: 'b'.repeat(64)}); await w.check(); assert.equal(w.count(), 1);
});
test('store extensions are not reloaded by development updater', async () => {
  const w = load({kind: 'normal', disk: '11.2.19.0'}); await w.check(); assert.equal(w.count(), 0);
});
test('missing management permission still checks an unpacked deployment stamp', async () => {
  const w = load({management: false, disk: '11.2.19.0'});
  assert.equal((await w.check()).state, 'reloading');
  assert.equal(w.count(), 1);
});
test('explicit opt-out is respected', async () => {
  const w = load({enabled: false, disk: '11.2.19.0'}); await w.check(); assert.equal(w.count(), 0);
});
test('partial deployment read failure does not trigger reload', async () => {
  const w = load({broken: true}); await w.check(); assert.equal(w.count(), 0);
});
test('invalid revision does not override session baseline', async () => {
  const session = {allieRunningRevision: 'a'.repeat(64)};
  const w = load({session, revision: '../../bad'}); await w.check();
  assert.equal(w.count(), 0); assert.equal(session.allieRunningRevision, 'a'.repeat(64));
});
test('old completion marker blocks a partially deployed new version', async () => {
  const w = load({disk: '11.2.19.0', stampVersion: '11.2.18.0'});
  assert.equal((await w.check()).state, 'awaiting-deployment'); assert.equal(w.count(), 0);
});
test('sequential checks cannot cause repeated reloads before the worker unloads', async () => {
  const w = load({disk: '11.2.19.0'}); await w.check(); await w.check(); assert.equal(w.count(), 1);
});

