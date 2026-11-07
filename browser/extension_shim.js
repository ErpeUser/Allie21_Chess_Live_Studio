/* Minimal Greasemonkey compatibility for the unpacked Edge extension. */
var GM_getValue = (key, fallback) => {
  try {
    const value = localStorage.getItem(`__allie21_${key}`);
    return value === null ? fallback : JSON.parse(value);
  } catch (_) {
    return fallback;
  }
};

var GM_setValue = (key, value) => {
  try { localStorage.setItem(`__allie21_${key}`, JSON.stringify(value)); } catch (_) {}
};

var GM_xmlhttpRequest = options => {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
    options.ontimeout?.();
  }, options.timeout || 15000);
  fetch(options.url, {
    method: options.method || 'GET',
    headers: options.headers || {},
    body: options.data,
    signal: controller.signal,
  }).then(async response => {
    clearTimeout(timer);
    options.onload?.({status: response.status, responseText: await response.text()});
  }).catch(error => {
    clearTimeout(timer);
    if (error.name !== 'AbortError') options.onerror?.(error);
  });
  return {abort: () => { clearTimeout(timer); controller.abort(); }};
};
