// CSV import: RFC4180-style quoting, explicit scalar coercion and bounded input.
export function parseCsv(text){
 if(typeof text!=='string'||text.length>2_000_000)throw Error('CSV exceeds 2 MB character limit');
 text=text.replace(/^\uFEFF/,'');const records=[];let row=[],field='',state='start';
 function cell(){row.push(field);field='';state='start';if(row.length>50)throw Error('Maximum 50 columns');}
 function record(){cell();records.push(row);row=[];if(records.length>5001)throw Error('Maximum 5,000 data rows');}
 for(let i=0;i<text.length;i++){
  const c=text[i];if(state==='quoted'){if(c==='"'){if(text[i+1]==='"'){field+='"';i++;}else state='closed';}else field+=c;continue;}
  if(c===',' ){cell();continue;}
  if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;record();continue;}
  if(state==='closed')throw Error('Unexpected character after closing quote');
  if(c==='"'){if(state!=='start')throw Error('Unexpected quote');state='quoted';continue;}
  field+=c;state='plain';
 }
 if(state==='quoted')throw Error('Unclosed quoted field');
 if(row.length||field.length||state!=='start')record();
 if(records.length<2)throw Error('CSV requires headers and at least one data row');
 const keys=records.shift().map(v=>v.trim());if(keys.some(k=>!k)||new Set(keys).size!==keys.length)throw Error('Headers must be unique and nonempty');
 const scalar=v=>{if(v==='')return null;if(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(v)){const n=Number(v);if(Number.isFinite(n)&&(!Number.isInteger(n)||Number.isSafeInteger(n)))return n;}return v;};
 return records.map((r,i)=>{if(r.length!==keys.length)throw Error('Inconsistent column count at data row '+(i+1));return Object.fromEntries(keys.map((k,j)=>[k,scalar(r[j])]));});
}
