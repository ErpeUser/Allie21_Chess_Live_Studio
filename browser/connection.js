/* Shared, dependency-free connection validation for MV3 packaged pages. */
'use strict';
(() => {
  const DEFAULT_PORT = 8765;
  function parsePort(value) {
    const raw = String(value ?? '').trim();
    if (!/^\d{4,5}$/.test(raw)) return null;
    const port = Number(raw);
    return Number.isInteger(port) && port >= 1024 && port <= 65535 ? port : null;
  }
  function healthStatus(data) {
    if (!data || data.alive !== true || data.api_version !== 2 ||
        !/^[a-f0-9]{32}$/.test(String(data.instance_id || ''))) {
      throw new Error('Kein kompatibler Allie-Server an diesem Port.');
    }
    if (data.ready === true && data.model_loaded === true && data.stockfish_available === true) {
      return {text:'OK', color:'#16c784', title:'Allie 2.1 und Stockfish sind bereit.'};
    }
    if (data.model_phase === 'loading' || data.phase === 'model_loading') {
      return {text:'...', color:'#d69e2e', title:'Allie wird geladen; der lokale Server ist erreichbar.'};
    }
    if (data.stockfish_available === true) {
      return {text:'SF', color:'#d69e2e', title:'Stockfish bereit; Allie ist noch nicht verfuegbar.'};
    }
    if (data.model_loaded === true) {
      return {text:'A', color:'#d69e2e', title:'Allie bereit; Stockfish fehlt oder ist nicht verifiziert.'};
    }
    return {text:'!', color:'#ef3340', title:'Server erreichbar; Analyse-Engines sind nicht bereit.'};
  }
  globalThis.AllieConnection = Object.freeze({DEFAULT_PORT, parsePort, healthStatus});
})();
