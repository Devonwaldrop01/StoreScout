// Local PostgreSQL (PGlite) validation; never opens a network database.
// npm install --prefix outputs/phase1/sql-runtime --save-exact @electric-sql/pglite@0.5.8
import { PGlite } from '../outputs/phase1/sql-runtime/node_modules/@electric-sql/pglite/dist/index.js';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const db = new PGlite();
await db.exec(readFileSync('supabase/migrations/007_shopify_store_index.sql','utf8'));
await db.exec(`ALTER TABLE shopify_store_index DROP CONSTRAINT shopify_store_index_status_check;
ALTER TABLE shopify_store_index ADD CONSTRAINT shopify_store_index_status_check CHECK(status IN ('discovered','candidate','verified','failed','rejected'));`);
await db.exec(readFileSync('supabase/migrations/20260905235144_verification_lifecycle.sql','utf8'));
const snapshot = JSON.parse(readFileSync('docs/quality-audit/real-world/evidence/index-snapshot.json','utf8'));
await db.query(`INSERT INTO shopify_store_index (domain,status,created_at,updated_at,last_verified_at)
SELECT domain,status,created_at,updated_at,last_verified_at FROM jsonb_to_recordset($1::jsonb)
AS x(domain text,status text,created_at timestamptz,updated_at timestamptz,last_verified_at timestamptz)`, [JSON.stringify(snapshot)]);
const clock='2026-09-05T20:44:23.705755+00:00';
const due = await db.query(`SELECT domain FROM shopify_store_index WHERE status='verified'
AND next_verification_at IS NULL AND last_verified_at <= $1::timestamptz - interval '53 days'`,[clock]);
assert.equal(due.rows.length,320);
const domain=due.rows[0].domain;
const original=(await db.query('SELECT updated_at::text FROM shopify_store_index WHERE domain=$1',[domain])).rows[0].updated_at;
const token='00000000-0000-4000-8000-000000000001';
const token2='00000000-0000-4000-8000-000000000002';
const claim=`UPDATE shopify_store_index SET verification_token=$1, updated_at=$2,
next_verification_at=$2::timestamptz + interval '5 minutes' WHERE domain=$3 AND updated_at=$4 RETURNING domain`;
assert.equal((await db.query(claim,[token,clock,domain,original])).rows.length,1);
assert.equal((await db.query(claim,[token2,clock,domain,original])).rows.length,0);
assert.equal((await db.query(`UPDATE shopify_store_index SET status='failed' WHERE domain=$1 AND verification_token=$2 RETURNING domain`,[domain,token2])).rows.length,0);
const rls=await db.query(`SELECT relrowsecurity FROM pg_class WHERE oid='shopify_store_index'::regclass`);
assert.equal(rls.rows[0].relrowsecurity,true);
await db.exec('ANALYZE shopify_store_index');
const plan=await db.query(`EXPLAIN SELECT domain FROM shopify_store_index WHERE status IN ('verified')
AND (next_verification_at <= $1::timestamptz OR (next_verification_at IS NULL AND last_verified_at <= $1::timestamptz - interval '53 days')
OR (next_verification_at IS NULL AND last_verified_at IS NULL))
ORDER BY next_verification_at NULLS FIRST,created_at,domain LIMIT 100`,[clock]);
console.log(JSON.stringify({rows:snapshot.length,renewal_due:due.rows.length,claim_cas:'passed',stale_completion:'passed',rls:'preserved',plan:plan.rows},null,2));
// The deployed old writer remains structurally compatible after this additive migration.
await db.query(`INSERT INTO shopify_store_index(domain,status) VALUES('legacy-writer.test','candidate')`);
const firstSeed = await db.query(`INSERT INTO shopify_store_index(domain,status,verification_token,next_verification_at)
VALUES('concurrent-seed.test','candidate',$1,$2::timestamptz+interval '5 minutes')
ON CONFLICT(domain) DO NOTHING RETURNING domain`,[token,clock]);
const secondSeed = await db.query(`INSERT INTO shopify_store_index(domain,status)
VALUES('concurrent-seed.test','discovered') ON CONFLICT(domain) DO NOTHING RETURNING domain`);
assert.equal(firstSeed.rows.length,1);
assert.equal(secondSeed.rows.length,0);
assert.equal((await db.query(`SELECT verification_token FROM shopify_store_index WHERE domain='concurrent-seed.test'`)).rows[0].verification_token,token);
assert.equal((await db.query(`UPDATE shopify_store_index SET status='failed'
WHERE domain='concurrent-seed.test' AND verification_token IS NULL RETURNING domain`)).rows.length,0);
assert.equal((await db.query(`UPDATE shopify_store_index SET status='verified'
WHERE domain='concurrent-seed.test' AND verification_token=$1
AND next_verification_at > $2::timestamptz + interval '6 minutes' RETURNING domain`,[token,clock])).rows.length,0);
console.log(JSON.stringify({atomic_conflicting_seed:'passed',claim_preservation:'passed',expired_completion:'refused',legacy_insert_after_migration:'passed'}));
await db.close();
