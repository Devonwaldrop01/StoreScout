// Read-only replay of the endpoint's actual PostgreSQL predicates in local PGlite.
import { PGlite } from '../../outputs/phase1/sql-runtime/node_modules/@electric-sql/pglite/dist/index.js';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
const source='docs/quality-audit/real-world/evidence/';
const out='outputs/controlled-validation/';
const load=p=>JSON.parse(readFileSync(p,'utf8'));
const plans=load(source+'replay-plan.json');
const original=load(source+'index-snapshot.json');
const db=new PGlite();
await db.exec(`CREATE TABLE local_index (domain text PRIMARY KEY,status text,verification_confidence integer,
 category text,subcategory text,description text,brand_name text,last_verified_at timestamptz)`);
const variants={before:original};
if(existsSync(out+'index-after.json')) {
 variants.after=load(out+'index-after.json');
 const sample=new Set(load(source+'health-sample.json').map(r=>r.domain));
 const afterMap=new Map(variants.after.map(r=>[r.domain,r]));
 variants.sample_only=original.map(r=>sample.has(r.domain)?afterMap.get(r.domain):r);
 const successful=new Set(load(out+'outcomes.json').filter(r=>r.result.outcome==='verified').map(r=>r.domain));
 variants.successes_only=original.map(r=>successful.has(r.domain)?afterMap.get(r.domain):r);
}
for(const [variant,rows] of Object.entries(variants)) {
 await db.exec('TRUNCATE local_index');
 await db.query(`INSERT INTO local_index SELECT domain,status,verification_confidence,category,subcategory,description,brand_name,last_verified_at
 FROM jsonb_to_recordset($1::jsonb) AS x(domain text,status text,verification_confidence integer,category text,
 subcategory text,description text,brand_name text,last_verified_at timestamptz)`,[JSON.stringify(rows)]);
 const channels=[];
 for(const c of plans) for(const channel of ['category','lexical']) {
  const args=channel==='category'?[c.user_category]:c.terms.map(t=>'%'+t+'%');
  const clause=channel==='category'?'category=$1':c.terms.flatMap((t,i)=>['category','subcategory','description','brand_name'].map(col=>`${col} ILIKE $${i+1}`)).join(' OR ');
  const where=`status='verified' AND verification_confidence>=60 AND (${clause})`;
  const count=(await db.query(`SELECT count(*)::integer n FROM local_index WHERE ${where}`,args)).rows[0].n;
  const selected=(await db.query(`SELECT domain FROM local_index WHERE ${where} ORDER BY last_verified_at DESC LIMIT 200`,args)).rows.map(r=>r.domain);
  channels.push({case_id:c.id,channel,matched_count:count,domains:selected});
 }
 const path=out+variant+'/evidence/'; mkdirSync(path,{recursive:true});
 writeFileSync(path+'retrieval-postgres.json',JSON.stringify({channels},null,2));
 writeFileSync(path+'index-snapshot.json',JSON.stringify(rows));
 console.log(variant, rows.length, channels.length);
}
await db.close();
