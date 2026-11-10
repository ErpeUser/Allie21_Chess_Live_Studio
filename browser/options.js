'use strict';
(() => {
  const {DEFAULT_PORT, parsePort, healthStatus} = AllieConnection;
  const port = document.getElementById('port');
  const status = document.getElementById('status');
  const save = document.getElementById('save');
  const test = document.getElementById('test');
  const viewer = document.getElementById('viewer');
  let testController = null;
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
  save.disabled = true;
  storageCall('get', {port:DEFAULT_PORT}).then(values => {
    port.value = parsePort(values?.port) ?? DEFAULT_PORT;
    updateViewer(port.value);
  }).catch(() => {
    port.value = DEFAULT_PORT;
    show('Gespeicherter Port konnte nicht geladen werden. Bitte erneut speichern.', 'error');
  }).finally(() => {save.disabled = false;});
})();
