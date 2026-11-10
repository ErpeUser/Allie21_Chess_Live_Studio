'use strict';
(() => {
  const status = document.getElementById('workerStatus');
  const wake = document.getElementById('wakeWorker');
  const update = document.getElementById('checkUpdate');
  const auto = document.getElementById('autoReload');
  document.getElementById('extensionVersion').textContent = chrome.runtime.getManifest().version;
  function ask(type) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Worker antwortet nicht. Erweiterung neu laden.')), 6000);
      try {
        chrome.runtime.sendMessage({type}, response => {
          clearTimeout(timer);
          const error = chrome.runtime.lastError;
          if (error || !response) reject(new Error(error?.message || 'Keine Antwort.'));
          else resolve(response);
        });
      } catch (error) {clearTimeout(timer); reject(error);}
    });
  }
  wake.onclick = async () => {
    wake.disabled = true;
    try {
      const result = await ask('allie21:ping');
      status.textContent = `Worker antwortet. Version ${result.version}, Port ${result.port}. Server separat testen.`;
    } catch (error) {status.textContent = error.message;}
    finally {wake.disabled = false;}
  };
  update.onclick = async () => {
    update.disabled = true;
    try {
      const result = await ask('allie21:check-update');
      const messages = {current: 'Erweiterungsdateien aktuell.', reloading: 'Erweiterung wird neu geladen. Schach-Tabs danach neu laden.',
        'awaiting-deployment': 'UPDATE_ALLIE.cmd ausfuehren; noch kein fertiger Update-Stand erkannt.',
        'store-managed': 'Store-Erweiterung: Updates werden vom Browser verwaltet.', disabled: 'Automatisches Neuladen ausgeschaltet.'};
      status.textContent = messages[result.state] || `Update-Pruefung: ${result.reason || result.state}`;
    } catch (error) {status.textContent = error.message;}
    finally {update.disabled = false;}
  };
  chrome.storage.local.get({autoReloadUnpacked: true}, values => {auto.checked = values.autoReloadUnpacked !== false;});
  auto.onchange = () => chrome.storage.local.set({autoReloadUnpacked: auto.checked});
})();
