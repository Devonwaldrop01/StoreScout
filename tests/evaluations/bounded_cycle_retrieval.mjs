import { PGlite } from '../../outputs/phase1/sql-runtime/node_modules/@electric-sql/pglite/dist/index.js';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import assert from 'node:assert/strict';
const load=p=>JSON.parse(readFileSync(p,'utf8'));
const source='docs/quality-audit/real-world/evidence/',out='outputs/bounded-cycle/';
const plans=load(source+'replay-plan.json');
const db=new PGlite();
await db.exec(`CREATE TABLE local_index(domain text,status text,verification_confidence integer,
category text,subcategory text,description text,brand_name text,last_verified_at timestamptz,dna_keywords jsonb)`);
// Real PostgreSQL regression: singleton JSONB containment has any-keyword
// semantics, excludes null, and handles punctuation without a type conversion.
assert.equal((await db.query(`SELECT ('["keyboard","low-profile"]'::jsonb @> '["keyboard"]'::jsonb OR
 '["keyboard","low-profile"]'::jsonb @> '["coffee"]'::jsonb) AS ok`)).rows[0].ok,true);
for (const [variant,input] of Object.entries({frozen:source+'index-snapshot.json',controlled:out+'index-after.json'})) {
 const rows=load(input); await db.exec('TRUNCATE local_index');
 await db.query(`INSERT INTO local_index SELECT domain,status,verification_confidence,category,subcategory,description,brand_name,last_verified_at,dna_keywords
 FROM jsonb_to_recordset($1::jsonb) AS x(domain text,status text,verification_confidence integer,category text,subcategory text,description text,brand_name text,last_verified_at timestamptz,dna_keywords jsonb)`,[JSON.stringify(rows)]);
 const channels=[];
 for(const c of plans) for(const channel of ['category','lexical','dna']) {
  const args=channel==='category'?[c.user_category]:c.terms.map(t=>channel==='dna'?JSON.stringify([t]):'%'+t+'%');
  const clause=channel==='category'?'category=$1':channel==='dna'?c.terms.map((t,i)=>`dna_keywords @> $${i+1}::jsonb`).join(' OR '):c.terms.flatMap((t,i)=>['category','subcategory','description','brand_name'].map(col=>`${col} ILIKE $${i+1}`)).join(' OR ');
  const where=`status='verified' ${channel==='dna'?'':'AND verification_confidence>=60'} AND (${clause})`;
  const count=(await db.query(`SELECT count(*)::integer n FROM local_index WHERE ${where}`,args)).rows[0].n;
  const selected=(await db.query(`SELECT domain FROM local_index WHERE ${where} ORDER BY last_verified_at DESC LIMIT 200`,args)).rows.map(r=>r.domain);
  channels.push({case_id:c.id,channel,matched_count:count,domains:selected});
 }
 const p=out+variant+'/evidence/';mkdirSync(p,{recursive:true});
 writeFileSync(p+'index-snapshot.json',JSON.stringify(rows));
 writeFileSync(p+'retrieval-postgres.json',JSON.stringify({channels},null,2));
 console.log(variant,channels.length,'SQL channels');
}
await db.close();
