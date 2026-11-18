const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('source/app/browser/allie21_overlay.user.js', 'utf8');
const stateStart = source.indexOf('let browserSessionNeedsReset');
const stateEnd = source.indexOf('const START_PLACEMENT', stateStart);
if (stateStart < 0 || stateEnd < 0) throw new Error('one-shot browser session reset is missing');

const context = {retryAfter: 30000};
vm.createContext(context);
vm.runInContext(source.slice(stateStart, stateEnd), context);
if (!context.browserSessionResetPending()) throw new Error('page reload must start with a pending tracker reset');
context.browserSessionResetDone();
if (context.browserSessionResetPending()) throw new Error('successful reset must be consumed exactly once');
if (context.retryAfter !== 0) throw new Error('successful reset must remove an old analysis backoff');
context.markBrowserSessionReset();
if (!context.browserSessionResetPending()) throw new Error('manual analysis must request a fresh tracker reset');
if (!context.shorterValidatedRound('e2e4 e7e5 g1f3', 1)) {
  throw new Error('a shorter validated history must be recognized as a new round');
}
if (context.shorterValidatedRound('e2e4', 1)) {
  throw new Error('the same history length is not a new round');
}

if (!source.includes("<option value='aggressive'>Aggressiv")) {
  throw new Error('aggressive play-style selector is missing');
}
if (!source.includes('play_style:cfg.playStyle')) {
  throw new Error('analysis request does not send the selected play style');
}
if (!source.includes("whiteOpening:'grob'")) {
  throw new Error('ragebait white opening is not the default');
}
if (!source.includes("blackOpening:'englund'")) {
  throw new Error('ragebait black opening is not the default');
}
for (const option of [
  "value='bongcloud'", "value='halloween'", "value='steinitz'", "value='frankenstein'",
  "value='stafford'", "value='traxler'",
]) {
  if (!source.includes(option)) throw new Error(`troll opening selector is missing: ${option}`);
}
if (!source.includes('function selectedOpeningSettings()') || !source.includes('...openingSettings')) {
  throw new Error('opening selections are not sent to the analysis service');
}
if (!source.includes('review_finished:false')) {
  throw new Error('live overlay must not rewind a finished game onto the final board');
}
if (!source.includes("await localPost('/api/browser-position/reset'")) {
  throw new Error('pending browser tracker reset is not sent to the backend');
}
if (!source.includes("el('now').onclick=async()=>{markBrowserSessionReset()")) {
  throw new Error('manual analysis does not request a tracker reset');
}

// When an analysis slot is busy, a 429 must not become a server-offline error
// or trigger a second request that immediately hits the same semaphore.
if (!source.includes("if(error?.status===429)") ||
    !source.includes("Analyse bereits aktiv – erneuter Versuch folgt.") ||
    !source.includes("if(error.name==='AbortError'||error.status)throw error;") ||
    !source.includes("(!pending&&!currentResult&&Date.now()>=retryAfter)")) {
  throw new Error('busy analysis must be retried without a false connection error');
}

console.log('overlay round/style tests passed');
