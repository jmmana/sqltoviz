export * from "./features.js";
export * from "./contract.js";
export * from "./rules.js";
export * from "./engine.js";
import type {Cell} from "./features.js";
export type Row=Record<string,Cell>;
export type Plan={contract_version:"preview-v0.1";mode:"deterministic-preview";chartType:"kpi"|"bar"|"horizontal_bar"|"line"|"table";encodings:{x?:string;y?:string};reason:string;warnings:string[];insights:Record<string,ReturnType<typeof madOutliers>>};
const numeric=(x:unknown):x is number=>typeof x==="number"&&Number.isFinite(x);
const median=(v:number[])=>{const a=[...v].sort((x,y)=>x-y),i=Math.floor(a.length/2);return a.length%2?a[i]:a[i-1]/2+a[i]/2;};
export function madOutliers(values:unknown[],threshold=3.5){
 if(!numeric(threshold)||threshold<=0)throw new RangeError("threshold");
 const p=values.flatMap((v,i)=>numeric(v)?[{i,v}]:[]);
 if(p.length<3)return {status:"insufficient_samples",outliers:[] as {index:number;score:number}[]};
 const center=median(p.map(x=>x.v)),mad=median(p.map(x=>Math.abs(x.v-center)));
 if(mad===0)return {status:"zero_mad",median:center,mad,outliers:[]};
 const scores=p.map(x=>({index:x.i,score:0.6744897501960817*((x.v-center)/mad)}));
 if(scores.some(x=>!numeric(x.score)))return {status:"numeric_overflow",outliers:[]};
 return {status:"ok",median:center,mad,outliers:scores.filter(x=>Math.abs(x.score)>threshold)};
}
export function temporalShifts(values:unknown[]){
 return values.slice(1).map((b,j)=>{const a=values[j],index=j+1;if(!numeric(a)||!numeric(b))return {index,status:"missing",delta:null,relative_change:null};const delta=b-a;if(!numeric(delta))return {index,status:"numeric_overflow",delta:null,relative_change:null};const c=a===0?null:delta/Math.abs(a);return {index,status:a===0?"zero_baseline":numeric(c)?"ok":"numeric_overflow",delta,relative_change:numeric(c)?c:null};});
}
export function pareto(values:unknown[],coverage=0.8,additive=false){
 if(!numeric(coverage)||coverage<=0||coverage>1)throw new RangeError("coverage");
 if(!additive)return {status:"unknown_additivity",items:[]};
 if(values.some(v=>!numeric(v)||v<0))return {status:"invalid_weights",items:[]};
 const a=values as number[],scale=a.reduce((m,v)=>Math.max(m,v),0);
 if(!scale)return {status:"zero_total",items:[]};
 const total=a.reduce((s,v)=>s+v/scale,0);let running=0,reached=false;
 const items=a.map((v,index)=>({v,index})).sort((a,b)=>b.v-a.v||a.index-b.index).map(({v,index})=>{const share=v/scale/total;running=Math.min(1,running+share);const included=!reached&&v>0;reached ||= running>=coverage-1e-15;return {index,share,cumulative:running,included};});
 return {status:"ok",items};
}
export function pearson(xs:unknown[],ys:unknown[]){
 if(xs.length!==ys.length)throw new RangeError("paired arrays");
 const p: [number,number][]=[];xs.forEach((x,i)=>{const y=ys[i];if(numeric(x)&&numeric(y))p.push([x,y]);});const n=p.length;
 if(n<3)return {status:"insufficient_samples",n,r:null};
 const scale=(a:number[])=>{const s=a.reduce((m,x)=>Math.max(m,Math.abs(x)),0);return s?a.map(x=>x/s):a;};
 const center=(a:number[])=>{const mean=a.reduce((s,x)=>s+x,0)/n;return a.map(x=>x-mean);};
 const a=center(scale(p.map(x=>x[0]))),b=center(scale(p.map(x=>x[1]))),aa=a.reduce((s,x)=>s+x*x,0),bb=b.reduce((s,x)=>s+x*x,0);
 if(!aa||!bb)return {status:"constant_column",n,r:null};
 return {status:"ok",n,r:Math.max(-1,Math.min(1,a.reduce((s,x,i)=>s+x*b[i],0)/Math.sqrt(aa*bb)))};
}
function isoDate(v:string){if(!/^\d{4}-\d{2}-\d{2}$/.test(v)||v.startsWith("0000"))return false;const d=new Date(v+"T00:00:00Z");return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===v;}
export function recommend(sql:string,rows:Row[]):Plan{
 if(typeof sql!=="string"||!sql.trim()||sql.length>20000)throw new TypeError("SQL must contain 1–20000 characters");
 if(!Array.isArray(rows)||rows.length<1||rows.length>5000||rows.some(r=>!r||typeof r!=="object"||Array.isArray(r)))throw new TypeError("Expected 1–5000 rows");
 const keys=Object.keys(rows[0]);if(!keys.length||keys.length>50||keys.some(k=>!k)||rows.some(r=>Object.keys(r).length!==keys.length||keys.some(k=>!Object.hasOwn(r,k)||!(r[k]===null||typeof r[k]==="string"||typeof r[k]==="boolean"||numeric(r[k])))))throw new TypeError("Rows must have identical scalar columns");
 const nums=keys.filter(k=>rows.every(r=>numeric(r[k]))),cats=keys.filter(k=>rows.every(r=>typeof r[k]==="string"&&r[k]!==""));
 let chartType:Plan["chartType"]="table",encodings:Plan["encodings"]={},reason="No supported safe chart for shape";
 if(rows.length===1&&keys.length===1&&nums.length===1){chartType="kpi";encodings={y:nums[0]};reason="One numeric scalar";}
 else if(keys.length===2&&nums.length===1&&cats.length===1&&rows.length<=100){const x=cats[0],y=nums[0],labels=rows.map(r=>r[x] as string);if(new Set(labels).size===labels.length){const temporal=labels.length>=4&&labels.every(isoDate)&&labels.every((v,i)=>i===0||v>labels[i-1]);chartType=temporal?"line":rows.length>12?"horizontal_bar":"bar";encodings={x,y};reason=temporal?"Ordered ISO dates":"Unique categories";}}
 return {contract_version:"preview-v0.1",mode:"deterministic-preview",chartType,encodings,reason,insights:Object.fromEntries(nums.map(k=>[k,madOutliers(rows.map(r=>r[k]))])),warnings:["No ONNX model; stacking and other metadata-dependent charts are not supported by this preview."]};
}
function parts(p:Plan,rows:Row[]){if(!["bar","horizontal_bar","line"].includes(p.chartType)||!p.encodings.x||!p.encodings.y)throw new TypeError("Unsupported adapter chart");const {x,y}=p.encodings;return {x,y,a:rows.map(r=>r[x]),b:rows.map(r=>r[y]),horizontal:p.chartType==="horizontal_bar",line:p.chartType==="line"};}
export function toEcharts(p:Plan,rows:Row[]){const {x,y,a,b,horizontal,line}=parts(p,rows),cat={type:"category",data:a,name:x},num={type:"value",name:y};return {xAxis:horizontal?num:cat,yAxis:horizontal?cat:num,series:[{type:line?"line":"bar",data:b}]};}
export function toRecharts(p:Plan,rows:Row[]){const {x,y,horizontal,line}=parts(p,rows);return {data:rows,chart:line?"LineChart":"BarChart",layout:horizontal?"vertical":"horizontal",categoryKey:x,valueKey:y};}
