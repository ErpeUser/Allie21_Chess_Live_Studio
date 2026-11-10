// ==UserScript==
// @name         Allie 2.1 Live Studio v11 (Automatisches Live-Overlay)
// @namespace    local.allie21.study
// @version      11.2.17
// @description  Permanent Allie move, opponent and pre-move arrows on visible DOM chess boards.
// @match        https://chess.com/play/*
// @match        https://www.chess.com/play/*
// @match        https://www.chess.com/game/*
// @match        https://www.chess.com/analysis/*
// @match        https://www.chess.com/watch/*
// @match        https://www.chess.com/broadcast/*
// @match        https://lichess.org/*
// @run-at       document-idle
// @noframes
// ==/UserScript==
/*
  No auto-moves and never clicks on the chess site. The local service is bound
  to 127.0.0.1 and needs no account or access key.
*/
(() => {
 'use strict';
 if (window.top !== window.self || document.getElementById('allie21-auto-study-root')) return;
 const host=location.hostname.toLowerCase(),path=location.pathname;
 const supportedHost=host==='lichess.org'||host==='chess.com'||host==='www.chess.com';
 const supportedPath=host==='lichess.org'
   ? /^(?:\/game\/[A-Za-z0-9]{8,16}(?:\/|$)|\/[A-Za-z0-9]{8}(?:\/|$)|\/(?:analysis|study|broadcast|tv)(?:\/|$))/.test(path)
   : /^(?:\/(?:play|game|analysis|watch|broadcast)(?:\/|$))/.test(path);
 if(!supportedHost||!supportedPath)return;
 const STORE='allie21.auto.v11';
 const PRIVATE_STORE='allie21.private.v1';
 const readObject=key=>{try{const value=JSON.parse(localStorage.getItem(key)||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{}}catch{return{}}};
 const load=()=>readObject(STORE);
 const loadPrivate=()=>readObject(PRIVATE_STORE);
 const stored=load();
 const privateStored=loadPrivate();
 const cfg=Object.assign({elo:1950,tc:'300+0',port:8765,enabled:true,orientation:'auto',playerSide:'auto',playerSideMode:'auto',playStyle:'normal',whiteOpening:'grob',blackOpening:'englund',privateMode:true},stored);
 cfg.privateMode=typeof privateStored.privateMode==='boolean'?privateStored.privateMode:
   typeof stored.privateMode==='boolean'?stored.privateMode:true;
 if(!stored.playerSideMode){cfg.playerSide='auto';cfg.playerSideMode='auto'}
 const ARROW_COLORS=Object.freeze({ownTop1:'#16c784',ownTop2:'#7ee2b8',opponentTop1:'#ef3340',opponentTop2:'#ff9299',premove:'#2f80ed'});
 const save=()=>{try{localStorage.setItem(STORE,JSON.stringify(cfg))}catch{}};
 const wrapper=document.createElement('div');
 wrapper.id='allie21-auto-study-root';
 wrapper.style.cssText='all:initial;display:none;position:fixed;right:18px;bottom:18px;z-index:2147483000;font-family:Inter,ui-sans-serif,system-ui,"Segoe UI",sans-serif;color:#f7ead8';
 document.documentElement.appendChild(wrapper);
 const shadow=wrapper.attachShadow({mode:'open'});
 shadow.innerHTML=`
 <style>
 *{box-sizing:border-box}button,input,select{font:inherit}#bubble{background:#4b3426;color:#fff3e2;border:1px solid #a77a4d;border-radius:999px;padding:10px 14px;font-size:12px;font-weight:650;cursor:pointer;box-shadow:0 6px 18px #1a0e088c,0 0 0 1px #f2d4a522 inset;letter-spacing:.01em}#bubble:before{content:'';display:inline-block;width:7px;height:7px;margin-right:7px;border-radius:50%;background:#d6ad67;box-shadow:0 0 8px #d6ad67}
 #panel{display:none;width:360px;max-width:calc(100vw - 20px);max-height:76vh;overflow:auto;background:#2a1d17f7;color:#f7ead8;border:1px solid #806044;box-shadow:0 18px 42px #160b08bf,0 0 0 1px #f2d4a51a inset;border-radius:14px;padding:16px;line-height:1.45;font-size:12px;backdrop-filter:blur(10px)}
 #panel.open{display:block}h3{margin:10px 0 5px;color:#e1bd7c;font-size:13px}p{margin:6px 0}label{display:block;margin:8px 0 4px;color:#dfc7ab}.row{display:flex;gap:9px;align-items:center}.row>*{flex:1;min-width:0}#close{flex:0 0 32px;padding:6px;background:transparent;color:#f7ead8;border-color:#8c694d}input,select{width:100%;min-height:38px;padding:8px 9px;background:#1d1410;border:1px solid #72543d;border-radius:8px;color:#f8eee3}input:focus,select:focus{outline:2px solid #c99a5c;outline-offset:1px}
 button{min-height:38px;border:1px solid #8b6546;background:#704c32;color:#fff3e2;border-radius:8px;padding:7px;cursor:pointer;transition:background .15s ease,border-color .15s ease}button:hover{background:#8a5d3a;border-color:#b78755}.item{display:flex;gap:8px;justify-content:space-between;border-bottom:1px solid #604631;padding:7px 0}.stat{color:#d2b991}.warn{color:#f0b28c}.small{font-size:11px;color:#c5ab8b}#results{margin-top:10px}.insight{background:#39271d;border:1px solid #694b35;border-radius:9px;margin:8px 0;padding:10px 11px;box-shadow:0 4px 12px #180c081f}.analysis-title{display:flex;justify-content:space-between;align-items:center;color:#e1bd7c;font-weight:700;margin-top:11px}
 </style>
 <button id='bubble'>Allie · Analyse</button>
 <section id='panel'><div class='row'><b style='font-size:15px'>Allie Live-Analyse</b><button id='close' aria-label='Fenster schließen'>×</button></div>
 <p class='small'>Allie schätzt menschliche Züge. Stockfish prüft sie objektiv.</p>
 <div class='row'><div><label>Elo</label><input id='elo' type='number' min='600' max='2800'/></div>
  <div><label>Zeitkontrolle</label><input id='tc' placeholder='300+0'/></div></div>
 <label>Lokaler Server-Port</label><input id='port' type='number' min='1024' max='65535' step='1' title='Muss mit ALLIE_PORT übereinstimmen'/>
 <div class='row'><div><label>Brettorientierung</label><select id='orientation'><option value='auto'>Automatisch</option><option value='white'>Weiss unten</option><option value='black'>Schwarz unten</option></select></div>
 <div><label>Deine Farbe</label><select id='playerSide'><option value='auto'>Automatisch</option><option value='white'>Weiss</option><option value='black'>Schwarz</option></select></div></div>
 <label>Spielstil</label><select id='playStyle'><option value='normal'>Normal · menschlich wahrscheinlich</option><option value='aggressive'>Aggressiv · Matt und Königsdruck</option></select>
 <div class='row'><div><label>Weißes Opening</label><select id='whiteOpening'><option value='grob'>Grob Gambit · Ragebait</option><option value='bongcloud'>Bongcloud</option><option value='halloween'>Halloween-Gambit</option><option value='vienna'>Wiener Gambit</option><option value='steinitz'>Steinitz-Gambit</option><option value='frankenstein'>Frankenstein-Dracula</option><option value='danish'>Dänisches Gambit</option></select></div>
  <div><label>Schwarzes Opening</label><select id='blackOpening'><option value='englund'>Englund Gambit · Ragebait</option><option value='stafford'>Stafford-Gambit</option><option value='traxler'>Traxler-Gegenangriff</option><option value='budapest'>Budapester Gambit</option><option value='alekhine'>Aljechin-Verteidigung</option></select></div></div>
 <div class='row' style='margin-top:8px'><button id='toggle'>Live-Hinweise: Ein</button><button id='now'>Jetzt analysieren</button></div>
 <label class='private-row'><input id='privateMode' type='checkbox'> Privater Modus (keine DOM-/SVG-HUDs)</label>
 <button id='retryPrivate' type='button'>Privates Overlay erneut pruefen</button>
 <p id='privateStatus' class='small'>Privater Modus aktiv: Visualisierung bleibt außerhalb der Webseite.</p>
 <p id='status' class='stat'>Warte auf ein Brett. Die Verbindung startet automatisch.</p>
 <div id='results'></div><p class='small'>Starkgrün: Mein Top 1 · Hellgrün: Mein Top 2<br>Starkrot: Gegner Top 1 · Hellrot: Gegner Top 2<br>Blau: Sicherer Pre-Move (bedingt): gilt nur fuer die vorhergesagte Fortsetzung, nicht garantiert. Allie klickt nie selbst.</p>
 </section>`;
 const el=id=>shadow.getElementById(id);
 const OPENING_VALUES=Object.freeze({white:['grob','bongcloud','halloween','vienna','steinitz','frankenstein','danish'],black:['englund','stafford','traxler','budapest','alekhine']});
 for(const [side,legacy] of [['white','whiteOpening'],['black','blackOpening']]){
  const choice=stored['opening_'+side]??stored[legacy];
  cfg[legacy]=OPENING_VALUES[side].includes(choice)?choice:(side==='white'?'grob':'englund');
 }
 function persistOpeningSelection(){const selected=selectedOpeningSettings();Object.assign(cfg,selected,{whiteOpening:selected.opening_white,blackOpening:selected.opening_black});}
 function selectedOpeningSettings(){const white=el('whiteOpening').value,black=el('blackOpening').value;return{opening_white:OPENING_VALUES.white.includes(white)?white:'grob',opening_black:OPENING_VALUES.black.includes(black)?black:'englund'}}
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let pending=false,lastPGN='',currentResult=null,retryAfter=0,busyRetries=0,lastPlacement='',trackedPGN='',trackedFen='',trackingPending=false,currentBoard=null,analysisKey='',tickTimer=0,activeRequest=null,analysisSerial=0,unsettledPlacement='',unsettledRetries=0,panelDismissed=false,visualRevision=0,visualRequest=null,repaintFrame=0,boardResizeObserver=null,observedBoard=null,boardAnimationHandlers=[],renderedBoard=null,renderedSvg=null,renderedPosition='',renderedInlinePosition='',privateUnavailable=false;
 const cancelAnalysis=()=>{analysisSerial++;if(activeRequest){activeRequest.abort();activeRequest=null}pending=false};
 el('bubble').onclick=()=>{panelDismissed=false;el('panel').classList.add('open');el('bubble').style.display='none';placePanel()};
 el('close').onclick=()=>{panelDismissed=true;el('panel').classList.remove('open');el('bubble').style.display=''};
 const invalidate=()=>{cancelAnalysis();busyRetries=0;lastPGN='';trackedFen='';analysisKey='';currentResult=null;clearOverlay();show({});clearRemoteOverlay('stale')};
 const normalizePort=value=>{const port=Number(value);return Number.isInteger(port)&&port>=1024&&port<=65535?port:8765};
 cfg.port=normalizePort(cfg.port);
 const updateSettings=()=>{cfg.elo=Number(el('elo').value)||1950;cfg.tc=el('tc').value.trim()||'300+0';cfg.port=normalizePort(el('port').value);cfg.orientation=el('orientation').value;cfg.playerSide=el('playerSide').value;cfg.playerSideMode=cfg.playerSide==='auto'?'auto':'manual';cfg.playStyle=el('playStyle').value;persistOpeningSelection();save();setServicePort(cfg.port);try{chrome?.storage?.local?.set?.({port:cfg.port})}catch{};invalidate();scheduleTick(true)};
 for(const field of ['elo','tc','port','orientation','playerSide','playStyle','whiteOpening','blackOpening'])el(field).addEventListener('change',updateSettings);
 const fill=()=>{el('results').hidden=Boolean(cfg.privateMode);el('elo').value=cfg.elo;el('tc').value=cfg.tc;el('port').value=cfg.port;el('orientation').value=cfg.orientation;el('playerSide').value=cfg.playerSide;el('playStyle').value=cfg.playStyle;el('whiteOpening').value=cfg.whiteOpening;el('blackOpening').value=cfg.blackOpening;el('toggle').textContent=`Live-Hinweise: ${cfg.enabled?'Ein':'Aus'}`;el('privateMode').checked=cfg.privateMode;el('privateStatus').textContent=cfg.privateMode?(privateUnavailable?'Privates Overlay nicht bereit. Hinweise bleiben verborgen; erneut pruefen oder bewusst ausschalten.':'Privater Modus angefordert: Hinweise nur im verifizierten Windows-Overlay.'):'Privater Modus aus: DOM-/SVG-HUDs sind sichtbar.'};fill();
 persistOpeningSelection();save();
 el('toggle').onclick=()=>{cfg.enabled=!cfg.enabled;save();fill();invalidate();if(cfg.enabled)scheduleTick(true)};
 el('privateMode').onchange=()=>{cfg.privateMode=Boolean(el('privateMode').checked);try{localStorage.setItem(PRIVATE_STORE,JSON.stringify({privateMode:cfg.privateMode}))}catch{};fill();invalidate();sendOverlayMode(cfg.privateMode?'private':'normal');if(!cfg.privateMode)scheduleTick(true)};
 el('retryPrivate').onclick=()=>syncPrivateMode(true);
 let sessionHash=Date.now()>>>0;
  let boardSessionId='web-'+(crypto.randomUUID?.()||Math.random().toString(36).slice(2)),overlayOwnerToken='';
 const selectors=['wc-simple-move-list [data-node]','wc-vertical-move-list [data-node]','wc-horizontal-move-list [data-node]','wc-move-list [data-node]','wc-move-list .main-line-ply','wc-move-list .move','wc-move-list [data-ply]','wc-move-list .node','wc-move-list [class*="move-node"]','wc-move-list button','wc-simple-move-list [data-ply]','wc-simple-move-list .node','wc-simple-move-list [class*="move"]','wc-simple-move-list button','wc-vertical-move-list [data-ply]','wc-vertical-move-list [class*="move"]','wc-vertical-move-list button','[data-cy="move-list"] [data-ply]','[data-cy="move-list"] [class*="move"]','[class*="move-list"] button','l4x l4','l4x move','.analyse__moves move','.analyse__moves .san','.vertical-move-list .move','.move-list .move','.move-list-component .move','.pgn-viewer .san','.analysis-moves .san','.move-text-component'];
 const sanPattern=/^(?:O-O(?:-O)?|0-0(?:-0)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?|[a-h][1-8][+#]?)$/;
 // Lichess changes its short custom tag names regularly. Locate the current
 // mainline structurally via the rewind-to-ply-0 control instead of tag names.
 function structuralMoveRoot(){
  const rewind=document.querySelector('button[data-ply="0"]');
  const candidate=rewind?.parentElement?.nextElementSibling;
  const roots=[];
  if(candidate?.children?.length>=2)roots.push(candidate);
  for(const selector of ['.analyse__moves','.vertical-move-list','.move-list','[data-cy="move-list"]','[class*="move-list"]']){
   for(const root of Array.from(document.querySelectorAll(selector)))if(root.children?.length>=2&&!roots.includes(root))roots.push(root);
  }
  let best=null,bestCount=0;
  for(const root of roots){
   const moves=typeof movesFromRoot==='function'?movesFromRoot(root):movesFromNodes(root.children);
   if(moves.length>bestCount){best=root;bestCount=moves.length}
  }
  return bestCount>=2?best:null;
 }
 const figurines={'♔':'K','♕':'Q','♖':'R','♗':'B','♘':'N','♚':'K','♛':'Q','♜':'R','♝':'B','♞':'N'};
 function nodeMoveText(node){
  let out='';
  const walk=item=>{
   if(item?.nodeType===3){out+=item.textContent||'';return}
   if(!item)return;
   const cls=String(item.className||item.getAttribute?.('class')||'').toLowerCase();
   if(/icon-font-chess|figurine|move-piece/.test(cls)){
    const piece=/\bknight\b/.test(cls)?'N':/\bbishop\b/.test(cls)?'B':/\brook\b/.test(cls)?'R':/\bqueen\b/.test(cls)?'Q':/\bking\b/.test(cls)?'K':'';
    out+=piece;return;
   }
   const children=Array.from(item.childNodes||[]);
   if(children.length)for(const child of children)walk(child);else out+=item.textContent||'';
  };
  walk(node);return out;
 }
 function cleanMove(text,node){
  let value=String(text||'').trim().replace(/^\d+(?:\.{1,3})?\s*/,'').replace(/[!?]+/g,'').replace(/\s+/g,'');
  value=value.replace(/^[♔♕♖♗♘♚♛♜♝♞]/,piece=>figurines[piece]);
  if(/^[a-h][1-8](?:x[a-h][1-8])?(?:=[QRBN])?[+#]?$/.test(value)&&node){
   const owner=node.closest?.('button,[data-ply],[data-node],[data-san],move,l4,.main-line-ply,.move,.node')||node;
   const descendants=Array.from(owner.querySelectorAll?.('[data-figurine],[data-piece],[class*="knight"],[class*="bishop"],[class*="rook"],[class*="queen"],[class*="king"]')||[]).slice(0,5);
   const signature=[owner,node,...descendants].map(n=>`${n.getAttribute?.('data-figurine')||''} ${n.getAttribute?.('data-piece')||''} ${String(n.className||'')}`).join(' ').toLowerCase();
   const tokens=signature.split(/\s+/).map(part=>part.replace(/[^a-z]/g,'')).filter(Boolean);
   const coded=tokens.map(part=>/^(?:[wb])?([nbrqk])$/.exec(part)?.[1]).find(Boolean);
   const piece=/knight/.test(signature)||coded==='n'?'N':/bishop/.test(signature)||coded==='b'?'B':/rook/.test(signature)||coded==='r'?'R':/queen/.test(signature)||coded==='q'?'Q':/king/.test(signature)||coded==='k'?'K':'';
   if(piece)value=piece+value;
  }
  return value;
 }
 function movesFromNodes(nodes){
  const ordered=Array.from(nodes).slice(0,1100).map((node,index)=>{const raw=node.getAttribute?.('data-ply'),dataNode=node.getAttribute?.('data-node'),match=/^0-(\d+)$/.exec(dataNode||'');const ply=raw==null||raw===''?(match?Number(match[1]):NaN):Number(raw);return{node,index,ply}});
  if(ordered.some(item=>Number.isFinite(item.ply)))ordered.sort((a,b)=>(Number.isFinite(a.ply)?a.ply:1e9)-(Number.isFinite(b.ply)?b.ply:1e9)||a.index-b.index);
  const compact=[];
  for(const {node} of ordered){const move=cleanMove(node.getAttribute?.('data-san')||nodeMoveText(node),node);if(sanPattern.test(move))compact.push(move)}
  return compact;
 }
 function movesFromRoot(root){
  const preferred=root.querySelectorAll?.('[data-ply],[data-node],[data-san],button,[role="button"],.main-line-ply,.move,.node,.san,[class*="move-node"],[class*="move-text"],[class*="move-san"]')||[];
  let moves=movesFromNodes(preferred);
  const leaves=Array.from(root.querySelectorAll?.('span,div,button,move,l4')||[]).filter(n=>n.children.length===0&&cleanMove(n.textContent,n));
  const leafMoves=movesFromNodes(leaves);if(leafMoves.length>moves.length)moves=leafMoves;
  const compact=[];for(const move of moves)if(move!==compact.at(-1))compact.push(move);
  return compact;
 }
 function candidateMoveRoots(){
  const rootSelectors=['wc-move-list','wc-simple-move-list','wc-vertical-move-list','wc-horizontal-move-list','.analyse__moves','.vertical-move-list','.move-list','.move-list-component','.pgn-viewer','.analysis-moves','[data-cy="move-list"]','[class*="move-list"]'];
  const roots=Array.from(document.querySelectorAll(rootSelectors.join(',')));
  return Array.from(new Set(roots)).filter(root=>!root.closest('#allie21-auto-study-root'));
 }
 function historyText(moves){return moves.map((m,i)=>i%2===0?`${1+i/2}. ${m}`:m).join(' ')}
 function readHistoryCandidates(){
  const found=[],add=moves=>{if(moves.length)found.push(moves)};
  for(const sel of selectors){
    add(movesFromNodes(document.querySelectorAll(sel)));
  }
  const structural=structuralMoveRoot();
  if(structural)add(movesFromNodes(structural.children));
  for(const root of candidateMoveRoots()){
   add(movesFromRoot(root));
  }
  // Python accepts this candidate only when every move is legal from the
  // standard start and the final placement equals the visible board. A
  // virtualised fragment therefore cannot create a false history.
  // Exact, indexed move-list selectors are added first. Keep that priority:
  // broad descendants can duplicate moves and must never crowd the valid SAN
  // mainline out of the bounded request.
  const candidates=Array.from(new Set(found.map(historyText))).sort((a,b)=>b.split(/\s+/).length-a.split(/\s+/).length).slice(0,16);
  return candidates.length?candidates:isStandardStartPosition()?['*']:[];
 }
 function readHistory(){return readHistoryCandidates()[0]||''}
 function chessComGameId(){
  const match=/\/game\/(?:live\/)?(\d+)/.exec(location.pathname);
  return /\.chess\.com$/.test('.'+location.hostname)&&match?match[1]:'';
 }
 function pieceCode(node){
  const attrs=['data-piece','data-figurine','data-color','data-role','aria-label','alt','src'].map(name=>node.getAttribute?.(name)||'').join(' ');
  const style=(node.getAttribute?.('style')||'')+' '+(getComputedStyle(node).backgroundImage||'');
  const signature=(String(node.className||'')+' '+attrs+' '+style).toLowerCase().replace(/[_./-]+/g,' ');
  let color=/\bwhite\b|\blight\b/.test(signature)?'w':/\bblack\b|\bdark\b/.test(signature)?'b':'';
  let type=/\bpawn\b/.test(signature)?'p':/\bknight\b/.test(signature)?'n':/\bbishop\b/.test(signature)?'b':/\brook\b/.test(signature)?'r':/\bqueen\b/.test(signature)?'q':/\bking\b/.test(signature)?'k':'';
  for(const raw of [signature,String(node.className||''),node.getAttribute?.('data-piece')||'',node.getAttribute?.('data-figurine')||'']){
   for(const part of raw.split(/\s+/)){
    const normalized=part.toLowerCase().replace(/[^a-z]/g,'');
    const match=/^([wb])([prnbqk])$/.exec(normalized)||/^([wb])(pawn|rook|knight|bishop|queen|king)$/.exec(normalized);
    if(match){color=match[1];type={pawn:'p',rook:'r',knight:'n',bishop:'b',queen:'q',king:'k'}[match[2]]||match[2]}
   }
  }
  return color&&type?color+type:'';
 }
 function boardQueryAll(board,selector){
  const roots=[],seen=new Set(),addRoot=root=>{if(root&&!seen.has(root)){seen.add(root);roots.push(root)}};
  addRoot(board);addRoot(board?.shadowRoot);
  for(let index=0;index<roots.length;index++){
   const root=roots[index];
   for(const element of Array.from(root.querySelectorAll?.('*')||[]))addRoot(element.shadowRoot);
  }
  return Array.from(new Set(roots.flatMap(root=>Array.from(root.querySelectorAll?.(selector)||[]))));
 }
 function pieceNodes(board){
  const selector='piece,.piece,[data-piece],[data-figurine],img[alt*="pawn" i],img[alt*="knight" i],img[alt*="bishop" i],img[alt*="rook" i],img[alt*="queen" i],img[alt*="king" i],[aria-label*="pawn" i],[aria-label*="knight" i],[aria-label*="bishop" i],[aria-label*="rook" i],[aria-label*="queen" i],[aria-label*="king" i]';
  return boardQueryAll(board,selector).filter(node=>pieceCode(node)&&!isTransientPieceNode(node));
 }
 function boardOrientation(board,pieces){
  if(cfg.orientation!=='auto')return cfg.orientation;
  const attribute=(board?.getAttribute?.('data-orientation')||'').trim().toLowerCase();
  if(attribute==='black')return 'black';if(attribute==='white')return 'white';
  const explicit=(board?.parentElement?.className||'')+' '+(board?.className||'');
  if(/\b(flipped|orientation-black|black-bottom|board-layout-flipped)\b/i.test(explicit)&&!/orientation-white/i.test(explicit))return 'black';
  const scoped=board?.closest?.('.orientation-black,.orientation-white,.board-layout-flipped,.chess-board.flipped,.board.flipped,cg-wrap');
  const scopedClass=String(scoped?.className||'');
  if(/\b(orientation-black|board-layout-flipped|flipped)\b/i.test(scopedClass)&&!/orientation-white/i.test(scopedClass))return 'black';
  if(/\borientation-white\b/i.test(scopedClass))return 'white';
  const white=[],black=[];for(const piece of pieces||[]){const code=pieceCode(piece),r=piece.getBoundingClientRect();if(code[0]==='w')white.push(r.top+r.height/2);if(code[0]==='b')black.push(r.top+r.height/2)}
  if(white.length&&black.length){const avg=a=>a.reduce((x,y)=>x+y,0)/a.length;return avg(white)>avg(black)?'white':'black'}
  return 'white';
 }
 function isTransientPieceNode(piece){return /\b(?:fading|ghost)\b/i.test(String(piece?.className||''))}
 function authoritativePieceSquare(piece,board,ori){
  if(isTransientPieceNode(piece))return null;
  const square=/\bsquare-([1-8])([1-8])\b/.exec(String(piece?.className||''));
  if(square)return{file:Number(square[1])-1,rank:Number(square[2])-1};
  if(String(board?.tagName||'').toLowerCase()!=='cg-board'||String(piece?.tagName||'').toLowerCase()!=='piece')return null;
  const style=piece.getAttribute?.('style')||'';
  const move=/translate(?:3d)?\(\s*(-?\d+(?:\.\d+)?)(px|%)\s*,\s*(-?\d+(?:\.\d+)?)(px|%)/i.exec(style);
  if(!move)return null;
  const rect=board.getBoundingClientRect(),toPixels=(value,unit,size)=>Number(value)*(unit==='%'?size/800:1);
  const col=Math.round(toPixels(move[1],move[2],rect.width)/(rect.width/8));
  const row=Math.round(toPixels(move[3],move[4],rect.height)/(rect.height/8));
  if(col<0||col>7||row<0||row>7)return null;
  return{file:ori==='black'?7-col:col,rank:ori==='black'?row:7-row};
 }
 let pendingBoardPlacement='',pendingBoardSince=0;
 function boardFrameIsStable(placement,now=Date.now()){
  if(placement!==pendingBoardPlacement){pendingBoardPlacement=placement;pendingBoardSince=now;return false}
  return now-pendingBoardSince>=220;
 }
 function placementFromBoard(board){
  const rect=board.getBoundingClientRect(),pieces=pieceNodes(board),ori=boardOrientation(board,pieces),square=rect.width/8;
  if(rect.width<130||rect.height<130||Math.abs(rect.width-rect.height)>Math.max(rect.width,rect.height)*.12)return null;
  const found=new Map();let authoritative=0;
  for(const piece of pieces){
   const code=pieceCode(piece),r=piece.getBoundingClientRect();
   if(!code||r.width<2||r.height<2||r.width>square*1.8||r.height>square*1.8)continue;
   const target=authoritativePieceSquare(piece,board,ori);let file,rank;
   if(target){({file,rank}=target);authoritative++}else{
    const px=r.left+r.width/2,py=r.top+r.height/2;if(px<rect.left||px>rect.right||py<rect.top||py>rect.bottom)continue;
    const col=Math.max(0,Math.min(7,Math.floor((px-rect.left)/square))),row=Math.max(0,Math.min(7,Math.floor((py-rect.top)/square)));
    file=ori==='black'?7-col:col;rank=ori==='black'?row:7-row;
   }
   const key=rank*8+file;
   if(found.has(key)&&found.get(key)!==code)return null;found.set(key,code);
  }
  const values=Array.from(found.values());if(values.filter(x=>x==='wk').length!==1||values.filter(x=>x==='bk').length!==1||values.length<4||values.length>32)return null;
  const ranks=[];for(let rank=7;rank>=0;rank--){let empty=0,text='';for(let file=0;file<8;file++){const code=found.get(rank*8+file);if(!code){empty++;continue}if(empty){text+=empty;empty=0}text+=code[0]==='w'?code[1].toUpperCase():code[1]}if(empty)text+=empty;ranks.push(text)}
  return {placement:ranks.join('/'),orientation:ori,pieces:values.length,authoritative:authoritative===values.length};
 }
 function boardCandidates(){
  const selector='cg-board,wc-chess-board,chess-board,.chessboard,[data-chess-board],.analyse__board,.board,[class*="chess-board"],[class*="chessboard"],[id*="chessboard"],[role="grid"]';
  const sortByArea=(a,b)=>{const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return y.width*y.height-x.width*x.height};
  return Array.from(document.querySelectorAll(selector)).filter(node=>!node.closest('#allie21-auto-study-root')).sort(sortByArea);
 }
 function readBoardSnapshot(){
   if(currentBoard?.isConnected){const snapshot=placementFromBoard(currentBoard);if(snapshot)return{board:currentBoard,...snapshot}}
   for(const board of boardCandidates()){const snapshot=placementFromBoard(board);if(snapshot){currentBoard=board;return{board,...snapshot}}}
   currentBoard=null;return null;
 }
 function boardElement(){return readBoardSnapshot()?.board||null;}
 function isStandardStartPosition(){
  return readBoardSnapshot()?.placement==='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR';
 }
 const layer=document.createElement('div');
 layer.style.cssText='position:fixed;inset:0;z-index:2147482999;pointer-events:none;overflow:hidden';
  document.documentElement.appendChild(layer);
  function requestRepaint(){
   if(repaintFrame)return;
   const run=()=>{repaintFrame=0;if(currentResult)paint(currentResult);else if(currentBoard)sendVisualUpdate('stale')};
   if(typeof requestAnimationFrame==='function')repaintFrame=requestAnimationFrame(run);else repaintFrame=setTimeout(run,0);
  }
  function observeBoardGeometry(board){
   if(board===observedBoard)return;
   boardResizeObserver?.disconnect?.();for(const [event,handler] of boardAnimationHandlers)observedBoard?.removeEventListener?.(event,handler);boardAnimationHandlers=[];observedBoard=board||null;
   if(!board||typeof ResizeObserver!=='function')return;
   boardResizeObserver=new ResizeObserver(()=>requestRepaint());
   boardResizeObserver.observe(board);
   for(const event of ['transitionrun','transitionstart','transitionend','animationstart','animationiteration','animationend']){const handler=()=>requestRepaint();board.addEventListener?.(event,handler,{passive:true});boardAnimationHandlers.push([event,handler])}
  }
 function visualGeometry(board){
  const rect=board?.getBoundingClientRect?.();
  const dpr=Number(window.devicePixelRatio||1),viewport={width:window.innerWidth,height:window.innerHeight};
  if(!rect)return{viewport,device_pixel_ratio:dpr,board:null};
  const boardRect={left:Math.round(rect.left),top:Math.round(rect.top),width:Math.round(rect.width),height:Math.round(rect.height)};
  // Browser chrome is an estimate; real mixed-DPI capture still needs Windows acceptance.
  const border=Math.max(0,((Number(window.outerWidth)||window.innerWidth)-window.innerWidth)/2);
  const chromeTop=Math.max(0,(Number(window.outerHeight)||window.innerHeight)-window.innerHeight-border);
  const screenBoard={left:Math.round((Number(window.screenX||0)+border+rect.left)*dpr),top:Math.round((Number(window.screenY||0)+chromeTop+rect.top)*dpr),width:Math.round(rect.width*dpr),height:Math.round(rect.height*dpr)};
  const orientation=typeof boardOrientation==='function'?boardOrientation(board,pieceNodes(board)):'white';
  return{viewport,device_pixel_ratio:dpr,board:boardRect,screen_board:screenBoard,orientation};
 }
 function visualSource(){return /(^|\.)lichess\.org$/.test(location.hostname)?'lichess_dom':/\.chess\.com$/.test('.'+location.hostname)?'chesscom_dom':'unknown'}
 function shortAnalysisKey(value){let hash=2166136261;for(const char of String(value||'')){hash^=char.charCodeAt(0);hash=Math.imul(hash,16777619)}return (hash>>>0).toString(16).padStart(8,'0')}
 function visualArrows(data){
  const out=[];
  for(const [items,color] of [[(data?.opponent_moves||[]).slice(0,2),[ARROW_COLORS.opponentTop1,ARROW_COLORS.opponentTop2]],[(data?.my_moves||[]).slice(0,2),[ARROW_COLORS.ownTop1,ARROW_COLORS.ownTop2]],[[data?.premove].filter(Boolean),[ARROW_COLORS.premove]]])for(const [index,item] of items.entries())if(/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(item?.uci||''))out.push({uci:item.uci,color:color[index]||color[0],opacity:index?0.65:0.96});
  return out.slice(0,8);
 }
 function visualPayload(mode='stale',data={}){
  const board=boardElement();
   return{schema_version:1,session_id:boardSessionId,owner_token:overlayOwnerToken,generation:analysisSerial,render_revision:++visualRevision,analysis_key:shortAnalysisKey(analysisKey),fen:data?.fen||'',mode,source:visualSource(),geometry:visualGeometry(board),arrows:visualArrows(data),messages:insightLines(data),visible:mode==='normal'&&!cfg.privateMode&&cfg.enabled};
 }
 let pendingVisualUpdate=null;
 function sendVisualUpdate(mode='stale',data={}){
  if(!cfg.privateMode||!cfg.enabled||document.hidden||(!cfg.privateMode&&document.hasFocus?.()===false))return;
  if(cfg.privateMode&&!overlayOwnerToken){pendingVisualUpdate={mode,data};return;}
  const payload=visualPayload(mode,data);
  visualRequest?.abort?.();
  const request=postJson('/api/overlay/update',payload,4000);
  visualRequest=request;
  request.promise.catch(()=>{}).finally(()=>{if(visualRequest===request)visualRequest=null});
 }
 function applyPrivateStatus(state){
  privateUnavailable=cfg.privateMode&&!(state?.available===true&&state?.capture_excluded===true&&state?.mode==='private');
  fill();
  if(privateUnavailable&&state?.reason)el('privateStatus').textContent+=' '+String(state.reason).slice(0,160);
  if(cfg.privateMode){el('results').replaceChildren();clearOverlay();}
 }
  function sendOverlayMode(mode){
   if(mode!=='private'&&!overlayOwnerToken)return Promise.resolve(null);
   const claim=mode==='private'?postJson('/api/overlay/claim',{session_id:boardSessionId},6000).promise.then(lease=>{overlayOwnerToken=lease.owner_token}):Promise.resolve();
   return claim.then(()=>postJson('/api/overlay/mode',{session_id:boardSessionId,owner_token:overlayOwnerToken,mode},6000).promise).then(state=>{
    if((mode==='private')===cfg.privateMode)applyPrivateStatus(state);
    if(mode==='private'&&cfg.privateMode&&overlayOwnerToken&&pendingVisualUpdate){const queued=pendingVisualUpdate;pendingVisualUpdate=null;sendVisualUpdate(queued.mode,queued.data)}
    if(mode!=='private'&&overlayOwnerToken){postJson('/api/overlay/release',{session_id:boardSessionId,owner_token:overlayOwnerToken},4000).promise.catch(()=>{});overlayOwnerToken='';}
    return state;
  }).catch(error=>{if(cfg.privateMode)applyPrivateStatus({available:false,reason:error.message});return null;});
 }
 function clearRemoteOverlay(reason='stale'){
  if(!cfg.privateMode||!overlayOwnerToken)return;
  visualRequest?.abort?.();visualRequest=null;
   postJson('/api/overlay/clear',{session_id:boardSessionId,owner_token:overlayOwnerToken,generation:analysisSerial,render_revision:++visualRevision,reason},4000).promise.catch(()=>{});
 }
 function clearOverlay(){layer.replaceChildren();if(renderedSvg?.isConnected)renderedSvg.remove();if(renderedBoard&&renderedPosition){renderedBoard.style.position=renderedInlinePosition}renderedBoard=null;renderedSvg=null;renderedPosition='';renderedInlinePosition='';layer.style.display=cfg.privateMode?'none':'';wrapper.style.display=cfg.privateMode?'':'none';if(cfg.privateMode)el('results').replaceChildren()}
 function center(s,rect,ori){let file=s.charCodeAt(0)-97,rank=Number(s[1])-1;if(ori==='black'){file=7-file}else{rank=7-rank}return [rect.left+(file+.5)*rect.width/8,rect.top+(rank+.5)*rect.height/8]}
 function drawArrow(svg,rect,ori,uci,color,opacity=.87){
  if(!/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(uci||''))return;
  const [x,y]=center(uci.slice(0,2),rect,ori),[u,v]=center(uci.slice(2,4),rect,ori);
  const dx=u-x,dy=v-y,norm=Math.max(1,Math.hypot(dx,dy)),ux=dx/norm,uy=dy/norm;
  const sx=x+ux*rect.width/22,sy=y+uy*rect.width/22,tx=u-ux*rect.width/18,ty=v-uy*rect.width/18;
  const mk=(tag,props)=>{let a=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(props).forEach(([k,val])=>a.setAttribute(k,val));svg.appendChild(a)};
  const width=Math.max(4,Math.min(10,rect.width/72));
  mk('line',{x1:sx,y1:sy,x2:tx,y2:ty,stroke:color,'stroke-width':width,'stroke-linecap':'round',opacity});
  let angle=Math.atan2(dy,dx),size=Math.max(14,Math.min(30,rect.width/22)),tip=[u,v];
  let points=[[tip[0],tip[1]],[tip[0]-size*Math.cos(angle-.48),tip[1]-size*Math.sin(angle-.48)],[tip[0]-size*Math.cos(angle+.48),tip[1]-size*Math.sin(angle+.48)]];
  mk('polygon',{points:points.map(p=>p.join(',')).join(' '),fill:color,opacity});
 }
 function atHistoryEnd(){
   // If a visible move is selected earlier in the score, arrows for the last
   // move would point at a DIFFERENT board. Suppress rather than mislead.
   for(const sel of ['l4x move','.analyse__moves move','wc-move-list .main-line-ply','wc-move-list .move','.vertical-move-list .move']){
     const all=Array.from(document.querySelectorAll(sel));
     if(all.length<2)continue;
     const active=all.filter(n=>n.matches('.active,.current,.selected,[aria-current="true"]'));
     if(active.length && active.at(-1)!==all.at(-1))return false;
   }
   const structural=structuralMoveRoot();
   if(structural){
     const moves=Array.from(structural.children).filter(n=>sanPattern.test(cleanMove(n.textContent)));
     const active=moves.filter(n=>n.matches?.('.active,.current,.selected,[aria-current="true"]'));
     if(active.length&&active.at(-1)!==moves.at(-1))return false;
   }
   return true;
 }
 function paint(data){currentResult=data;if(data?.reviewed_finished_game||!cfg.enabled||cfg.privateMode||!atHistoryEnd()){clearOverlay();sendVisualUpdate(cfg.privateMode?'private':'stale',data);return}
   const board=boardElement();if(!board)return clearOverlay();observeBoardGeometry(board);const rect=board.getBoundingClientRect();
  if(rect.width<130||rect.height<130)return clearOverlay();
  // Render in board-local pixels instead of a viewport-sized SVG.  A global
  // viewBox was sensitive to browser zoom/scroll and made arrows drift away
  // from their squares on Chess.com responsive boards.
  const svgRect={left:0,top:0,width:rect.width,height:rect.height};
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('width','100%');svg.setAttribute('height','100%');
  svg.setAttribute('viewBox',`0 0 ${rect.width} ${rect.height}`);
   svg.style.cssText='position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible;z-index:2147482999';
  // Use the same piece-aware orientation as placementFromBoard(). Re-running
  // the resolver without pieces falls back to white on boards without an
  // explicit CSS orientation marker and mirrors arrows on black boards.
  let ori=boardOrientation(board,pieceNodes(board));
  (data.opponent_moves||[]).slice(0,2).forEach((m,i)=>drawArrow(svg,svgRect,ori,m.uci,i===0?ARROW_COLORS.opponentTop1:ARROW_COLORS.opponentTop2,i===0?.96:.62));
  (data.my_moves||[]).slice(0,2).forEach((m,i)=>drawArrow(svg,svgRect,ori,m.uci,i===0?ARROW_COLORS.ownTop1:ARROW_COLORS.ownTop2,i===0?.96:.65));
  if(data.premove)drawArrow(svg,svgRect,ori,data.premove.uci,ARROW_COLORS.premove,.96);
   layer.style.display='';layer.replaceChildren();
   if(renderedSvg?.isConnected)renderedSvg.remove();
   if(renderedBoard&&renderedBoard!==board&&renderedPosition)renderedBoard.style.position=renderedInlinePosition;
   if(renderedBoard!==board){
    const computed=window.getComputedStyle?.(board);renderedPosition=computed?.position||'';renderedInlinePosition=board.style.position||'';
    if(renderedPosition==='static')board.style.position='relative';
   }
   renderedBoard=board;renderedSvg=svg;
   board.appendChild(svg);sendVisualUpdate('normal',data);
 }
 function insightLines(data){
  return (Array.isArray(data?.plan_messages)?data.plan_messages:[]).filter(Boolean).slice(0,6);
 }
 // Use space outside the board; on a full-screen board the panel is placed
 // below it in document coordinates and remains accessible by scrolling.
 function panelPosition(rect,viewportWidth,viewportHeight,panelWidth=350,panelHeight=360){
  const gap=12,margin=10,width=Math.max(120,Math.min(panelWidth,viewportWidth-2*margin));
  const height=Math.max(100,Math.min(panelHeight,viewportHeight-2*margin));
  const top=Math.max(margin,Math.min(rect.top,viewportHeight-height-margin));
  if(viewportWidth-rect.right>=width+gap+margin)return{left:Math.round(rect.right+gap),top:Math.round(top),width,maxHeight:height,position:'fixed'};
  if(rect.left>=width+gap+margin)return{left:Math.round(rect.left-width-gap),top:Math.round(top),width,maxHeight:height,position:'fixed'};
  const left=Math.max(margin,Math.min(rect.left,viewportWidth-width-margin));
  const below=viewportHeight-rect.bottom-gap-margin;
  if(below>=100)return{left:Math.round(left),top:Math.round(rect.bottom+gap),width,maxHeight:Math.min(height,below),position:'fixed'};
  const above=rect.top-gap-margin;
  if(above>=100)return{left:Math.round(left),top:Math.round(Math.max(margin,rect.top-gap-height)),width,maxHeight:Math.min(height,above),position:'fixed'};
  return{left:Math.round(left),top:Math.round(Math.max(margin,rect.bottom+gap)),width,maxHeight:height,position:'absolute'};
 }
 function placePanel(board=currentBoard||boardElement()){
  if(!board)return;
  const pos=panelPosition(board.getBoundingClientRect(),window.innerWidth,window.innerHeight,360);
  const documentSpace=pos.position==='absolute';
  wrapper.style.position=pos.position;
  wrapper.style.left=`${pos.left+(documentSpace?Number(window.scrollX||0):0)}px`;
  wrapper.style.top=`${pos.top+(documentSpace?Number(window.scrollY||0):0)}px`;
  wrapper.style.right='auto';wrapper.style.bottom='auto';
  el('panel').style.width=`${pos.width}px`;el('panel').style.maxHeight=`${pos.maxHeight}px`;
 }
 function show(data){if(cfg.privateMode){el('results').replaceChildren();el('results').hidden=true;return}el('results').hidden=false;let html='';
  if(data.allie_skip_reason)html+=`<p class='warn'>${escape(data.allie_skip_reason)}</p>`;
  if(data.repertoire?.primary)html+=`<p class='small'><b>Repertoire:</b> ${escape(data.repertoire.primary)}${data.repertoire.selection?` · Auswahl ${escape(data.repertoire.selection)}`:''}${data.repertoire.expected_san?` · nächster Wunschzug ${escape(data.repertoire.expected_san)}`:''}</p>`;
  const choices=Array.isArray(data.moves)?data.moves.slice(0,5):[];
  if(choices.length){html+='<h3>Menschliche Zugwahrscheinlichkeit</h3>';for(const choice of choices){const probability=Number(choice.probability);html+=`<div class='item'><span>${escape(choice.san||choice.uci||'')}</span><span>${Number.isFinite(probability)&&probability>=0&&probability<=1?(100*probability).toFixed(1)+' %':'unbekannt'}</span></div>`}html+="<p class='small'>Allie-Modellausgabe, keine Gewinnchance. Stil und Repertoire koennen die Reihenfolge beeinflussen.</p>";}
  const thinkTime=Number(data.expected_think_time_s);
  if(data.expected_think_time_s!=null&&Number.isFinite(thinkTime)&&thinkTime>=0)html+=`<p class='small'>Erwartete Bedenkzeit: ${thinkTime.toFixed(1)} s</p>`;
  const messages=insightLines(data);
  if(messages.length)html+=`<div class='analysis-title'><span>Allie \u00b7 Spielanalyse</span><span>${messages.length} Hinweise</span></div>`;
  for(const message of messages)html+=`<div class='insight'>${escape(message)}</div>`;
  if(data.stockfish){html+='<h3>Stockfish: objektiv</h3>';if(!data.stockfish.available)html+=`<p>${escape(data.stockfish.error||'Engine fehlt')}</p>`;else for(const m of data.stockfish.lines||[])html+=`<div class='item'><span>${escape(m.san)} | ${escape(m.variation)}</span><span>${escape(m.score)}</span></div>`}
  el('results').innerHTML=html;
  if(messages.length&&!panelDismissed){el('panel').classList.add('open');el('bubble').style.display='none';placePanel()}
 }
 let capabilityToken='',capabilityInstance='',capabilityPromise=null,capabilityRetryAfter=0,pairingCode='',pairingPromise=null,servicePort=normalizePort(cfg.port),servicePortPromise=null,serviceEpoch=0;
 function serviceUrl(path){return `http://127.0.0.1:${servicePort}${path}`}
 function resetCapability(){serviceEpoch++;capabilityToken='';capabilityInstance='';capabilityPromise=null;pairingCode='';pairingPromise=null;}
 function setServicePort(value){const port=normalizePort(value);if(port!==servicePort){servicePort=port;resetCapability()}return port;}
 function ensureServicePort(){
  if(servicePortPromise)return servicePortPromise;
  const pending=new Promise(resolve=>{
   let settled=false,timer;
   const finish=value=>{if(settled)return;settled=true;clearTimeout(timer);resolve(setServicePort(value));};
   const fallback=()=>finish(cfg.port);
   try{
    if(typeof chrome==='undefined'||!chrome.runtime?.sendMessage)return fallback();
    timer=setTimeout(fallback,1000);
    chrome.runtime.sendMessage({type:'allie21:get-port'},response=>{
     if(chrome.runtime?.lastError||!response)return fallback();
     finish(response.port);
    });
   }catch{fallback()}
  });
  servicePortPromise=pending;
  pending.finally(()=>{if(servicePortPromise===pending)servicePortPromise=null});
  return pending;
 }
 function ensurePairingCode(){
  if(pairingCode)return Promise.resolve(pairingCode);
  if(pairingPromise)return pairingPromise;
  pairingPromise=new Promise(resolve=>{
   if(typeof chrome==='undefined'||!chrome.runtime?.sendMessage){resolve('');return}
   let settled=false,timer=setTimeout(()=>{if(!settled){settled=true;resolve('')}},5000);
   try{chrome.runtime.sendMessage({type:'allie21:get-pairing'},response=>{if(settled)return;settled=true;clearTimeout(timer);const value=String(response?.pairing_code||'');if(/^\d{8}$/.test(value))pairingCode=value;resolve(pairingCode)})}catch{clearTimeout(timer);resolve('')}
  }).finally(()=>{pairingPromise=null});
  return pairingPromise;
 }
 function ensureCapability(){
  return ensureServicePort().then(()=>{
   if(capabilityToken)return capabilityToken;
   if(Date.now()<capabilityRetryAfter){const error=Error('Browser-Pairing erforderlich. Edge-Erweiterung laden und Tab neu laden.');error.code='pairing';error.status=401;throw error}
   if(capabilityPromise)return capabilityPromise;
   const epoch=serviceEpoch,controller=new AbortController(),timer=setTimeout(()=>controller.abort(),6000);
   const pending=ensurePairingCode().then(pairing=>fetch(serviceUrl('/api/capability'),{headers:{'X-Allie-Overlay':'1',...(pairing?{'X-Allie-Pairing':pairing}:{})},cache:'no-store',signal:controller.signal}))
    .then(async response=>{const data=await response.json();if(epoch!==serviceEpoch)throw new DOMException('Server changed','AbortError');if(!response.ok||!data.token||!data.instance_id){const error=Error(data.error||data.detail||`HTTP ${response.status}`);if(response.status===401||response.status===429){error.code='pairing';error.status=response.status;capabilityRetryAfter=Date.now()+30000}throw error}capabilityToken=data.token;capabilityInstance=data.instance_id;return capabilityToken})
    .finally(()=>{clearTimeout(timer);if(capabilityPromise===pending)capabilityPromise=null});
   capabilityPromise=pending;
   return pending;
  });
 }
 function postJson(path,data,timeout=15000){
  const controller=new AbortController();let expired=false;
  const timer=setTimeout(()=>{expired=true;controller.abort()},timeout);
  const send=async(retry=true)=>{
   const token=await ensureCapability();
   if(controller.signal.aborted)throw new DOMException('Request aborted','AbortError');
   const epoch=serviceEpoch;
   const response=await fetch(serviceUrl(path),{method:'POST',headers:{'Content-Type':'application/json','X-Allie-Overlay':'1','Authorization':'Bearer '+token,'X-Allie-Instance':capabilityInstance},body:JSON.stringify(data),signal:controller.signal});
   if(epoch!==serviceEpoch)throw new DOMException('Server changed','AbortError');
   if(response.status===401&&retry){resetCapability();markBrowserSessionReset();return send(false)}
   let parsed={};try{parsed=await response.json()}catch{}
   if(!response.ok){const error=new Error(parsed.error||String(response.status));error.status=response.status;throw error}return parsed;
  };
  const promise=send().catch(error=>{if(expired)throw Error('Lokale Analyse braucht zu lange.');if(error.name==='AbortError'||error.status)throw error;throw Error('Lokaler Allie-Server nicht erreichbar: '+error.message)}).finally(()=>clearTimeout(timer));
  return{promise,abort:()=>controller.abort()};
 }
 const localPost=(path,data,timeout)=>postJson(path,data,timeout).promise;
 let browserSessionNeedsReset=true;
 function browserSessionResetPending(){return browserSessionNeedsReset}
 function markBrowserSessionReset(){browserSessionNeedsReset=true}
 function browserSessionResetDone(){browserSessionNeedsReset=false;retryAfter=0}
 function shorterValidatedRound(previousPgn,movesSeen){return Boolean(previousPgn&&movesSeen<previousPgn.trim().split(/\s+/).length)}
 const START_PLACEMENT='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR';
 function startPositionHistory(snapshot){
  if(snapshot?.placement!==START_PLACEMENT)return null;
  return{pgn:'*',fen:'',orientation:snapshot.orientation,placement:snapshot.placement,message:'Startstellung erkannt - Analyse startet.',ready:true,fallback_ready:false,moves_seen:0};
 }
 function sideToken(value){
  const text=String(value||'').toLowerCase();
  if(/(?:^|[\s_-])(black|dark|schwarz)(?:$|[\s_-])/.test(text))return'black';
  if(/(?:^|[\s_-])(white|light|weiss|weiß)(?:$|[\s_-])/.test(text))return'white';
  return'';
 }
 function detectedPlayerSide(board){
  const direct=[board,board?.parentElement,board?.closest?.('[data-player-color],[data-player-side],[data-color]')].filter(Boolean);
  for(const node of direct){
   for(const attr of ['data-player-color','data-player-side','data-color','data-side','player-color']){
    const side=sideToken(node.getAttribute?.(attr));if(side)return side;
   }
  }
  if(typeof document==='undefined'||!board)return'';
  const boardRect=board.getBoundingClientRect?.();
  const candidates=Array.from(document.querySelectorAll('[data-player-color],[data-player-side],[data-color],[data-side],[class*="player"]'));
  let best='',bestScore=-1;
  for(const node of candidates){
   const side=sideToken(['data-player-color','data-player-side','data-color','data-side'].map(a=>node.getAttribute?.(a)||'').concat(String(node.className||'')).join(' '));
   if(!side)continue;
   const cls=String(node.className||'').toLowerCase(),rect=node.getBoundingClientRect?.();
   let score=0;
   if(/player-bottom|bottom-player|player-bottom/.test(cls))score+=100;
   if(boardRect&&rect&&rect.top>boardRect.bottom)score+=50;
   if(boardRect&&rect)score-=Math.min(20,Math.abs(rect.top-boardRect.bottom)/100);
   if(score>bestScore){best=side;bestScore=score}
  }
  return best;
 }
 function pendingInsights(history){
  if(history?.placement===START_PLACEMENT)return{plan_messages:['Startstellung erkannt: Allie berechnet sofort die menschlich wahrscheinlichsten Eröffnungszüge.','Eröffnungsphase: Zentrum kontrollieren, Leichtfiguren entwickeln und den König sicher rochieren.']};
  return{plan_messages:['Stellung erkannt: Allie analysiert den aktuellen Zug.']};
 }
 async function historyFromVisibleBoard(){
 const snapshot=readBoardSnapshot();if(!snapshot)return{pgn:readHistory(),orientation:cfg.orientation==='auto'?'white':cfg.orientation,placement:''};
  const initial=startPositionHistory(snapshot);
   if(initial&&lastPlacement!==START_PLACEMENT)markBrowserSessionReset();
   if(browserSessionResetPending()){
    await localPost('/api/browser-position/reset',{session_id:boardSessionId},4000);
    browserSessionResetDone();trackedPGN='';trackedFen='';lastPlacement='';
   }
   if(initial){
    lastPlacement=snapshot.placement;trackedPGN='*';trackedFen='';return initial;
  }
  if(snapshot.placement===lastPlacement&&trackedPGN)return{pgn:trackedPGN,fen:'',orientation:snapshot.orientation,placement:snapshot.placement,fallback_ready:false};
   const expected=snapshot.placement,candidates=readHistoryCandidates(),fallback=candidates[0]||'',game_id=chessComGameId(),previousPGN=trackedPGN;
   const state=await localPost('/api/browser-position',{session_id:boardSessionId,placement:expected,pgn:fallback,pgn_candidates:candidates,game_id},12000);
   const latest=readBoardSnapshot();if(!latest||latest.placement!==expected)return{pgn:'',orientation:snapshot.orientation,placement:expected,stale:true};
   if(state.ready&&shorterValidatedRound(previousPGN,state.moves_seen))retryAfter=0;
  lastPlacement=expected;trackedPGN=state.ready?state.pgn:'';trackedFen=state.fallback_ready&&!state.ready?state.fen:'';
  return{pgn:trackedPGN,fen:trackedFen,orientation:snapshot.orientation,placement:expected,message:state.message,ready:state.ready,fallback_ready:state.fallback_ready,moves_seen:state.moves_seen};
 }
 // Plattform-Farbmarker haben Vorrang. Fehlen sie (z.B. bei laufenden Chess.com-
 // Partien), entspricht die eigene Seite der sichtbaren Brettseite; die manuelle
 // Auswahl bleibt jederzeit maßgeblich.
 function playerSideFor(orientation,detected){return cfg.playerSide==='auto'?(detected||orientation||'white'):cfg.playerSide}
 function analyze(pgn,placement='',fen='',playerSide='white'){
   if(pending||!cfg.enabled)return;
   const basis=pgn||fen,openingSettings=selectedOpeningSettings(),key=JSON.stringify([pgn,fen,placement,cfg.elo,cfg.tc,playerSide,cfg.playStyle,openingSettings.opening_white,openingSettings.opening_black]);analysisKey=key;
   const serial=++analysisSerial;
   pending=true;el('status').textContent='Allie analysiert den aktuellen Zug...';
   const current=()=>serial===analysisSerial&&analysisKey===key&&lastPGN===basis&&atHistoryEnd()&&(!placement||readBoardSnapshot()?.placement===placement);
   const request=(source,preview,final)=>{
     const fallback=source==='stockfish'&&!fen;
     const data={pgn,fen,white_elo:cfg.elo,black_elo:cfg.elo,time_control:cfg.tc,review_finished:false,player_side:playerSide,play_style:cfg.playStyle,...openingSettings,analysis_source:fen?'stockfish':source,preview:fen?false:preview};
    const fail=error=>{
     if(serial!==analysisSerial)return;
     activeRequest=null;
     const message=typeof error==='string'?error:(error?.message||String(error));
     if(error?.code==='pairing'){
       pending=false;busyRetries=0;retryAfter=Date.now()+30000;
       if(current())el('status').textContent=message;
       return;
     }
     if(error?.status===429){
       // The server is working on another request; Stockfish would hit the same gate.
       pending=false;
       const delay=Math.min(12000,2000*(2**Math.min(busyRetries++,3)));
       retryAfter=Date.now()+delay;
       if(current())el('status').textContent='Analyse bereits aktiv – erneuter Versuch folgt.';
       setTimeout(()=>{if(serial===analysisSerial)scheduleTick()},delay+50);
       return;
     }
     if(source==='allie'&&!fen&&current()){
       el('status').textContent='Allie nicht verfügbar – Stockfish-Fallback läuft...';
       return request('stockfish',false,true);
     }
     pending=false;busyRetries=0;retryAfter=Date.now()+30000;
     if(current())el('status').textContent=message;
     scheduleTick();
    };
    activeRequest=postJson('/analyze',data,240000);
    activeRequest.promise.then(parsed=>{if(serial!==analysisSerial)return;activeRequest=null;try{
      if(!current()){pending=false;lastPGN='';return scheduleTick()}
      if(source==='allie'&&!fen&&(!Array.isArray(parsed?.moves)||!parsed.moves.length||parsed?.allie_skip_reason)){
        el('status').textContent='Allie nicht verfügbar – Stockfish-Fallback läuft...';
        return request('stockfish',false,true);
      }
      currentResult=parsed;show(parsed);paint(parsed);
      pending=false;busyRetries=0;el('status').textContent=source==='stockfish'?(fallback?'Stockfish-Fallback aktuell':'Stockfish aktuell'):`Allie aktuell · ${parsed.move_count} Halbzuege`;
     }catch(e){fail('Analyse: '+e.message)}}).catch(error=>fail(error.name==='AbortError'?'Analyse abgebrochen.':error));
   };
   request(fen?'stockfish':'allie',!fen,true);
 }
  el('now').onclick=async()=>{markBrowserSessionReset();updateSettings();retryAfter=0;lastPlacement='';trackedPGN='';trackedFen='';await tick(true)};
 async function tick(manual=false){
   if(trackingPending)return;
   const previousBoard=currentBoard;const visibleBoard=readBoardSnapshot();
   if(previousBoard&&visibleBoard&&previousBoard!==visibleBoard.board)resetBoardSession('board_changed');
   observeBoardGeometry(visibleBoard?.board||null);
   wrapper.style.display='';if(visibleBoard)placePanel(visibleBoard.board);
  if(!visibleBoard){if(currentResult||lastPGN){currentResult=null;lastPGN='';clearOverlay();clearRemoteOverlay('stale');show({})}return}
  // Private mode hides all page-owned DOM/SVG HUDs, but it must not stop the
  // browser tracker or analysis pipeline.  The native protected window gets
  // its frames from paint() after analysis; returning here made private mode
  // permanently invisible because no position was ever analysed.
  if(cfg.privateMode)clearOverlay();
  if(!cfg.enabled){clearOverlay();clearRemoteOverlay('stale');return}
  if(!visibleBoard.authoritative&&!boardFrameIsStable(visibleBoard.placement)){
   if(visibleBoard.placement!==lastPlacement){currentResult=null;clearOverlay();if(pending)cancelAnalysis()}
   scheduleTick();return;
  }
  trackingPending=true;
  try{
   const history=await historyFromVisibleBoard(),pgn=history.pgn,fen=history.fen||'',basis=pgn||fen;
   if(!basis||!atHistoryEnd()){
    if(currentResult||lastPGN){currentResult=null;lastPGN='';clearOverlay();clearRemoteOverlay('stale');show({})}
    if(manual||history.message)el('status').textContent=history.message||'Brett erkannt – warte auf eine vollständige Zugfolge ab der Startstellung.';
    if(!basis){
     if(history.placement!==unsettledPlacement){unsettledPlacement=history.placement;unsettledRetries=0}
     if(unsettledRetries<4){unsettledRetries++;scheduleTick()}
    }
    return;
   }
    unsettledPlacement=history.placement;unsettledRetries=0;
    const playerSide=playerSideFor(history.orientation,detectedPlayerSide(currentBoard));
    const wanted=JSON.stringify([pgn,fen,history.placement,cfg.elo,cfg.tc,playerSide,cfg.playStyle,cfg.whiteOpening,cfg.blackOpening]);
    if(basis!==lastPGN||wanted!==analysisKey||(!pending&&!currentResult&&Date.now()>=retryAfter)){
     if(basis!==lastPGN||wanted!==analysisKey)busyRetries=0;
     currentResult=null;clearOverlay();show(pendingInsights(history));
     // Keep the protected native HUD alive while the model is thinking.  In
     // private mode a normal-mode payload is deliberately rejected by the
     // fail-closed router, which used to make the overlay disappear during
     // every analysis request.
     sendVisualUpdate(cfg.privateMode?'private':'normal',pendingInsights(history));
     if(pending)cancelAnalysis();
     if(Date.now()>=retryAfter){lastPGN=basis;analyze(pgn,history.placement,fen,playerSide)}
    }
  }catch(error){if(manual)el('status').textContent=error.message||String(error)}finally{trackingPending=false}
 }
 window.addEventListener('resize',()=>{placePanel();requestRepaint()},{passive:true});
 window.addEventListener('scroll',()=>{placePanel();requestRepaint()},true);
 window.visualViewport?.addEventListener('resize',requestRepaint,{passive:true});
 window.visualViewport?.addEventListener('scroll',requestRepaint,{passive:true});
 function scheduleTick(manual=false){clearTimeout(tickTimer);tickTimer=setTimeout(()=>tick(manual),120)}
 function hideForInactive(){clearOverlay();if(document.hidden||!cfg.privateMode)clearRemoteOverlay(document.hidden?'stale':'focus_lost')}
 document.addEventListener('visibilitychange',()=>{if(document.hidden)hideForInactive();else scheduleTick(true)},{passive:true});
 window.addEventListener('blur',hideForInactive,{passive:true});
 window.addEventListener('focus',()=>scheduleTick(true),{passive:true});
 function resetBoardSession(reason='navigation'){
  clearRemoteOverlay(reason);
  cancelAnalysis();
  currentResult=null;lastPGN='';trackedPGN='';trackedFen='';analysisKey='';busyRetries=0;lastPlacement='';unsettledPlacement='';unsettledRetries=0;currentBoard=null;markBrowserSessionReset();
  sessionHash=Math.imul(sessionHash^Date.now(),16777619);boardSessionId='web-'+(crypto.randomUUID?.()||Math.random().toString(36).slice(2));
  clearOverlay();show({});scheduleTick(true);
 }
 function installNavigationLifecycle(){
  for(const method of ['pushState','replaceState']){
   const original=history[method];if(typeof original!=='function')continue;
   history[method]=function(...args){const before=location.href;const result=original.apply(this,args);if(location.href!==before)resetBoardSession('navigation');return result};
  }
  window.addEventListener('popstate',()=>resetBoardSession('navigation'),{passive:true});
  window.addEventListener('hashchange',()=>resetBoardSession('navigation'),{passive:true});
 }
 let privateSync=null,privateModeSent=null;
 async function syncPrivateMode(force=false){
  if(privateSync)return privateSync;
  const requested=Boolean(cfg.privateMode);
  if(!requested){fill();return null;}
  const pending=(async()=>{
   if(force||privateModeSent!==requested){privateModeSent=requested;return sendOverlayMode(requested?'private':'normal')}
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),6000);
   try{
    await ensureServicePort();
    if(controller.signal.aborted)throw new DOMException('Request aborted','AbortError');
    const response=await fetch(serviceUrl('/api/overlay/status'),{cache:'no-store',headers:{'X-Allie-Overlay':'1'},signal:controller.signal});
    if(!response.ok)throw Error(`HTTP ${response.status}`);
    const state=await response.json();
    if(requested===cfg.privateMode)applyPrivateStatus(state);
    return state;
   }catch(error){if(requested&&cfg.privateMode)applyPrivateStatus({available:false,reason:error.message});return null}
   finally{clearTimeout(timer)}
  })();
  privateSync=pending;
  try{return await pending}finally{if(privateSync===pending)privateSync=null}
 }
 installNavigationLifecycle();
 new MutationObserver(changes=>{
    if(changes.every(change=>wrapper.contains(change.target)||layer.contains(change.target)||change.target===renderedBoard||renderedSvg?.contains?.(change.target)))return;
    scheduleTick();
  }).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style','data-ply','data-piece','data-orientation']});
 setInterval(scheduleTick,5000);setInterval(syncPrivateMode,10000);window.addEventListener('beforeunload',()=>clearRemoteOverlay('stopped'));syncPrivateMode();tick();
})();
