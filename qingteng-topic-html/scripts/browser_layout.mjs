/** Serializable browser probes. Measures actual frames and rendered button foregrounds. */
export function buttonIssues(){
 const issues=[],white='rgb(255, 255, 255)',ink='rgb(23, 34, 30)';
 for(const b of document.querySelectorAll('.qt-t-topic .qt-btn,.qt-t-lightbox .qt-btn')){
  if(!b.getClientRects().length||getComputedStyle(b).visibility==='hidden'||b.matches(':disabled'))continue;
  const s=getComputedStyle(b),secondary=b.matches('.qt-btn-secondary,.qt-btn-inverse');
  const expected=secondary?ink:white,bg=s.backgroundColor;
  const rgb=bg.match(/[\d.]+/g)?.map(Number)||[];
  const validBackground=secondary?bg===white:rgb.length>=3&&rgb[1]>rgb[0]&&rgb[1]>rgb[2]&&(rgb[3]??1)===1;
  const texts=[b,...b.querySelectorAll('*')].filter(e=>[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()));
  if(!validBackground||texts.some(e=>getComputedStyle(e).color!==expected))issues.push({text:b.textContent.trim().slice(0,60),background:bg,expectedText:expected,actualText:texts.map(e=>getComputedStyle(e).color)});
 }
 return issues;
}

export function alignmentIssues(){
 const issues=[],visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';
 const box=e=>e.getBoundingClientRect(),module=e=>e.closest('[data-module-id]')?.dataset.moduleId;
 const delta=values=>Math.max(...values)-Math.min(...values);
 const peerSelector='[data-qt-group],.qt-t-group,.qt-t-production,[data-qt-composition="parallel"]';
 const round=n=>Math.round(n*100)/100;
 function rowsOf(peers){
  const rows=[];
  for(const peer of peers){const r=box(peer);let row=rows.find(row=>row.some(p=>{const a=box(p);return Math.min(a.bottom,r.bottom)>Math.max(a.top,r.top)+2&&Math.min(a.right,r.right)<=Math.max(a.left,r.left)+2;}));if(row)row.push(peer);else rows.push([peer]);}
  return rows;
 }
 function painted(img){
  const r=box(img),s=getComputedStyle(img),px=v=>parseFloat(v)||0;
  const left=r.left+px(s.borderLeftWidth)+px(s.paddingLeft),top=r.top+px(s.borderTopWidth)+px(s.paddingTop);
  const cw=r.width-px(s.borderLeftWidth)-px(s.borderRightWidth)-px(s.paddingLeft)-px(s.paddingRight),ch=r.height-px(s.borderTopWidth)-px(s.borderBottomWidth)-px(s.paddingTop)-px(s.paddingBottom);
  if(s.objectFit!=='contain'||!img.naturalWidth||!img.naturalHeight)return {left,right:left+cw,top,bottom:top+ch};
  const scale=Math.min(cw/img.naturalWidth,ch/img.naturalHeight),w=img.naturalWidth*scale,h=img.naturalHeight*scale,tokens=s.objectPosition.match(/calc\([^)]*\)|[^\s]+/g)||[];
  const offset=(token,space)=>{const n=token?.match(/^([+-]?(?:\d*\.)?\d+)(%|px)$/);return ['left','top'].includes(token)?0:['right','bottom'].includes(token)?space:token==='center'?space/2:n?Number(n[1])*(n[2]==='%'?space/100:1):null;};
  const x=offset(tokens[0],cw-w),y=offset(tokens[1],ch-h);if(tokens.length!==2||x===null||y===null)return null;
  return {left:left+x,right:left+x+w,top:top+y,bottom:top+y+h};
 }
 function contentBottom(root){
  let bottom=box(root).top;const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  for(let n=walker.nextNode();n;n=walker.nextNode()){
   if(!n.textContent.trim()||!visible(n.parentElement)||n.parentElement.closest('script,style,[aria-hidden="true"]'))continue;
   const range=document.createRange();range.selectNodeContents(n);for(const r of range.getClientRects())if(r.width&&r.height)bottom=Math.max(bottom,r.bottom);
  }
  for(const media of root.querySelectorAll('img,video,svg'))if(visible(media)){const r=media.matches('img')?painted(media):box(media);if(r)bottom=Math.max(bottom,r.bottom);}
  return bottom;
 }
 function surface(e){const s=getComputedStyle(e);return !['transparent','rgba(0, 0, 0, 0)'].includes(s.backgroundColor)||parseFloat(s.borderBottomWidth)>0||s.boxShadow!=='none';}
 for(const group of document.querySelectorAll('main [data-qt-group],main .qt-t-group,main .qt-t-production,main [data-qt-composition="parallel"]')){
  const peers=[...group.children].filter(visible),rows=rowsOf(peers);
  // Grouping by a coincident top would miss the very top misalignment being tested.
  for(const row of rows){
   if(row.length<2)continue;
   if(delta(row.map(e=>box(e).top))>2||delta(row.map(e=>box(e).bottom))>2)issues.push({type:'visible-peer-frames',module:module(group),bottoms:row.map(e=>round(box(e).bottom))});
   for(const peer of row){
    const r=box(peer),s=getComputedStyle(peer),tail=r.bottom-(parseFloat(s.paddingBottom)||0)-(parseFloat(s.borderBottomWidth)||0)-contentBottom(peer);
    if(surface(peer)&&tail>Math.max(48,r.height*.2))issues.push({type:'peer-content-balance',module:module(group),emptyTail:round(tail),height:round(r.height)});
   }
   const names=[...new Set(row.flatMap(e=>[...e.querySelectorAll('[data-qt-field]')].filter(f=>visible(f)&&f.closest(peerSelector)===group).map(f=>f.dataset.qtField)))];
   for(const name of names){
    const fields=row.map(e=>[...e.querySelectorAll('[data-qt-field]')].find(f=>visible(f)&&f.dataset.qtField===name&&f.closest(peerSelector)===group));
    if(fields.some(f=>!f)){issues.push({type:'missing-peer-field',module:module(group),field:name});continue;}
    if(delta(fields.map(e=>box(e).top))>2||delta(fields.map(e=>box(e).bottom))>2)issues.push({type:'peer-field-alignment',module:module(group),field:name});
   }
   const anchors=row.map(e=>[...e.querySelectorAll('[data-qt-anchor]')].filter(f=>visible(f)&&f.closest(peerSelector)===group));
   for(const name of new Set(anchors.flat().map(e=>e.dataset.qtAnchor))){
    const matches=anchors.map(a=>a.filter(e=>e.dataset.qtAnchor===name));
    if(matches.some(a=>a.length!==1)){issues.push({type:'missing-or-duplicate-peer-anchor',module:module(group),anchor:name});continue;}
    if(delta(matches.map(a=>box(a[0]).top))>2)issues.push({type:'peer-anchor-alignment',module:module(group),anchor:name});
   }
  }
 }
 // Authored class names cannot silently opt a content row out of acceptance.
 const known=peerSelector+',.qt-t-cluster,.qt-t-evidence,.qt-t-hero,.qt-t-illustrated,.qt-t-fit,[data-qt-fit],.qt-t-change,.qt-t-scene,.qt-t-row,.qt-t-quadrants,.qt-t-scroll-viewport';
 const substantive=e=>e.matches('figure,article,dl,ol,ul')||!!e.querySelector('figure,dl,ol,ul,h3,p');
 for(const group of document.querySelectorAll('main div,main section,main article')){
  if(!visible(group))continue;
  const peers=[...group.children].filter(visible),s=getComputedStyle(group);
  const rows=/^(inline-)?(flex|grid)$/.test(s.display)?rowsOf(peers.filter(substantive)).filter(r=>r.length>1):[];
  if(rows.length&&!group.matches(known))issues.push({type:'unregistered-composition',module:module(group),element:group.className,reason:'Use a supported composition or declare data-qt-composition="parallel" and check its visible boundaries.'});
  if(group.matches('.qt-t-evidence'))for(const row of rows){
   const heights=row.map(e=>contentBottom(e)-box(e).top),gap=delta(heights);
   if(gap>Math.max(32,Math.max(...heights)*.2))issues.push({type:'composition-balance',module:module(group),contentHeights:heights.map(round),gap:round(gap)});
  }
  // Full-width figures in a vertical photo column imply common visible edges.
  const photos=peers.map(e=>e.matches('figure')?e:e.children.length===1&&e.firstElementChild.matches('figure')?e.firstElementChild:null).filter(f=>f?.dataset.mediaRole==='photo');
  if(photos.length>1&&delta(photos.map(f=>box(f).left))<=2&&delta(photos.map(f=>box(f).right))<=2){
   const images=photos.map(f=>f.querySelector('img')),paints=images.map(i=>i&&painted(i));
   if(paints.every(Boolean)&&(delta(paints.map(r=>r.left))>2||delta(paints.map(r=>r.right))>2))issues.push({type:'photo-column-edges',module:module(group),edges:paints.map(r=>({left:round(r.left),right:round(r.right)}))});
  }
 }
 for(const cluster of document.querySelectorAll('main .qt-t-cluster')){
  const peers=[...cluster.children].filter(visible);if(peers.length!==2)continue;
  const [a,b]=peers,ar=box(a),br=box(b);if(Math.abs(ar.top-br.top)>2)continue;
  let frames=[b];
  if(!b.matches('.qt-t-card,.qt-t-primary-card,figure'))frames=[...b.querySelectorAll('.qt-t-card,.qt-t-primary-card,figure,.qt-t-production > li')].filter(visible);
  // Do not substitute an empty stretch wrapper for a real frame.
  const bottom=frames.length?Math.max(...frames.map(e=>box(e).bottom)):br.top;
  const gap=Math.abs(ar.bottom-bottom);
  if(gap>2)issues.push({type:'cluster-visible-bottom',module:module(cluster),gap:Math.round(gap*100)/100});
 }
 const baselines=new Map();
 for(const e of document.querySelectorAll('main [data-qt-baseline]')){
  if(!visible(e))continue;
  const edge=e.dataset.qtBaselineEdge||'left',name=e.dataset.qtBaseline;
  if(!name||!['left','right'].includes(edge)){issues.push({type:'invalid-baseline',module:module(e)});continue;}
  const key=name+':'+edge,points=baselines.get(key)||[];points.push({module:module(e),position:box(e)[edge]});baselines.set(key,points);
 }
 for(const [name,points] of baselines)if(points.length>1&&delta(points.map(p=>p.position))>2)issues.push({type:'baseline-line',baseline:name,points});
 for(const facts of document.querySelectorAll('main .qt-t-facts')){
  const rows=[...facts.querySelectorAll(':scope > .qt-t-fact')].filter(visible),values=[];
  for(const row of rows){const label=row.querySelector('dt'),value=row.querySelector('dd');
   if(!label||!value){issues.push({type:'fact-structure',module:module(row)});continue;}
   const a=box(label),b=box(value);values.push(b.left);
   if(Math.abs(a.top-b.top)>2||b.left<a.right+2)issues.push({type:'fact-label-value',module:module(row)});
  }
  if(values.length>1&&delta(values)>2)issues.push({type:'fact-value-column',module:module(facts)});
 }
 for(const f of document.querySelectorAll('main figure[data-qt-media-align]')){
  const img=f.querySelector('img'),caption=f.querySelector('figcaption'),align=f.dataset.qtMediaAlign;if(!img||!caption||!visible(f))continue;
  if(!img.naturalWidth||!img.naturalHeight){issues.push({type:'media-alignment-unreadable',module:module(f),media:f.dataset.mediaId});continue;}
  const r=box(img),c=box(caption),s=getComputedStyle(img),cs=getComputedStyle(caption),px=v=>parseFloat(v)||0;
  const start=r.left+px(s.borderLeftWidth)+px(s.paddingLeft),cw=r.width-px(s.borderLeftWidth)-px(s.borderRightWidth)-px(s.paddingLeft)-px(s.paddingRight),ch=r.height-px(s.borderTopWidth)-px(s.borderBottomWidth)-px(s.paddingTop)-px(s.paddingBottom);
  const contain=s.objectFit==='contain',scale=Math.min(cw/img.naturalWidth,ch/img.naturalHeight),w=contain?img.naturalWidth*scale:cw;
  const tokens=s.objectPosition.match(/calc\([^)]*\)|[^\s]+/g)||[],position=tokens[0],number=position?.match(/^([+-]?(?:\d*\.)?\d+)(%|px)$/);
  let offset=position==='left'?0:position==='right'?cw-w:position==='center'?(cw-w)/2:number?Number(number[1])*(number[2]==='%'?(cw-w)/100:1):null;
  // Complex positions need visual review; a guessed percentage must not fail layout.
  if(tokens.length!==2||offset===null)continue;
  const captionStart=c.left+px(cs.borderLeftWidth)+px(cs.paddingLeft),captionEnd=c.right-px(cs.borderRightWidth)-px(cs.paddingRight);
  const actual=align==='start'?start+offset:start+offset+w/2,expected=align==='start'?captionStart:(captionStart+captionEnd)/2;
  if(!['start','center'].includes(align)||Math.abs(actual-expected)>2)issues.push({type:'media-content-caption',module:module(f),media:f.dataset.mediaId,align,actual,expected});
 }
 return issues;
}
