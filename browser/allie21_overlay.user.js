// ==UserScript==
// @name         Allie 2.1 Live Studio v11 (Automatisches Live-Overlay)
// @namespace    local.allie21.study
// @version      11.1.7
// @description  Permanent Allie move, opponent and pre-move arrows on visible DOM chess boards.
// @match        https://*.chess.com/*
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
 const STORE='allie21.auto.v11';
 const load=()=>{try{return JSON.parse(localStorage.getItem(STORE)||'{}')}catch{return{}}};
 const stored=load();
 const cfg=Object.assign({elo:1950,tc:'300+0',enabled:true,orientation:'auto',playerSide:'auto',playerSideMode:'auto'},stored);
 if(!stored.playerSideMode){cfg.playerSide='auto';cfg.playerSideMode='auto'}
 const ARROW_COLORS=Object.freeze({ownTop1:'#16c784',ownTop2:'#7ee2b8',opponentTop1:'#ef3340',opponentTop2:'#ff9299',premove:'#2f80ed'});
 const save=()=>{try{localStorage.setItem(STORE,JSON.stringify(cfg))}catch{}};
 const wrapper=document.createElement('div');
 wrapper.id='allie21-auto-study-root';
 wrapper.style.cssText='all:initial;display:none;position:fixed;right:15px;bottom:18px;z-index:2147483000;font-family:system-ui,sans-serif;color:#e7f2ff';
 document.documentElement.appendChild(wrapper);
 const shadow=wrapper.attachShadow({mode:'open'});
 shadow.innerHTML=`
 <style>
 *{box-sizing:border-box}button,input,select{font:inherit}#bubble{background:#10283d;color:#eaf6ff;border:1px solid #48758c;border-radius:25px;padding:9px 13px;font-size:12px;font-weight:650;cursor:pointer;box-shadow:0 2px 10px #0008}
 #panel{display:none;width:350px;max-width:calc(100vw - 20px);max-height:76vh;overflow:auto;background:#102236;color:#e7f2ff;border:1px solid #43657e;box-shadow:0 8px 24px #0009;border-radius:10px;padding:11px;line-height:1.35;font-size:12px}
 #panel.open{display:block}h3{margin:8px 0 4px;color:#8de0c5;font-size:13px}p{margin:5px 0}label{display:block;margin:6px 0 3px}.row{display:flex;gap:7px;align-items:center}.row>*{flex:1;min-width:0}#close{flex:0 0 32px;padding:6px}input,select{width:100%;padding:6px;background:#091724;border:1px solid #3c6076;border-radius:5px;color:#e6f3ff}
 button{border:1px solid #3c6076;background:#285474;color:white;border-radius:6px;padding:7px;cursor:pointer}.item{display:flex;gap:8px;justify-content:space-between;border-bottom:1px solid #325068;padding:4px 0}.stat{color:#a6d9e3}.warn{color:#ffccaf}.small{font-size:11px;color:#abc4d6}#results{margin-top:7px}.insight{background:#ffffff0b;border-left:3px solid #58b99a;border-radius:7px;margin:6px 0;padding:8px 9px}.analysis-title{display:flex;justify-content:space-between;align-items:center;color:#8de0c5;font-weight:700;margin-top:9px}
 </style>
 <button id='bubble'>Allie 2.1 | Analyse</button>
 <section id='panel'><div class='row'><b style='font-size:15px'>Allie 2.1 | Live Overlay</b><button id='close'>X</button></div>
 <p class='small'>Allie wählt menschlich passend zu Elo und Zeit; Stockfish bleibt nur der objektive Vergleich.</p>
 <div class='row'><div><label>Elo</label><input id='elo' type='number' min='600' max='2800'/></div>
  <div><label>Zeitkontrolle</label><input id='tc' placeholder='300+0'/></div></div>
 <div class='row'><div><label>Brettorientierung</label><select id='orientation'><option value='auto'>Automatisch</option><option value='white'>Weiss unten</option><option value='black'>Schwarz unten</option></select></div>
 <div><label>Deine Farbe</label><select id='playerSide'><option value='auto'>Automatisch</option><option value='white'>Weiss</option><option value='black'>Schwarz</option></select></div></div>
 <div class='row' style='margin-top:8px'><button id='toggle'>Live-Hinweise: Ein</button><button id='now'>Jetzt analysieren</button></div>
 <p id='status' class='stat'>Lokalen Server starten; die Analyse verbindet sich automatisch.</p>
 <div id='results'></div><p class='small'>Starkgrün: Mein Top 1 · Hellgrün: Mein Top 2<br>Starkrot: Gegner Top 1 · Hellrot: Gegner Top 2<br>Blau: Sicherer Pre-Move. Allie klickt nie selbst.</p>
 </section>`;
 const el=id=>shadow.getElementById(id);
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let pending=false,lastPGN='',currentResult=null,retryAfter=0,lastPlacement='',trackedPGN='',trackedFen='',trackingPending=false,currentBoard=null,analysisKey='',tickTimer=0,activeRequest=null,analysisSerial=0,unsettledPlacement='',unsettledRetries=0,panelDismissed=false;
 const cancelAnalysis=()=>{analysisSerial++;if(activeRequest){activeRequest.abort();activeRequest=null}pending=false};
 el('bubble').onclick=()=>{panelDismissed=false;el('panel').classList.add('open');el('bubble').style.display='none';placePanel()};
 el('close').onclick=()=>{panelDismissed=true;el('panel').classList.remove('open');el('bubble').style.display=''};
 const invalidate=()=>{cancelAnalysis();lastPGN='';trackedFen='';analysisKey='';currentResult=null;clearOverlay();show({})};
 const updateSettings=()=>{cfg.elo=Number(el('elo').value)||1950;cfg.tc=el('tc').value.trim()||'300+0';cfg.orientation=el('orientation').value;cfg.playerSide=el('playerSide').value;cfg.playerSideMode=cfg.playerSide==='auto'?'auto':'manual';save();invalidate();scheduleTick(true)};
 for(const field of ['elo','tc','orientation','playerSide'])el(field).addEventListener('change',updateSettings);
 const fill=()=>{el('elo').value=cfg.elo;el('tc').value=cfg.tc;el('orientation').value=cfg.orientation;el('playerSide').value=cfg.playerSide;el('toggle').textContent=`Live-Hinweise: ${cfg.enabled?'Ein':'Aus'}`};fill();
 el('toggle').onclick=()=>{cfg.enabled=!cfg.enabled;save();fill();invalidate();if(cfg.enabled)scheduleTick(true)};
 const sessionSeed=location.hostname+location.pathname;
 let sessionHash=2166136261;for(const char of sessionSeed){sessionHash^=char.charCodeAt(0);sessionHash=Math.imul(sessionHash,16777619)}
 const boardSessionId='web-'+(sessionHash>>>0).toString(36);
 const selectors=['wc-move-list .main-line-ply','wc-move-list .move','wc-move-list [data-ply]','wc-move-list [data-node]','wc-move-list .node','wc-move-list [class*="move-node"]','wc-move-list button','wc-simple-move-list [data-ply]','wc-simple-move-list [data-node]','wc-simple-move-list .node','wc-simple-move-list [class*="move"]','wc-simple-move-list button','wc-vertical-move-list [data-ply]','wc-vertical-move-list [data-node]','wc-vertical-move-list [class*="move"]','wc-vertical-move-list button','[data-cy="move-list"] [data-ply]','[data-cy="move-list"] [class*="move"]','[class*="move-list"] button','l4x l4','l4x move','.analyse__moves move','.analyse__moves .san','.vertical-move-list .move','.move-list .move','.move-list-component .move','.pgn-viewer .san','.analysis-moves .san','.move-text-component'];
 const sanPattern=/^(?:O-O(?:-O)?|0-0(?:-0)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?|[a-h][1-8][+#]?)$/;
 // Lichess changes its short custom tag names regularly. Locate the current
 // mainline structurally via the rewind-to-ply-0 control instead of tag names.
 function structuralMoveRoot(){
  const rewind=document.querySelector('button[data-ply="0"]');
  const candidate=rewind?.parentElement?.nextElementSibling;
  if(!candidate||candidate.children.length<2)return null;
  const texts=Array.from(candidate.children).slice(0,12).map(n=>(n.textContent||'').trim());
  return texts.some(t=>t==='1')&&texts.some(t=>sanPattern.test(t.replace(/[!?]+/g,'')))?candidate:null;
 }
 const figurines={'♔':'K','♕':'Q','♖':'R','♗':'B','♘':'N','♚':'K','♛':'Q','♜':'R','♝':'B','♞':'N'};
 function cleanMove(text,node){
  let value=String(text||'').trim().replace(/^\d+\.(?:\.\.)?/,'').replace(/[!?]+/g,'').replace(/\s+/g,'');
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
  for(const {node} of ordered){const move=cleanMove(node.getAttribute?.('data-san')||node.textContent,node);if(sanPattern.test(move)&&move!==compact.at(-1))compact.push(move)}
  return compact;
 }
 function startsAtMoveOne(root){
  if(root.querySelector?.('[data-ply="0"],[data-ply="1"],[data-node="0-0"],[data-move-number="1"]'))return true;
  const text=(root.textContent||'').trim().slice(0,240);
  return /(?:^|\s)1\s*\./.test(text)||/^1(?=[a-hKQRBN♔♕♖♗♘♚♛♜♝♞])/.test(text);
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
  const rootSelectors=['wc-move-list','wc-simple-move-list','wc-vertical-move-list','.analyse__moves','.vertical-move-list','.move-list','.move-list-component','.pgn-viewer','.analysis-moves','[data-cy="move-list"]','[class*="move-list"]'];
  const roots=Array.from(document.querySelectorAll(rootSelectors.join(',')));
  return Array.from(new Set(roots)).filter(root=>!root.closest('#allie21-auto-study-root'));
 }
 function readHistory(){
  let best=[];
  for(const sel of selectors){
    let arr=movesFromNodes(document.querySelectorAll(sel));
    if(arr.length>best.length)best=arr;
  }
  const structural=structuralMoveRoot();
  if(structural){const arr=movesFromNodes(structural.children);if(arr.length>best.length)best=arr}
  for(const root of candidateMoveRoots()){
   const arr=movesFromRoot(root);if(arr.length>best.length)best=arr;
  }
  if(!best.length)return isStandardStartPosition()?'*':'';
  // Python accepts this candidate only when every move is legal from the
  // standard start and the final placement equals the visible board. A
  // virtualised fragment therefore cannot create a false history.
  return best.map((m,i)=>i%2===0?`${1+i/2}. ${m}`:m).join(' ');
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
 function pieceNodes(board){
  const selector='piece,.piece,[data-piece],[data-figurine],img[alt*="pawn" i],img[alt*="knight" i],img[alt*="bishop" i],img[alt*="rook" i],img[alt*="queen" i],img[alt*="king" i],[aria-label*="pawn" i],[aria-label*="knight" i],[aria-label*="bishop" i],[aria-label*="rook" i],[aria-label*="queen" i],[aria-label*="king" i]';
  return Array.from(new Set(board.querySelectorAll(selector))).filter(pieceCode);
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
 function placementFromBoard(board){
  const rect=board.getBoundingClientRect(),pieces=pieceNodes(board),ori=boardOrientation(board,pieces),square=rect.width/8;
  if(rect.width<130||rect.height<130||Math.abs(rect.width-rect.height)>Math.max(rect.width,rect.height)*.12)return null;
  const found=new Map();
  for(const piece of pieces){
   const code=pieceCode(piece),r=piece.getBoundingClientRect();
   if(!code||r.width<2||r.height<2||r.width>square*1.8||r.height>square*1.8)continue;
   const px=r.left+r.width/2,py=r.top+r.height/2;if(px<rect.left||px>rect.right||py<rect.top||py>rect.bottom)continue;
   let col=Math.max(0,Math.min(7,Math.floor((px-rect.left)/square))),row=Math.max(0,Math.min(7,Math.floor((py-rect.top)/square)));
   const file=ori==='black'?7-col:col,rank=ori==='black'?row:7-row,key=rank*8+file;
   if(found.has(key)&&found.get(key)!==code)return null;found.set(key,code);
  }
  const values=Array.from(found.values());if(values.filter(x=>x==='wk').length!==1||values.filter(x=>x==='bk').length!==1||values.length<4||values.length>32)return null;
  const ranks=[];for(let rank=7;rank>=0;rank--){let empty=0,text='';for(let file=0;file<8;file++){const code=found.get(rank*8+file);if(!code){empty++;continue}if(empty){text+=empty;empty=0}text+=code[0]==='w'?code[1].toUpperCase():code[1]}if(empty)text+=empty;ranks.push(text)}
  return {placement:ranks.join('/'),orientation:ori,pieces:values.length};
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
 function clearOverlay(){layer.replaceChildren()}
 function center(s,rect,ori){let file=s.charCodeAt(0)-97,rank=Number(s[1])-1;if(ori==='black'){file=7-file}else{rank=7-rank}return [rect.left+(file+.5)*rect.width/8,rect.top+(rank+.5)*rect.height/8]}
 function drawArrow(svg,rect,ori,uci,color,opacity=.87){
  if(!/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(uci||''))return;
  const [x,y]=center(uci.slice(0,2),rect,ori),[u,v]=center(uci.slice(2,4),rect,ori);
  const dx=u-x,dy=v-y,norm=Math.max(1,Math.hypot(dx,dy)),ux=dx/norm,uy=dy/norm;
  const sx=x+ux*rect.width/22,sy=y+uy*rect.width/22,tx=u-ux*rect.width/18,ty=v-uy*rect.width/18;
  const mk=(tag,props)=>{let a=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(props).forEach(([k,val])=>a.setAttribute(k,val));svg.appendChild(a)};
  const width=Math.max(4,Math.min(10,rect.width/72));
  mk('line',{x1:sx,y1:sy,x2:tx,y2:ty,stroke:color,'stroke-width':width,'stroke-linecap':'round',opacity});
  let angle=Math.atan2(dy,dx),size=Math.max(14,Math.min(30,rect.width/22));
  let points=[[tx,ty],[tx-size*Math.cos(angle-.48),ty-size*Math.sin(angle-.48)],[tx-size*Math.cos(angle+.48),ty-size*Math.sin(angle+.48)]];
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
     const active=moves.filter(n=>String(n.className||'').trim());
     if(active.length&&active.at(-1)!==moves.at(-1))return false;
   }
   return true;
 }
 function paint(data){currentResult=data;if(data?.reviewed_finished_game||!cfg.enabled||!atHistoryEnd())return clearOverlay();
  const board=boardElement();if(!board)return clearOverlay();const rect=board.getBoundingClientRect();
  if(rect.width<130||rect.height<130)return clearOverlay();
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('width','100%');svg.setAttribute('height','100%');
  svg.setAttribute('viewBox',`0 0 ${window.innerWidth} ${window.innerHeight}`);
  let ori=boardOrientation(board);
  (data.opponent_moves||[]).slice(0,2).forEach((m,i)=>drawArrow(svg,rect,ori,m.uci,i===0?ARROW_COLORS.opponentTop1:ARROW_COLORS.opponentTop2,i===0?.96:.62));
  (data.my_moves||[]).slice(0,2).forEach((m,i)=>drawArrow(svg,rect,ori,m.uci,i===0?ARROW_COLORS.ownTop1:ARROW_COLORS.ownTop2,i===0?.96:.65));
  if(data.premove)drawArrow(svg,rect,ori,data.premove.uci,ARROW_COLORS.premove,.96);
  layer.replaceChildren(svg);
 }
 function insightLines(data){
  return (Array.isArray(data?.plan_messages)?data.plan_messages:[]).filter(Boolean).slice(0,6);
 }
 function panelPosition(rect,viewportWidth,viewportHeight,panelWidth=350){
  const gap=12,margin=10;
  let left=viewportWidth-rect.right>=panelWidth+gap?rect.right+gap:rect.left>=panelWidth+gap?rect.left-panelWidth-gap:Math.max(margin,viewportWidth-panelWidth-margin);
  return{left:Math.round(left),top:Math.round(Math.max(margin,Math.min(rect.top,viewportHeight-180)))};
 }
 function placePanel(board=currentBoard||boardElement()){
  if(!board)return;
  const pos=panelPosition(board.getBoundingClientRect(),window.innerWidth,window.innerHeight);
  wrapper.style.left=`${pos.left}px`;wrapper.style.top=`${pos.top}px`;wrapper.style.right='auto';wrapper.style.bottom='auto';
 }
 function show(data){let html='';
  if(data.allie_skip_reason)html+=`<p class='warn'>${escape(data.allie_skip_reason)}</p>`;
  const messages=insightLines(data);
  if(messages.length)html+=`<div class='analysis-title'><span>Allie \u00b7 Spielanalyse</span><span>${messages.length} Hinweise</span></div>`;
  for(const message of messages)html+=`<div class='insight'>${escape(message)}</div>`;
  if(data.stockfish){html+='<h3>Stockfish: objektiv</h3>';if(!data.stockfish.available)html+=`<p>${escape(data.stockfish.error||'Engine fehlt')}</p>`;else for(const m of data.stockfish.lines||[])html+=`<div class='item'><span>${escape(m.san)} | ${escape(m.variation)}</span><span>${escape(m.score)}</span></div>`}
  el('results').innerHTML=html;
  if(messages.length&&!panelDismissed){el('panel').classList.add('open');el('bubble').style.display='none';placePanel()}
 }
 function postJson(path,data,timeout=15000){
  const controller=new AbortController();let expired=false;
  const timer=setTimeout(()=>{expired=true;controller.abort()},timeout);
  const promise=fetch('http://127.0.0.1:8765'+path,{method:'POST',headers:{'Content-Type':'application/json','X-Allie-Overlay':'1'},body:JSON.stringify(data),signal:controller.signal})
   .then(async response=>{let parsed={};try{parsed=await response.json()}catch{}if(!response.ok)throw Error(parsed.error||String(response.status));return parsed})
   .catch(error=>{if(expired)throw Error('Lokale Analyse braucht zu lange.');if(error.name==='AbortError')throw error;throw Error('Lokaler Allie-Server nicht erreichbar: '+error.message)})
   .finally(()=>clearTimeout(timer));
  return{promise,abort:()=>controller.abort()};
 }
 const localPost=(path,data,timeout)=>postJson(path,data,timeout).promise;
 const START_PLACEMENT='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR';
 function startPositionHistory(snapshot){
  if(snapshot?.placement!==START_PLACEMENT)return null;
  return{pgn:'*',fen:'',orientation:snapshot.orientation,placement:snapshot.placement,message:'Startstellung erkannt - Analyse startet.',ready:true,fallback_ready:false,moves_seen:0};
 }
 function pendingInsights(history){
  if(history?.placement===START_PLACEMENT)return{plan_messages:['Startstellung erkannt: Allie berechnet sofort die menschlich wahrscheinlichsten Eröffnungszüge.','Eröffnungsphase: Zentrum kontrollieren, Leichtfiguren entwickeln und den König sicher rochieren.']};
  return{plan_messages:['Stellung erkannt: Allie analysiert den aktuellen Zug.']};
 }
 async function historyFromVisibleBoard(){
  const snapshot=readBoardSnapshot();if(!snapshot)return{pgn:readHistory(),orientation:cfg.orientation==='auto'?'white':cfg.orientation,placement:''};
  const initial=startPositionHistory(snapshot);
  if(initial){lastPlacement=snapshot.placement;trackedPGN='*';trackedFen='';return initial}
  if(snapshot.placement===lastPlacement&&trackedPGN)return{pgn:trackedPGN,fen:'',orientation:snapshot.orientation,placement:snapshot.placement,fallback_ready:false};
  const expected=snapshot.placement,fallback=readHistory();
  const state=await localPost('/api/browser-position',{session_id:boardSessionId,placement:expected,pgn:fallback},12000);
  const latest=readBoardSnapshot();if(!latest||latest.placement!==expected)return{pgn:'',orientation:snapshot.orientation,placement:expected,stale:true};
  lastPlacement=expected;trackedPGN=state.ready?state.pgn:'';trackedFen=state.fallback_ready&&!state.ready?state.fen:'';
  return{pgn:trackedPGN,fen:trackedFen,orientation:snapshot.orientation,placement:expected,message:state.message,ready:state.ready,fallback_ready:state.fallback_ready,moves_seen:state.moves_seen};
 }
 function playerSideFor(orientation){return cfg.playerSide==='auto'?(orientation==='black'?'black':'white'):cfg.playerSide}
 function analyze(pgn,placement='',fen='',playerSide='white'){
   if(pending||!cfg.enabled)return;
   const basis=pgn||fen,key=JSON.stringify([pgn,fen,placement,cfg.elo,cfg.tc,playerSide]);analysisKey=key;
   const serial=++analysisSerial;
   pending=true;el('status').textContent='Allie analysiert den aktuellen Zug...';
   const current=()=>serial===analysisSerial&&analysisKey===key&&lastPGN===basis&&atHistoryEnd()&&(!placement||readBoardSnapshot()?.placement===placement);
   const request=(source,preview,final)=>{
    const data={pgn,fen,white_elo:cfg.elo,black_elo:cfg.elo,time_control:cfg.tc,review_finished:true,player_side:playerSide,analysis_source:fen?'stockfish':source,preview:fen?false:preview};
    const fail=message=>{
     if(serial!==analysisSerial)return;
     activeRequest=null;
     if(!final&&current())return request('both',true,true);
     pending=false;retryAfter=Date.now()+30000;
     if(current())el('status').textContent=message;
     scheduleTick();
    };
    activeRequest=postJson('/analyze',data,240000);
    activeRequest.promise.then(parsed=>{if(serial!==analysisSerial)return;activeRequest=null;try{
      if(!current()){pending=false;lastPGN='';return scheduleTick()}
      currentResult=parsed;show(parsed);paint(parsed);
      if(!final){el('status').textContent='Allie-Züge sichtbar · Vorschau folgt...';return request('both',true,true)}
      pending=false;el('status').textContent=`Analyse aktuell: ${parsed.move_count} Halbzuege`;
     }catch(e){fail('Analyse: '+e.message)}}).catch(error=>fail(error.name==='AbortError'?'Analyse abgebrochen.':error.message));
   };
   request(fen?'stockfish':'allie',false,!!fen);
 }
 el('now').onclick=async()=>{updateSettings();retryAfter=0;lastPlacement='';trackedPGN='';trackedFen='';await tick(true)};
 async function tick(manual=false){
  if(trackingPending)return;
  const visibleBoard=readBoardSnapshot();wrapper.style.display=visibleBoard?'':'none';if(visibleBoard)placePanel(visibleBoard.board);
  if(!visibleBoard){if(currentResult||lastPGN){currentResult=null;lastPGN='';clearOverlay();show({})}return}
  if(!cfg.enabled){clearOverlay();return}
  trackingPending=true;
  try{
   const history=await historyFromVisibleBoard(),pgn=history.pgn,fen=history.fen||'',basis=pgn||fen;
   if(!basis||!atHistoryEnd()){
    if(currentResult||lastPGN){currentResult=null;lastPGN='';clearOverlay();show({})}
    if(manual||history.message)el('status').textContent=history.message||'Brett erkannt – warte auf eine vollständige Zugfolge ab der Startstellung.';
    if(!basis){
     if(history.placement!==unsettledPlacement){unsettledPlacement=history.placement;unsettledRetries=0}
     if(unsettledRetries<4){unsettledRetries++;scheduleTick()}
    }
    return;
   }
    unsettledPlacement=history.placement;unsettledRetries=0;
    const playerSide=playerSideFor(history.orientation);
    const wanted=JSON.stringify([pgn,fen,history.placement,cfg.elo,cfg.tc,playerSide]);
    if(basis!==lastPGN||wanted!==analysisKey){
     currentResult=null;clearOverlay();show(pendingInsights(history));
     if(pending)cancelAnalysis();
     if(Date.now()>=retryAfter){lastPGN=basis;analyze(pgn,history.placement,fen,playerSide)}
    }
  }catch(error){if(manual)el('status').textContent=error.message||String(error)}finally{trackingPending=false}
 }
 window.addEventListener('resize',()=>{placePanel();if(currentResult)paint(currentResult)});
 window.addEventListener('scroll',()=>{placePanel();if(currentResult)paint(currentResult)},true);
 function scheduleTick(manual=false){clearTimeout(tickTimer);tickTimer=setTimeout(()=>tick(manual),120)}
 new MutationObserver(changes=>{
   if(changes.every(change=>wrapper.contains(change.target)||layer.contains(change.target)))return;
   scheduleTick();
 }).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','style','data-ply','data-piece','data-orientation']});
 setInterval(scheduleTick,5000);tick();
})();
