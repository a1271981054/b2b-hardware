'use strict';
window.LearningDiagrams=(()=>{
 const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const prose=s=>window.LearningWords?.render(s)||e(s);
 let opener=null;
 const viewer=document.createElement('dialog');
 viewer.className='art-viewer';viewer.setAttribute('aria-label','课程插画');
 viewer.innerHTML='<div class="art-viewer-bar"><strong></strong><button type="button" class="btn small" data-close-art aria-label="关闭插画">关闭 ×</button></div><div class="art-viewer-scroll" tabindex="0" role="region" aria-label="插画，可滚动查看"><img alt=""></div>';
 document.body.append(viewer);
 viewer.addEventListener('click',ev=>{if(ev.target===viewer||ev.target.closest('[data-close-art]'))viewer.close()});
 viewer.addEventListener('close',()=>opener?.focus());
 function render(f){
  return `<figure class="lesson-illustration" data-figure="${e(f.id)}"><figcaption><span class="art-kind">${e(f.kind)}</span><strong>${e(f.title)}</strong><button type="button" class="plain art-zoom" data-diagram-size aria-label="放大插画：${e(f.title)}">放大 ↗</button></figcaption><button type="button" class="art-image-button" data-diagram-size aria-label="放大插画：${e(f.title)}"><img src="${e(f.src)}" alt="${e(f.alt)}" loading="lazy" decoding="async" width="1536" height="1024"></button><div class="art-reading"><div class="art-cues" role="group" aria-label="图解阅读步骤">${f.nodes.map((n,i)=>`<button type="button" data-diagram-node="${i}" aria-pressed="${i===0?'true':'false'}"><span>${i+1}</span>${e(n.label)}</button>`).join('')}</div><div class="art-explanation" aria-live="polite"><strong>${e(f.nodes[0].label)}</strong><p>${prose(f.nodes[0].detail)}</p></div></div>${f.caption?`<p class="art-caption">${prose(f.caption)}</p>`:""}</figure>`;
 }
 function action(el){
  const figure=el.closest('[data-figure]');if(!figure)return;
  const f=window.KB.topics.flatMap(t=>t.chapters).flatMap(c=>c.figures).find(f=>f.id===figure.dataset.figure);if(!f)return;
  if(el.hasAttribute('data-diagram-size')){
   opener=el;viewer.querySelector('strong').textContent=f.title;
   const img=viewer.querySelector('img');img.src=f.src;img.alt=f.alt;
   viewer.showModal();viewer.querySelector('[data-close-art]').focus();return;
  }
  const index=Number(el.dataset.diagramNode);if(!Number.isInteger(index)||!f.nodes[index])return;
  figure.querySelectorAll('[data-diagram-node]').forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));
  const info=figure.querySelector('.art-explanation');info.innerHTML=`<strong>${e(f.nodes[index].label)}</strong><p>${prose(f.nodes[index].detail)}</p>`;
  if(!matchMedia('(prefers-reduced-motion: reduce)').matches&&!document.body.classList.contains('no-motion'))info.animate([{opacity:.25,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}],{duration:220});
 }
 return {render,action};
})();
