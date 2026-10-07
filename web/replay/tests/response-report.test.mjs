import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,realpath,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {fixture} from './approach-fixture.mjs';
import {hash} from './evaluation-fixture.mjs';
import {responseReport} from '../../../tools/response_report.mjs';
test('report requires pinned identity and rejects corrupt data and overwriting output',async()=>{
  const root=await mkdtemp(path.join(tmpdir(),'aeroloop-response-'));
  try{
    const data=fixture(),bytes=JSON.stringify(data.index),digest=hash(bytes);
    await writeFile(path.join(root,'index.json'),bytes);
    await Promise.all(Object.entries(data.documents).map(([file,body])=>writeFile(path.join(root,file),body)));
    const report=await responseReport(root,digest);assert.equal(report.seeds.length,9);assert.equal(report.seeds.flatMap(s=>s.flights).length,36);assert.ok(report.seeds.every(s=>s.analysis.cells.every(c=>c.complete)));
    assert.ok(!JSON.stringify(report).includes(root));await assert.rejects(()=>responseReport(root,'0'.repeat(64)));
    const target=path.join(root,'review.json');await writeFile(target,'preserve');
    const cli=spawnSync(process.execPath,[fileURLToPath(new URL('../../../tools/response_report.mjs',import.meta.url)),'--bundle',root,'--index-sha256',digest,'--output',target],{encoding:'utf8'});assert.equal(cli.status,1);assert.match(cli.stderr,/existing output/);assert.equal(await readFile(target,'utf8'),'preserve');
    const file=data.index.cases[0].file;await writeFile(path.join(root,file),'{}');await assert.rejects(()=>responseReport(root,digest));
  }finally{assert.equal(path.dirname(await realpath(root)),await realpath(tmpdir()));assert.ok(path.basename(root).startsWith('aeroloop-response-'));await rm(root,{recursive:true,force:true});}
});
