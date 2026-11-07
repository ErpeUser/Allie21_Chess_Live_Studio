// ==UserScript==
// @name         Allie 2.1 Live Studio v10 (Manuelles Live-Overlay)
// @namespace    local.allie21.study
// @version      10.7.0
// @description  Permanent Allie move, opponent and pre-move arrows on visible DOM chess boards.
// @match        *://*/*
// @run-at       document-idle
// @noframes
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// ==/UserScript==
/*
  No auto-moves and never clicks on the chess site. The local service is bound
  to 127.0.0.1 and needs no account or access key.
*/
(() => {
 'use strict';
 if (window.top !== window.self || document.getElementById('allie21-auto-study-root')) return;
 const STORE='allie21.auto.v10';
 const cfg=Object.assign({elo:1950,tc:'600+0',enabled:true,orientation:'auto'}, GM_getValue(STORE,{}));
 const save=()=>GM_setValue(STORE,cfg);
 const wrapper=document.createElement('div');
 wrapper.id='allie21-auto-study-root';
 wrapper.style.cssText='all:initial;display:none;position:fixed;right:15px;bottom:18px;z-index:2147483000;font-family:system-ui,sans-serif;color:#e7f2ff';
 document.documentElement.appendChild(wrapper);
 const shadow=wrapper.attachShadow({mode:'open'});
 shadow.innerHTML=`
 <style>
 *{box-sizing:border-box}button,input,select{font:inherit}#bubble{background:#10283d;color:#eaf6ff;border:1px solid #48758c;border-radius:25px;padding:9px 13px;font-size:12px;font-weight:650;cursor:pointer;box-shadow:0 2px 10px #0008}
 #panel{display:none;width:365px;max-width:calc(100vw - 24px);max-height:78vh;overflow:auto;background:#102236;color:#e7f2ff;border:1px solid #43657e;box-shadow:0 10px 35px #0009;border-radius:12px;padding:13px;line-height:1.4;font-size:12px}
 #panel.open{display:block}h3{margin:9px 0 5px;color:#8de0c5;font-size:13px}p{margin:6px 0}label{display:block;margin:7px 0 4px}.row{display:flex;gap:7px;align-items:center}.row>*{flex:1;min-width:0}input,select{width:100%;padding:7px;background:#091724;border:1px solid #3c6076;border-radius:5px;color:#e6f3ff}
 button{border:1px solid #3c6076;background:#285474;color:white;border-radius:6px;padding:8px;cursor:pointer}.item{display:flex;gap:8px;justify-content:space-between;border-bottom:1px solid #325068;padding:5px 0}.stat{color:#a6d9e3}.warn{color:#ffccaf}.small{font-size:11px;color:#abc4d6}#results{margin-top:6px}
 </style>
 <button id='bubble'>Allie 2.1 | Analyse</button>
 <section id='panel'><div class='row'><b style='font-size:15px'>Allie 2.1 | Live Overlay</b><button id='close'>X</button></div>
 <p class='small'>Allie wählt menschlich passend zu Elo und Zeit; Stockfish bleibt nur der objektive Vergleich.</p>
 <div class='row'><div><label>Elo</label><input id='elo' type='number' min='600' max='2800'/></div>
 <div><label>Zeitkontrolle</label><input id='tc' placeholder='600+0'/></div></div>
 <label>Brettorientierung</label><select id='orientation'><option value='auto'>Automatisch</option><option value='white'>Weiss unten</option><option value='black'>Schwarz unten</option></select>
 <div class='row' style='margin-top:8px'><button id='toggle'>Live-Hinweise: Ein</button><button id='now'>Jetzt analysieren</button></div>
 <p id='status' class='stat'>Lokalen Server starten; die Analyse verbindet sich automatisch.</p>
 <div id='results'></div><p class='small'>Rot = Gegner · Grün = du · Blau = Pre-Move. Allie klickt nie selbst.</p>
 </section>`;
 const el=id=>shadow.getElementById(id);
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 el('bubble').onclick=()=>{el('panel').classList.toggle('open');el('bubble').style.display=el('panel').classList.contains('open')?'none':''};
 el('close').onclick=()=>{el('panel').classList.remove('open');el('bubble').style.display=''};
 const updateSettings=()=>{cfg.elo=Number(el('elo').value)||1950;cfg.tc=el('tc').value.trim()||'600+0';cfg.orientation=el('orientation').value;save()};
 for(const field of ['elo','tc','orientation'])el(field).addEventListener('change',updateSettings);
 const fill=()=>{el('elo').value=cfg.elo;el('tc').value=cfg.tc;el('orientation').value=cfg.orientation;el('toggle').textContent=`Live-Hinweise: ${cfg.enabled?'Ein':'Aus'}`};fill();
 el('toggle').onclick=()=>{cfg.enabled=!cfg.enabled;save();fill();if(!cfg.enabled)clearOverlay()};
 let pending=false,lastPGN='',currentResult=null,retryAfter=0,lastPlacement='',trackedPGN='',trackingPending=false,currentBoard=null;
 const sessionSeed=location.hostname+location.pathname;
 let sessionHash=2166136261;for(const char of sessionSeed){sessionHash^=char.charCodeAt(0);sessionHash=Math.imul(sessionHash,16777619)}
 const boardSessionId='web-'+(sessionHash>>>0).toString(36);
 const selectors=['wc-move-list .main-line-ply','wc-move-list .move','wc-move-list [data-ply]','wc-move-list .node','wc-move-list [class*="move-node"]','wc-simple-move-list [data-ply]','wc-simple-move-list [class*="move"]','wc-vertical-move-list [data-ply]','wc-vertical-move-list [class*="move"]','[data-cy="move-list"] [data-ply]','[data-cy="move-list"] [class*="move"]','l4x l4','l4x move','.analyse__moves move','.analyse__moves .san','.vertical-move-list .move','.move-list .move','.move-list-component .move','.pgn-viewer .san','.analysis-moves .san','.move-text-component'];
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
   const descendants=Array.from(node.querySelectorAll?.('[data-figurine],[data-piece],[class*="knight"],[class*="bishop"],[class*="rook"],[class*="queen"],[class*="king"]')||[]).slice(0,5);
   const signature=[node,...descendants].map(n=>`${n.getAttribute?.('data-figurine')||''} ${n.getAttribute?.('data-piece')||''} ${String(n.className||'')}`).join(' ').toLowerCase();
   const piece=/knight|(?:^|\s)[bn]n?(?:\s|$)/.test(signature)?'N':/bishop/.test(signature)?'B':/rook/.test(signature)?'R':/queen/.test(signature)?'Q':/king/.test(signature)?'K':'';
   if(piece)value=piece+value;
  }
  return value;
 }
 function movesFromNodes(nodes){return Array.from(nodes).slice(0,1100).map(n=>cleanMove(n.textContent,n)).filter(s=>sanPattern.test(s))}
 function startsAtMoveOne(root){
  if(root.querySelector?.('[data-ply="0"],[data-ply="1"],[data-move-number="1"]'))return true;
  const text=(root.textContent||'').trim().slice(0,240);
  return /(?:^|\s)1\s*\./.test(text)||/^1(?=[a-hKQRBN♔♕♖♗♘♚♛♜♝♞])/.test(text);
 }
 function movesFromRoot(root){
  const preferred=root.querySelectorAll?.('[data-ply],.main-line-ply,.move,.node,.san,[class*="move-node"],[class*="move-text"],[class*="move-san"]')||[];
  let moves=movesFromNodes(preferred);
  if(moves.length<2){
   const leaves=Array.from(root.querySelectorAll?.('*')||[]).filter(n=>n.children.length===0&&cleanMove(n.textContent,n));
   moves=movesFromNodes(leaves);
  }
  const compact=[];for(const move of moves)if(move!==compact.at(-1))compact.push(move);
  return compact;
 }
 function candidateMoveRoots(){
  const rootSelectors=['wc-move-list','wc-simple-move-list','wc-vertical-move-list','.analyse__moves','.vertical-move-list','.move-list','.move-list-component','.pgn-viewer','.analysis-moves','[data-cy="move-list"]','[class*="move-list"]'];
  const roots=Array.from(document.querySelectorAll(rootSelectors.join(',')));
  for(const node of Array.from(document.querySelectorAll('*')).filter(n=>/move/.test(n.localName||'')).slice(0,80))roots.push(node);
  return Array.from(new Set(roots)).filter(root=>!root.closest('#allie21-auto-study-root')&&startsAtMoveOne(root));
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
  // IMPORTANT: a virtualised or scrolled list may contain only moves 23-31.
  // Never renumber that fragment as if it started at move one.
  const sources=['wc-move-list','wc-simple-move-list','wc-vertical-move-list','l4x','.analyse__moves','.vertical-move-list',
                 '.move-list','.move-list-component','.pgn-viewer','.analysis-moves','[data-cy="move-list"]','[class*="move-list"]'];
  const roots=sources.map(sel=>document.querySelector(sel)).filter(Boolean);roots.push(...candidateMoveRoots());if(structural)roots.push(structural);
  if(!roots.some(startsAtMoveOne))return '';

  // UCI/SAN from the first halfmove; Python validates every move before analysis.
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
  let nodes=Array.from(board.querySelectorAll(selector));
  if(nodes.filter(pieceCode).length<2)nodes=Array.from(board.querySelectorAll('*')).slice(0,900).filter(pieceCode);
  return Array.from(new Set(nodes)).filter(pieceCode);
 }
 function boardOrientation(board,pieces){
  if(cfg.orientation!=='auto')return cfg.orientation;
  const attribute=(board?.getAttribute?.('data-orientation')||'').trim().toLowerCase();
  if(attribute==='black')return 'black';if(attribute==='white')return 'white';
  const explicit=(board?.parentElement?.className||'')+' '+(board?.className||'');
  if(/\b(flipped|orientation-black|black-bottom|board-layout-flipped)\b/i.test(explicit)&&!/orientation-white/i.test(explicit))return 'black';
  if(document.querySelector('.orientation-black,.flipped.chess-board,.board.flipped,.board-layout-flipped'))return 'black';
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
  const known=Array.from(document.querySelectorAll(selector)).filter(node=>!node.closest('#allie21-auto-study-root')).sort(sortByArea);
  const generic=Array.from(document.querySelectorAll('div,section,main')).filter(node=>{const r=node.getBoundingClientRect(),ratio=r.width/Math.max(1,r.height);return r.width>=160&&r.width<=1400&&ratio>.88&&ratio<1.12&&node.children.length>1&&!node.closest('#allie21-auto-study-root')}).sort(sortByArea).slice(0,120);
  return Array.from(new Set([...known,...generic]));
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
  const width=Math.max(4,rect.width/38);
  mk('line',{x1:sx,y1:sy,x2:tx,y2:ty,stroke:color,'stroke-width':width,'stroke-linecap':'round',opacity});
  let angle=Math.atan2(dy,dx),size=rect.width/17;
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
  (data.opponent_moves||[]).slice(0,2).forEach((m,i)=>drawArrow(svg,rect,ori,m.uci,i===0?'#ff3f36':'#ff8b84',i===0?.96:.62));
  (data.my_moves||[]).slice(0,2).forEach((m,i)=>drawArrow(svg,rect,ori,m.uci,i===0?'#18dc98':'#78e8c1',i===0?.96:.65));
  if(data.premove)drawArrow(svg,rect,ori,data.premove.uci,'#389cff',.96);
  layer.replaceChildren(svg);
  const messages=(data.plan_messages||[]).slice(0,5);
  if(messages.length){
    const notes=document.createElement('div');notes.style.cssText='position:fixed;pointer-events:none;box-sizing:border-box;background:rgba(10,24,37,.96);border:1px solid #4ca99c;border-radius:12px;padding:11px;color:#edfafb;width:300px;max-width:calc(100vw - 16px);font:12px/1.4 system-ui,sans-serif;box-shadow:0 5px 22px #0009;white-space:normal';
    let left=rect.right+10,top=Math.max(10,rect.top);
    if(left+310>innerWidth)left=Math.max(10,rect.left-310);
    if(rect.left<310 && rect.right+310>innerWidth){left=Math.max(8,rect.left);top=Math.min(innerHeight-210,rect.bottom+8)}
    notes.style.left=left+'px';notes.style.top=top+'px';
    const add=(text,css='')=>{const d=document.createElement('div');d.style.cssText=css;d.textContent=text;notes.appendChild(d);return d};
    add('Allie · Live','font-weight:800;font-size:14px;color:#9cf0d5;margin-bottom:3px');
    add('🔴 Gegner  ·  🟢 Du  ·  🔵 Pre-Move','color:#a9bdca;font-size:10px;margin-bottom:7px');
    messages.forEach(message=>add(message,'background:#ffffff0b;border-radius:10px 10px 10px 3px;padding:7px 8px;margin:6px 0;color:#e7f2f7'));
    layer.appendChild(notes);
  }
 }
 function show(data){let html='';
  if(data.allie_skip_reason)html+=`<p class='warn'>${escape(data.allie_skip_reason)}</p>`;
  for(const message of data.plan_messages||[])html+=`<p style='background:#ffffff0b;border-radius:8px;padding:7px'>${escape(message)}</p>`;
  if(data.stockfish){html+='<h3>Stockfish: objektiv</h3>';if(!data.stockfish.available)html+=`<p>${escape(data.stockfish.error||'Engine fehlt')}</p>`;else for(const m of data.stockfish.lines||[])html+=`<div class='item'><span>${escape(m.san)} | ${escape(m.variation)}</span><span>${escape(m.score)}</span></div>`}
  el('results').innerHTML=html;
 }
 function localPost(path,data,timeout=15000){return new Promise((resolve,reject)=>GM_xmlhttpRequest({method:'POST',url:'http://127.0.0.1:8765'+path,timeout,headers:{'Content-Type':'application/json','X-Allie-Overlay':'1'},data:JSON.stringify(data),onload:r=>{try{const parsed=JSON.parse(r.responseText);if(r.status!==200)throw Error(parsed.error||String(r.status));resolve(parsed)}catch(e){reject(e)}},onerror:()=>reject(Error('Lokaler Allie-Server nicht erreichbar.')),ontimeout:()=>reject(Error('Lokale Brett-Erkennung braucht zu lange.'))}))}
 async function historyFromVisibleBoard(){
  const snapshot=readBoardSnapshot();if(!snapshot)return{pgn:readHistory(),orientation:cfg.orientation==='auto'?'white':cfg.orientation,placement:''};
  if(snapshot.placement===lastPlacement&&trackedPGN)return{pgn:trackedPGN,orientation:snapshot.orientation,placement:snapshot.placement};
  const expected=snapshot.placement,fallback=readHistory();
  const state=await localPost('/api/browser-position',{session_id:boardSessionId,placement:expected,pgn:fallback},12000);
  const latest=readBoardSnapshot();if(!latest||latest.placement!==expected)return{pgn:'',orientation:snapshot.orientation,placement:expected,stale:true};
  lastPlacement=expected;trackedPGN=state.ready?state.pgn:'';
  return{pgn:trackedPGN,orientation:snapshot.orientation,placement:expected,message:state.message,ready:state.ready,moves_seen:state.moves_seen};
 }
 function analyze(pgn,orientation,placement=''){
   if(pending||!cfg.enabled)return;
   pending=true;el('status').textContent='Stockfish startet sofort · Allie rechnet parallel...';
   const base={pgn,white_elo:cfg.elo,black_elo:cfg.elo,time_control:cfg.tc,review_finished:true,player_side:orientation||boardOrientation(boardElement())};
   const request=(data,timeout,onload,onfail)=>GM_xmlhttpRequest({method:'POST',url:'http://127.0.0.1:8765/analyze',timeout,
    headers:{'Content-Type':'application/json','X-Allie-Overlay':'1'},data:JSON.stringify(data),
    onload:r=>{try{const parsed=JSON.parse(r.responseText);if(r.status!==200)throw Error(parsed.error||String(r.status));onload(parsed)}catch(e){onfail(e.message)}},
    onerror:()=>onfail('Backend nicht erreichbar. Python-Server starten.'),ontimeout:()=>onfail('Backend-Zeitlimit.')});
   const current=()=>lastPGN===pgn&&atHistoryEnd()&&(!placement||readBoardSnapshot()?.placement===placement);
   let allieDone=false;
   request({...base,analysis_source:'stockfish',stockfish_time:.35,preview:false},30000,data=>{
     if(!current()||allieDone)return;currentResult=data;el('status').textContent='Stockfish sichtbar · Allie rechnet parallel...';show(data);paint(data);
   },message=>{if(current())el('status').textContent='Stockfish: '+message});
   request({...base,analysis_source:'allie',preview:true},240000,data=>{
     allieDone=true;pending=false;if(!current()){lastPGN='';clearOverlay();return}currentResult=data;el('status').textContent=`Allie aktuell: ${data.move_count} Halbzuege`;show(data);paint(data);
   },message=>{allieDone=true;pending=false;retryAfter=Date.now()+30000;if(!current()){lastPGN='';clearOverlay();return}el('status').textContent='Allie: '+message;if(!currentResult)lastPGN=''});
 }
 el('now').onclick=async()=>{updateSettings();retryAfter=0;lastPlacement='';trackedPGN='';await tick(true)};
 async function tick(manual=false){
  if(trackingPending)return;
  const visibleBoard=readBoardSnapshot();wrapper.style.display=visibleBoard?'':'none';
  if(!visibleBoard){if(currentResult||lastPGN){currentResult=null;lastPGN='';clearOverlay();show({})}return}
  if(!cfg.enabled){clearOverlay();return}
  trackingPending=true;
  try{
   const history=await historyFromVisibleBoard(),pgn=history.pgn;
   if(!pgn||!atHistoryEnd()){
    if(currentResult||lastPGN){currentResult=null;lastPGN='';clearOverlay();show({})}
    if(manual||history.message)el('status').textContent=history.message||'Brett erkannt – warte auf eine vollständige Zugfolge ab der Startstellung.';
    return;
   }
   if(pgn!==lastPGN){
    currentResult=null;clearOverlay();show({});
    if(pending){lastPGN='';return}
    if(Date.now()>=retryAfter){lastPGN=pgn;analyze(pgn,history.orientation,history.placement)}
   }else if(currentResult)paint(currentResult);
  }catch(error){if(manual)el('status').textContent=error.message||String(error)}finally{trackingPending=false}
 }
 window.addEventListener('resize',()=>currentResult&&paint(currentResult));
 window.addEventListener('scroll',()=>currentResult&&paint(currentResult),true);
 setInterval(tick,2200);tick();
})();
