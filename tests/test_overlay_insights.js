const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('browser/allie21_overlay.user.js', 'utf8');
const start = source.indexOf('function insightLines');
const end = source.indexOf('function show', start);
if (start < 0 || end < 0) throw new Error('insight helpers missing');

const context = {};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

const messages = [
  'Gespielt wird Ruy Lopez.',
  'Zur Stellung: Materiell ausgeglichen.',
  'Wahrscheinliche gegnerische Absicht: Druck auf e4.',
  'Konkrete Gefahr: Der rote Hauptzug kommt mit Schach.',
  'Spielverhalten: klarer Hauptplan.',
  'Pre-Move-Risiko: nicht blind ausfuehren.',
  'Diese siebte Zeile soll nicht mehr erscheinen.',
];
const visible = context.insightLines({plan_messages: messages});
if (JSON.stringify(visible) !== JSON.stringify(messages.slice(0, 6))) {
  throw new Error(`wrong insight lines: ${JSON.stringify(visible)}`);
}

const right = context.panelPosition({left: 200, right: 900, top: 80}, 1400, 900, 350);
if (right.left !== 912 || right.top !== 80) throw new Error(`wrong right placement: ${JSON.stringify(right)}`);
const left = context.panelPosition({left: 400, right: 1100, top: 40}, 1200, 900, 350);
if (left.left !== 38 || left.top !== 40) throw new Error(`wrong left placement: ${JSON.stringify(left)}`);

console.log('overlay insight tests passed');
