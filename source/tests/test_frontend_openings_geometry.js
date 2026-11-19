const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..', 'app');
const viewer = fs.readFileSync(path.join(repo, 'viewer', 'index.html'), 'utf8');
const overlay = fs.readFileSync(path.join(repo, 'browser', 'allie21_overlay.user.js'), 'utf8');

function requireSource(source, fragment, message) {
  if (!source.includes(fragment)) throw new Error(message || `missing source fragment: ${fragment}`);
}

// The two frontends must build opening settings from one normalized snapshot.
// This catches regressions where the GUI shows one value but a request sends a
// stale/default value (especially after a select is restored from settings).
requireSource(viewer, 'function selectedOpeningSettings()', 'viewer has no normalized opening settings helper');
requireSource(viewer, '...selectedOpeningSettings()', 'viewer requests do not use the selected opening snapshot');
requireSource(viewer, 'USER_SETTINGS_KEY', 'viewer settings are not persisted between starts');
requireSource(viewer, 'persistSettings()', 'viewer changes are not written to persistent settings');
requireSource(viewer, 'let viewerSessionId=makeViewerSessionId()', 'viewer overlay session id is not generated');
requireSource(viewer, 'function rotateViewerSession()', 'viewer overlay session is not rotated between captures');
requireSource(overlay, 'function selectedOpeningSettings()', 'browser overlay has no normalized opening settings helper');
requireSource(overlay, '...openingSettings', 'browser requests do not use the selected opening snapshot');

// Preferred and active opening names, retained settings, and legacy responses
// are exercised through production renderers in the two reliability suites.

// Keep arrow shafts inset for readability, but put the arrowhead tip exactly
// at the destination square center. This applies to every arrow, including the
// blue pre-move, because all of them share the same drawing function.
requireSource(viewer, 'tip=[ex,ey]', 'viewer arrowhead tip is not anchored to the target center');
requireSource(viewer, '[[tip[0],tip[1]]', 'viewer arrowhead polygon does not use the target center');
requireSource(overlay, 'tip=[u,v]', 'browser arrowhead tip is not anchored to the target center');
requireSource(overlay, '[[tip[0],tip[1]]', 'browser arrowhead polygon does not use the target center');
if (viewer.includes('[[end[0],end[1]]')) throw new Error('viewer arrowhead still ends at the inset shaft endpoint');
if (overlay.includes('[[tx,ty]]')) throw new Error('browser arrowhead still ends at the inset shaft endpoint');

// The blue continuation must continue through the shared draw path in both UIs.
requireSource(viewer, '[[result.premove].filter(Boolean)', 'viewer blue pre-move is not drawn through the common arrow path');
requireSource(overlay, 'if(data.premove)drawArrow', 'browser blue pre-move is not drawn through the common arrow path');

console.log('frontend opening/geometry tests passed');
