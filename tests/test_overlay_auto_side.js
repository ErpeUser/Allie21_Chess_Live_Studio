const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('function playerSideFor(');
const end = source.indexOf('\n function ', start + 1);
if (start < 0 || end < 0) throw new Error('automatic player-side resolver not found');

function resolve(configured, orientation) {
  const context = { cfg: { playerSide: configured }, orientation, result: '' };
  vm.runInNewContext(source.slice(start, end) + '\nresult=playerSideFor(orientation);', context);
  return context.result;
}

if (resolve('auto', 'black') !== 'black') throw new Error('black orientation must resolve to black');
if (resolve('auto', 'white') !== 'white') throw new Error('white orientation must resolve to white');
if (resolve('white', 'black') !== 'white') throw new Error('manual white override must be preserved');
