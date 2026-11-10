'use strict';
// The session baseline survives worker suspension, not extension reloads.
// No keepalive, remote code, or unsolicited chess-tab reloads.
var AllieUpdates = (() => {
  let pending = null, reloadRequested = false;
  async function checkOnce() {
    if (reloadRequested) return {state: 'reloading'};
    try {
      const self = await chrome.management.getSelf();
      if (self.installType !== 'development') return {state: 'store-managed'};
      const settings = await chrome.storage.local.get({autoReloadUnpacked: true});
      if (settings.autoReloadUnpacked === false) return {state: 'disabled'};
      const response = await fetch(chrome.runtime.getURL('manifest.json'), {cache: 'no-store'});
      if (!response.ok) return {state: 'unavailable'};
      const manifest = await response.json();
      if (!/^\d+(?:\.\d+){0,3}$/.test(manifest.version || '')) return {state: 'invalid'};
      let revision = '', stampVersion = '';
      try {
        const stamp = await fetch(chrome.runtime.getURL('allie-build.json'), {cache: 'no-store'});
        if (stamp.ok) {
          const data = await stamp.json();
          if (/^[a-f0-9]{64}$/.test(data.revision || '')) revision = data.revision;
          stampVersion = data.version;
        }
      } catch { /* Optional until the first successful local deployment. */ }
      if (!revision || stampVersion !== manifest.version) return {state: 'awaiting-deployment'};
      const saved = await chrome.storage.session.get('allieRunningRevision');
      const changed = manifest.version !== chrome.runtime.getManifest().version ||
        Boolean(saved.allieRunningRevision && revision !== saved.allieRunningRevision);
      if (revision !== saved.allieRunningRevision) {
        await chrome.storage.session.set({allieRunningRevision: revision});
      }
      if (changed) {
        reloadRequested = true;
        try { chrome.runtime.reload(); }
        catch (error) {reloadRequested = false; throw error;}
        return {state: 'reloading', version: manifest.version};
      }
      return {state: 'current', version: manifest.version};
    } catch (error) {
      return {state: 'unavailable', reason: String(error.message || error)};
    }
  }
  return {check() {
    if (pending) return pending;
    pending = checkOnce().finally(() => {pending = null;});
    return pending;
  }};
})();
