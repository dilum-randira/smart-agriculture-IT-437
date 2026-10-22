(() => {
  let observations=[];
  const panel=document.getElementById('history-chart');
  const status=document.getElementById('history-status');
  const range=document.getElementById('history-range');
  function draw(){
    const cutoff=document.getElementById('decision-date').value;
    const eligible=observations.filter(r=>r.date<=cutoff);
    const end=eligible.at(-1)?.date;
    const start=end?new Date(end+'T00:00:00Z'):null;
    if(start&&range.value!=='all')start.setUTCDate(start.getUTCDate()-Number(range.value)+1);
    const rows=eligible.filter(r=>range.value==='all'||r.date>=start.toISOString().slice(0,10));
    panel.replaceChildren();
    document.getElementById('history-values').replaceChildren();
    if(!rows.length){status.textContent='No recorded prices on or before this planning date.';return;}
    status.textContent=`${rows.length} observations · ${rows[0].date} to ${rows.at(-1).date} · on or before planning date ${cutoff}.`;
    const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
    svg.setAttribute('viewBox','0 0 800 250');svg.setAttribute('role','img');svg.setAttribute('aria-label',`Historical Dambulla Nai Miris price midpoints, ${rows[0].date} to ${rows.at(-1).date}. Exact dates and values are in the table below.`);
    function el(tag,attrs,text){const n=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;svg.append(n);return n;}
    const times=rows.map(r=>Date.parse(r.date+'T00:00:00Z')),values=rows.map(r=>r.price_lkr_per_kg);
    const lo=Math.max(0,Math.min(...values)-50),hi=Math.max(...values)+50;
    const x=t=>60+(t-times[0])/Math.max(86400000,times.at(-1)-times[0])*720;
    const y=v=>190-(v-lo)/(hi-lo)*160;
    for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4;el('line',{x1:60,x2:780,y1:y(v),y2:y(v),stroke:'#e0e8e2'});el('text',{x:50,y:y(v)+4,'text-anchor':'end','font-size':11,fill:'#596b60'},Math.round(v));}
    // Break the line across missing calendar dates rather than imply filled values.
    let segment=[];
    const flush=()=>{if(segment.length>1)el('polyline',{points:segment.join(' '),fill:'none',stroke:'#215b43','stroke-width':2});segment=[];};
    rows.forEach((r,i)=>{if(i&&times[i]-times[i-1]>86400000)flush();segment.push(`${x(times[i])},${y(r.price_lkr_per_kg)}`);const dot=el('circle',{cx:x(times[i]),cy:y(r.price_lkr_per_kg),r:rows.length>100?1.8:3,fill:'#215b43'});const title=document.createElementNS(ns,'title');title.textContent=`${r.date}: LKR ${r.price_lkr_per_kg}/kg`;dot.append(title);});flush();
    [...new Set([0,Math.floor((rows.length-1)/2),rows.length-1])].forEach(i=>el('text',{x:x(times[i]),y:224,'text-anchor':i===0?'start':i===rows.length-1?'end':'middle','font-size':11,fill:'#596b60'},rows[i].date));
    panel.append(svg);
    const table=document.createElement('table');const head=table.createTHead().insertRow();for(const title of ['Recorded date','Minimum (LKR/kg)','Maximum (LKR/kg)','Midpoint (LKR/kg)']){const th=document.createElement('th');th.scope='col';th.textContent=title;head.append(th);}const body=table.createTBody();for(const r of rows){const tr=body.insertRow();for(const v of [r.date,r.min_price_lkr_per_kg,r.max_price_lkr_per_kg,r.price_lkr_per_kg])tr.insertCell().textContent=v;}document.getElementById('history-values').append(table);
  }
  range.addEventListener('change',draw);
  document.getElementById('decision-date').addEventListener('change',draw);
  fetch('/market-history/dambulla').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{observations=d.observations.sort((a,b)=>a.date.localeCompare(b.date));draw();}).catch(()=>{status.textContent='Historical prices could not be loaded. Refresh while the local server is running.';});
})();
