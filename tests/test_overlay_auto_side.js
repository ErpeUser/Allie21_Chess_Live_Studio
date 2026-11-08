const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('function playerSideFor(');
const end = source.indexOf('\n function ', start + 1);
if (start < 0 || end < 0) throw new Error('automatic player-side resolver not found');

function resolve(configured, orientation, detected) {
  const context = { cfg: { playerSide: configured }, orientation, detected, result: '' };
  vm.runInNewContext(source.slice(start, end) + '\nresult=playerSideFor(orientation, detected);', context);
  return context.result;
}

if (resolve('auto', 'black', 'white') !== 'white') throw new Error('detected white player color must override board orientation');
if (resolve('auto', 'white', 'black') !== 'black') throw new Error('detected black player color must override board orientation');
if (resolve('auto', 'black', '') !== 'black') throw new Error('black board side must be the fallback when no player marker exists');
if (resolve('auto', 'white', '') !== 'white') throw new Error('white board side must be the fallback when no player marker exists');
if (resolve('white', 'black', 'black') !== 'white') throw new Error('manual white override must be preserved');
