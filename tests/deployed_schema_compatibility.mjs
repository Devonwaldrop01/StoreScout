// Offline reconstruction of the read-only production schema metadata.
import { PGlite } from '../outputs/phase1/sql-runtime/node_modules/@electric-sql/pglite/dist/index.js';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const schema=JSON.parse(readFileSync('docs/quality-audit/phase1/deployment-preflight/schema-readonly.json','utf8'));
const db=new PGlite();
const types=new Set(['uuid','text','integer','numeric','jsonb','timestamp with time zone','boolean']);
const defaults=new Set(['gen_random_uuid()','now()',"'candidate'::text",'false']);
const columns=schema.columns.map(c=>{
  assert.match(c.name,/^[a-z_]+$/);assert.ok(types.has(c.type));
  if(c.default!==null)assert.ok(defaults.has(c.default));
  return `${c.name} ${c.type}${c.nullable==='NO'?' NOT NULL':''}${c.default!==null?' DEFAULT '+c.default:''}`;
});
await db.exec(`CREATE TABLE public.shopify_store_index (${columns.join(',')},PRIMARY KEY(id),UNIQUE(domain),
CHECK(status IN ('discovered','candidate','verified','rejected','failed')));
ALTER TABLE public.shopify_store_index ENABLE ROW LEVEL SECURITY;`);
const migration=readFileSync('supabase/migrations/20260905235144_verification_lifecycle.sql','utf8');
await db.exec(migration);
const manifest=JSON.parse(readFileSync('config/verification-canary.json','utf8'));
for(const e of manifest.stores){
 await db.query('INSERT INTO shopify_store_index(domain,status,updated_at) VALUES($1,$2,$3)',[e.domain,e.sample_status,e.expected_updated_at]);
}
const e=manifest.stores[0], token='00000000-0000-4000-8000-000000000011';
const claim=`UPDATE shopify_store_index SET verification_token=$1,updated_at=now(),next_verification_at=now()+interval '5 minutes'
WHERE domain=$2 AND updated_at=$3::timestamptz AND verification_token IS NULL RETURNING domain`;
assert.equal((await db.query(claim,[token,e.domain,e.expected_updated_at])).rows.length,1);
assert.equal((await db.query(claim,[token,e.domain,e.expected_updated_at])).rows.length,0);
await db.query('UPDATE shopify_store_index SET verification_token=NULL WHERE domain=$1',[e.domain]);
assert.equal((await db.query(claim,[token,e.domain,e.expected_updated_at])).rows.length,0);
assert.equal((await db.query('SELECT count(*)::int AS n FROM shopify_store_index')).rows[0].n,12);
assert.equal((await db.query("SELECT relrowsecurity FROM pg_class WHERE oid='shopify_store_index'::regclass")).rows[0].relrowsecurity,true);
console.log(JSON.stringify({deployed_columns:schema.columns.length,migration:'passed',manifest_rows:12,one_shot_row_precondition:'passed',row_count_preserved:true,rls_preserved:true}));
await db.close();
