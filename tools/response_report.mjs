#!/usr/bin/env node
// Reconstruct a bounded report from an explicitly pinned approach export.
import {readFile,lstat,realpath,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {validateApproachIndex,validateApproach} from '../web/replay/dist/approach-contract.js';
import {GROUPS,METHOD,quartet,analyze,validateWindow} from '../web/replay/dist/response-analysis.js';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
export async function responseReport(bundle,digest,window={start:40,end:43}){
  validateWindow(window);if(!/^[a-f0-9]{64}$/.test(digest))throw Error('Invalid digest');
  if((await lstat(bundle)).isSymbolicLink())throw Error('Linked bundle');
  const root=await realpath(bundle);
  async function bounded(file,hash,limit){
    const target=path.join(root,file),stat=await lstat(target);
    if(!stat.isFile()||stat.isSymbolicLink()||stat.size>limit||path.dirname(await realpath(target))!==root)throw Error('Invalid evidence file');
    const bytes=await readFile(target);if(bytes.length>limit||sha(bytes)!==hash)throw Error('Evidence checksum mismatch');
    return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  }
  const entries=validateApproachIndex(await bounded('index.json',digest,16384)),seeds=[];
  for(const g of GROUPS){
    const es=[0,1].map(p=>entries.find(e=>e.id===`${g.cohort}-p${p}-s${g.seed}`));
    const values=[];for(const e of es)values.push(validateApproach(await bounded(e.file,e.sha256,12*1024*1024),e));
    const q=quartet(values[0],values[1],es);
    seeds.push({...g,entries:es,analysis:analyze(q,window),flights:q.flights.map((f,i)=>({cell:['fixed-intact','fixed-outage','scheduled-intact','scheduled-outage'][i],status:f.status,failure_reason:f.failure_reason,gates:f.gates,outage:f.outage,provenance:f.provenance}))});
  }
  return {schema_version:1,kind:'landing_response_report',index_sha256:digest,method:METHOD,window,seeds};
}
async function main(){
  const args=process.argv.slice(2),options={};
  for(let i=0;i<args.length;i+=2){if(!['--bundle','--index-sha256','--output','--start','--end'].includes(args[i])||args[i] in options||!args[i+1])throw Error();options[args[i]]=args[i+1];}
  if(!options['--bundle']||!options['--output'])throw Error();
  const result=await responseReport(options['--bundle'],options['--index-sha256'],{start:Number(options['--start']??40),end:Number(options['--end']??43)});
  await writeFile(options['--output'],JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({seeds:result.seeds.length,flights:36,complete_windows:result.seeds.flatMap(s=>s.analysis.cells).filter(s=>s.complete).length}));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)main().catch(()=>{console.error('Response report rejected: invalid arguments, evidence, or existing output.');process.exitCode=1;});
