'use strict';
importScripts('connection.js');
importScripts('updates.js');

const DEFAULT_PORT = AllieConnection.DEFAULT_PORT;
let healthRevision = 0;
let healthController = null;
let pairingRequest = null;

function configuredPort() {
  return new Promise(resolve => {
    const timer = setTimeout(() => resolve(DEFAULT_PORT), 1500);
    try {
      chrome.storage.local.get({port: DEFAULT_PORT}, value => {
        clearTimeout(timer);
        const failed = chrome.runtime.lastError;
        resolve(failed ? DEFAULT_PORT : AllieConnection.parsePort(value?.port) ?? DEFAULT_PORT);
      });
    } catch {
      clearTimeout(timer);
      resolve(DEFAULT_PORT);
    }
  });
}

function serviceUrl(port, path) {
  return `http://127.0.0.1:${port}${path}`;
}

async function pairingCode() {
  if (pairingRequest) return pairingRequest;
  const request = (async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 4500);
    try {
      const port = await configuredPort();
      const response = await fetch(serviceUrl(port, '/api/pairing'), {
        cache: 'no-store', signal: controller.signal, headers: {'X-Allie-Overlay': '1'},
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!/^\d{8}$/.test(String(data?.pairing_code || ''))) {
        throw new Error('Pairing-Code fehlt');
      }
      return String(data.pairing_code);
    } finally {
      clearTimeout(timer);
    }
  })();
  pairingRequest = request;
  try { return await request; }
  finally { if (pairingRequest === request) pairingRequest = null; }
}

async function refreshBadge() {
  const revision = ++healthRevision;
  healthController?.abort();
  const controller = new AbortController();
  healthController = controller;
  const timer = setTimeout(() => controller.abort(), 5000);
  let info;
  try {
    const port = await configuredPort();
    if (revision !== healthRevision) return;
    const response = await fetch(serviceUrl(port, '/health'), {
      cache:'no-store', signal:controller.signal, headers:{'X-Allie-Overlay':'1'},
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    info = AllieConnection.healthStatus(await response.json());
  } catch {
    info = {text:'!', color:'#ef3340', title:'Allie 2.1: Server/Port pruefen oder lokalen Server starten.'};
  } finally {
    clearTimeout(timer);
    if (healthController === controller) healthController = null;
  }
  if (revision !== healthRevision) return;
  try {
    await chrome.action.setBadgeText({text:info.text});
    if (revision !== healthRevision) return;
    await chrome.action.setBadgeBackgroundColor({color:info.color});
    if (revision !== healthRevision) return;
    await chrome.action.setTitle({title:info.title});
  } catch {
    // The extension may have been unloaded during a pending badge operation.
  }
}

// Register synchronously on EVERY worker start. Idle termination is normal.
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id) return false;
  if (message?.type === 'allie21:ping') {
    configuredPort().then(port => sendResponse({ok: true, port,
      version: chrome.runtime.getManifest().version, worker: 'awake'}));
    return true;
  }
  if (message?.type === 'allie21:check-update') {
    AllieUpdates.check().then(sendResponse);
    return true;
  }
  if (message?.type === 'allie21:get-port') {
    configuredPort().then(port => sendResponse({port}));
    return true;
  }
  if (message?.type === 'allie21:get-pairing') {
    pairingCode().then(pairing_code => sendResponse({pairing_code}))
      .catch(error => sendResponse({error: error.message || 'Pairing-Code nicht verfuegbar'}));
    return true;
  }
  return false;
});
chrome.action.onClicked.addListener(() => {
  chrome.runtime.openOptionsPage().catch(() => {});
});
chrome.runtime.onInstalled.addListener(refreshBadge);
chrome.runtime.onStartup.addListener(refreshBadge);
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.port) refreshBadge();
});

function ensureHealthAlarm() {
  chrome.alarms.get('allie-health', alarm => {
    if (!alarm) chrome.alarms.create('allie-health', {periodInMinutes:0.5});
  });
}
chrome.runtime.onInstalled.addListener(ensureHealthAlarm);
chrome.runtime.onStartup.addListener(ensureHealthAlarm);
chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === 'allie-health') {
    refreshBadge();
    AllieUpdates.check();
  }
});
ensureHealthAlarm();
refreshBadge();
AllieUpdates.check();
