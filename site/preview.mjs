// Independent UI-only heuristic; not the frozen SqlVizSpec or SDK.
export function recommend(sql,rows){
 if(typeof sql!=='string'||!sql.trim()||sql.length>20000)throw Error('Provide SQL text (max 20,000 characters).');
 if(!Array.isArray(rows)||rows.length<1||rows.length>5000||rows.some(r=>!r||typeof r!=='object'||Array.isArray(r)))throw Error('Provide 1–5,000 JSON objects.');
 const keys=Object.keys(rows[0]);if(!keys.length||keys.length>50||rows.some(r=>Object.keys(r).length!==keys.length||keys.some(k=>!Object.hasOwn(r,k)||!(r[k]===null||['string','number','boolean'].includes(typeof r[k]))||(typeof r[k]==='number'&&!Number.isFinite(r[k])))))throw Error('Rows must share 1–50 scalar columns.');
 const numeric=keys.filter(k=>rows.every(r=>typeof r[k]==='number')),text=keys.filter(k=>rows.every(r=>typeof r[k]==='string'));
 const warnings=[];if(/\bAVG\s*\(|\bCOUNT\s*\(\s*DISTINCT\b/i.test(sql))warnings.push('Stacking rejected: aggregation may be non-additive. Disjointness or recomposition evidence is required.');
 const plan=(chartType,reason,encodings={})=>({mode:'deterministic-preview',chartType,reason,encodings,warnings});
 if(rows.length===1&&keys.length===1&&numeric.length===1)return plan('kpi','One numeric scalar.',{y:numeric[0]});
 if(keys.length===2&&numeric.length===1&&text.length===1&&rows.length<=100&&new Set(rows.map(r=>r[text[0]])).size===rows.length){
 const temporal=rows.length>=4&&rows.every(r=>/^\d{4}-\d{2}(?:-\d{2})?$/.test(r[text[0]]))&&rows.every((r,i)=>i===0||r[text[0]]>rows[i-1][text[0]]);
 return plan(temporal?'line':rows.length>12?'horizontal_bar':'bar',temporal?'Ordered ISO-like period labels.':'Unique categories and one numeric measure.',{x:text[0],y:numeric[0]});}
 return plan('table','No supported safe preview chart for this shape.');
}