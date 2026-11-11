'use strict';
(() => {
  const {DEFAULT_PORT, parsePort, healthStatus} = AllieConnection;
  const port = document.getElementById('port');
  const status = document.getElementById('status');
  const save = document.getElementById('save');
  const test = document.getElementById('test');
  const viewer = document.getElementById('viewer');
  const privateMode = document.getElementById('privateMode');
  const shareMode = document.getElementById('shareMode');
  const normalMode = document.getElementById('normalMode');
  const overlayStatus = document.getElementById('overlayStatus');
  let testController = null;
  let overlayVersion = 0;
  let overlayUpdatedAt = 0;
  function show(message, kind='info') {
    status.textContent = message;
    status.dataset.kind = kind;
  }
  function selectedPort() {
    const value = parsePort(port.value);
    if (value === null) throw new Error('Port muss zwischen 1024 und 65535 liegen.');
    return value;
  }
  function updateViewer(value) {
    viewer.href = `http://127.0.0.1:${value}/viewer`;
  }
  function setOverlayUi(settings) {
    const mode = ['private', 'share', 'normal'].includes(settings?.mode) ? settings.mode : 'private';
    const state = settings?.status && typeof settings.status === 'object' ? settings.status : settings;
    privateMode.checked = mode === 'private';
    shareMode.checked = mode === 'share';
    normalMode.checked = mode === 'normal';
    overlayVersion = Number(settings?.version) || overlayVersion;
    overlayUpdatedAt = Number(settings?.updated_at) || overlayUpdatedAt;
    const detail = state?.state === 'service_unavailable' ? 'Dienst noch nicht bereit' : (state?.state || state?.reason);
    overlayStatus.textContent = mode === 'share'
      ? `Share-Modus aktiv: HUD wird in Bildschirmübertragungen angezeigt.${detail ? ` (${detail})` : ''}`
      : mode === 'normal'
        ? `Browser-HUD im Schach-Tab aktiv; natives Overlay ist aus.${detail ? ` (${detail})` : ''}`
        : `Privatmodus aktiv; Capture-Ausschluss wird vom Dienst verifiziert.${detail ? ` (${detail})` : ''}`;
    overlayStatus.dataset.kind = mode === 'normal' || state?.available !== false ? 'good' : 'error';
  }
  function runtimeMessage(message) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Erweiterungs-Worker antwortet nicht.')), 6000);
      try {
        chrome.runtime.sendMessage(message, response => {
          clearTimeout(timer);
          const failure = chrome.runtime.lastError;
          if (failure) reject(new Error(failure.message || 'Worker nicht verfuegbar.'));
          else if (response?.error) reject(new Error(response.error));
          else resolve(response || {});
        });
      } catch (error) { clearTimeout(timer); reject(error); }
    });
  }
  async function loadOverlaySettings() {
    try { setOverlayUi(await runtimeMessage({type:'allie21:get-overlay-settings'})); }
    catch (error) { overlayStatus.textContent = `Overlay-Status nicht verfuegbar: ${error.message}`; overlayStatus.dataset.kind='error'; }
  }
  async function saveOverlayMode(mode) {
    privateMode.disabled = true; shareMode.disabled = true; normalMode.disabled = true;
    const nextVersion = Math.max(overlayVersion, 0) + 1;
    try {
      const result = await runtimeMessage({type:'allie21:set-overlay-settings', settings:{mode, version:nextVersion, updated_at:Date.now()/1000}});
      if (result?.mode && result.mode !== mode) {
        setOverlayUi(result);
        const labels = {private:'Privatmodus', share:'Share-Modus', normal:'Browser-HUD im Schach-Tab'};
        overlayStatus.textContent = `Konflikt aufgelöst: ${labels[result.mode] || 'Overlay-Modus'} ist jetzt maßgeblich.`;
      } else setOverlayUi(result);
    } catch (error) {
      overlayStatus.textContent = `Overlay-Einstellung konnte nicht synchronisiert werden: ${error.message}`;
      overlayStatus.dataset.kind='error';
      await loadOverlaySettings();
    } finally { privateMode.disabled = false; shareMode.disabled = false; normalMode.disabled = false; }
  }
  function storageCall(method, value) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Speicher antwortet nicht.')), 2000);
      try {
        chrome.storage.local[method](value, result => {
          clearTimeout(timer);
          const failure = chrome.runtime.lastError;
          if (failure) reject(new Error(failure.message || 'Speicher nicht verfuegbar.'));
          else resolve(result);
        });
      } catch (error) {
        clearTimeout(timer);
        reject(error);
      }
    });
  }
  save.addEventListener('click', async () => {
    save.disabled = true;
    try {
      const value = selectedPort();
      await storageCall('set', {port:value});
      updateViewer(value);
      show(`Gespeichert. Port ${value}. Bereits offene Schach-Tabs neu laden.`, 'good');
    } catch (error) {
      show(`Speichern fehlgeschlagen: ${error.message}`, 'error');
    } finally {
      save.disabled = false;
    }
  });
  port.addEventListener('input', () => {
    testController?.abort();
    const value = parsePort(port.value);
    if (value !== null) updateViewer(value);
  });
  test.addEventListener('click', async () => {
    testController?.abort();
    const controller = new AbortController();
    testController = controller;
    const timer = setTimeout(() => controller.abort(), 5000);
    test.disabled = true;
    show('Verbindung wird geprueft ...');
    try {
      const value = selectedPort();
      const response = await fetch(`http://127.0.0.1:${value}/health`, {
        cache:'no-store', signal:controller.signal, headers:{'X-Allie-Overlay':'1'},
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const info = healthStatus(await response.json());
      if (!controller.signal.aborted) show(`Port ${value}: ${info.title}`, info.text === 'OK' ? 'good' : 'info');
    } catch (error) {
      if (testController === controller) show(
        controller.signal.aborted ? 'Pruefung beendet: Zeitlimit oder Port geaendert.' : `Verbindung fehlgeschlagen: ${error.message}`, 'error');
    } finally {
      clearTimeout(timer);
      if (testController === controller) {testController = null; test.disabled = false;}
    }
  });
  privateMode.addEventListener('change', () => { if (privateMode.checked) saveOverlayMode('private'); });
  shareMode.addEventListener('change', () => { if (shareMode.checked) saveOverlayMode('share'); });
  normalMode.addEventListener('change', () => { if (normalMode.checked) saveOverlayMode('normal'); });
  save.disabled = true;
  storageCall('get', {port:DEFAULT_PORT}).then(values => {
    port.value = parsePort(values?.port) ?? DEFAULT_PORT;
    updateViewer(port.value);
  }).catch(() => {
    port.value = DEFAULT_PORT;
    show('Gespeicherter Port konnte nicht geladen werden. Bitte erneut speichern.', 'error');
  }).finally(() => {save.disabled = false;});
  loadOverlaySettings();
  if (typeof setInterval === 'function') setInterval(loadOverlaySettings, 10000);
  try { chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && changes['allie21.overlay.mode.v1']) setOverlayUi(changes['allie21.overlay.mode.v1'].newValue);
  }); } catch { /* options page may run in a minimal test harness */ }
})();
