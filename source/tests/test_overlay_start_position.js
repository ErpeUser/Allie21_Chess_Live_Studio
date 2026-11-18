const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('source/app/browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('const START_PLACEMENT=');
const end = source.indexOf('function playerSideFor', start);
if (start < 0 || end < 0) throw new Error('start-position resolver missing');

const context = {};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

const standard = context.startPositionHistory({
  placement: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR',
  orientation: 'white',
});
if (!standard || standard.pgn !== '*' || !standard.ready || standard.moves_seen !== 0) {
  throw new Error(`standard start was not accepted immediately: ${JSON.stringify(standard)}`);
}

const changed = context.startPositionHistory({
  placement: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR',
  orientation: 'white',
});
if (changed !== null) throw new Error('non-start position was incorrectly bypassed');

const pending = context.pendingInsights(standard);
if (!pending || pending.plan_messages.length < 2 || !pending.plan_messages[0].includes('Startstellung')) {
  throw new Error(`start analysis did not get immediate content: ${JSON.stringify(pending)}`);
}

console.log('overlay start-position tests passed');
