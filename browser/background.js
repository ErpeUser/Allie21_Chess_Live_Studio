'use strict';

const DEFAULT_PORT = 8765;

function configuredPort() {
  return new Promise(resolve => {
    chrome.storage.local.get({port: DEFAULT_PORT}, value => {
      const port = Number(value.port);
      resolve(Number.isInteger(port) && port >= 1024 && port <= 65535 ? port : DEFAULT_PORT);
    });
  });
}

function serviceUrl(port, path) {
  return `http://127.0.0.1:${port}${path}`;
}

async function refreshBadge() {
  try {
    const port = await configuredPort();
    const response = await fetch(serviceUrl(port, '/health'), {cache: 'no-store', headers: {'X-Allie-Overlay': '1'}});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    await chrome.action.setBadgeText({text: 'OK'});
    await chrome.action.setBadgeBackgroundColor({color: '#16c784'});
    await chrome.action.setTitle({title: 'Allie 2.1: Server aktiv'});
  } catch {
    await chrome.action.setBadgeText({text: '!'});
    await chrome.action.setBadgeBackgroundColor({color: '#ef3340'});
    await chrome.action.setTitle({title: 'Allie 2.1: Lokalen Server starten'});
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'allie21:get-port') return false;
  configuredPort().then(port => sendResponse({port}));
  return true;
});

chrome.runtime.onInstalled.addListener(refreshBadge);
chrome.runtime.onStartup.addListener(refreshBadge);

// MV3 alarms are allowed to run while the worker is suspended, but current
// Chromium enforces a 30-second minimum period.  Create the alarm from
// lifecycle events and avoid resetting an existing alarm on every worker
// wake-up.
function ensureHealthAlarm() {
  if (typeof chrome.alarms.get !== 'function') {
    chrome.alarms.create('allie-health', {periodInMinutes: 0.5});
    return;
  }
  chrome.alarms.get('allie-health', alarm => {
    if (!alarm) chrome.alarms.create('allie-health', {periodInMinutes: 0.5});
  });
}
chrome.runtime.onInstalled.addListener(ensureHealthAlarm);
chrome.runtime.onStartup.addListener(ensureHealthAlarm);
chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name === 'allie-health') refreshBadge();
});
ensureHealthAlarm();
refreshBadge();
