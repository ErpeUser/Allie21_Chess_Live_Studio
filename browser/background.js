'use strict';
importScripts('connection.js');

const DEFAULT_PORT = AllieConnection.DEFAULT_PORT;
let healthRevision = 0;
let healthController = null;

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
  const port = await configuredPort();
  const response = await fetch(serviceUrl(port, '/api/pairing'), {
    cache: 'no-store', headers: {'X-Allie-Overlay': '1'},
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  if (!/^\\d{8}$/.test(String(data?.pairing_code || ''))) {
    throw new Error('Pairing-Code fehlt');
  }
  return String(data.pairing_code);
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

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id) return false;
  if (message?.type === 'allie21:get-port') {
    configuredPort().then(port => sendResponse({port}));
    return true;
  }
  if (message?.type === 'allie21:get-pairing') {
    pairingCode().then(pairing_code => sendResponse({pairing_code}))
      .catch(error => sendResponse({error: error.message || 'Pairing-Code nicht verfügbar'}));
    return true;
  }
  return false;
});
chrome.runtime.onInstalled.addListener(refreshBadge);
chrome.runtime.onStartup.addListener(refreshBadge);
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.port) refreshBadge();
});

// Reuse the persisted MV3 alarm instead of resetting its schedule on wakeup.
function ensureHealthAlarm() {
  chrome.alarms.get('allie-health', alarm => {
    if (!alarm) chrome.alarms.create('allie-health', {periodInMinutes:0.5});
  });
}
chrome.runtime.onInstalled.addListener(ensureHealthAlarm);
chrome.runtime.onStartup.addListener(ensureHealthAlarm);
chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === 'allie-health') refreshBadge();
});
ensureHealthAlarm();
refreshBadge();
