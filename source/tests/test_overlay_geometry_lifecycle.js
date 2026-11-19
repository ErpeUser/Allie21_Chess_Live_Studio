const fs = require('fs');

const overlay = fs.readFileSync('source/app/browser/allie21_overlay.user.js', 'utf8');
const viewer = fs.readFileSync('source/app/viewer/index.html', 'utf8');

for (const token of [
  'new ResizeObserver(()=>requestRepaint())',
  'window.visualViewport?.addEventListener(\'resize\',requestRepaint',
  "history[method]=function(...args)",
  "resetBoardSession('navigation')",
  "svg.style.cssText='position:absolute;inset:0",
  'board.appendChild(svg)',
]) {
  if (!overlay.includes(token)) throw new Error(`overlay lifecycle guard missing: ${token}`);
}
for (const token of [
  'new ResizeObserver(refreshViewerGeometry)',
  "window.addEventListener('scroll',refreshViewerGeometry",
  "window.visualViewport?.addEventListener('resize',refreshViewerGeometry",
  "$('video').addEventListener('loadedmetadata',refreshViewerGeometry",
  'revision:geometryRevision',
]) {
  if (!viewer.includes(token)) throw new Error(`viewer geometry refresh missing: ${token}`);
}

console.log('overlay geometry/lifecycle tests passed');
