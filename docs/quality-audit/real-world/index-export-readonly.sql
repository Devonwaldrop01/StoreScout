-- PREPARED, NOT EXECUTED. Public catalog metadata only; no customer/private tables.
-- Use an authenticated read-only session. Do not use this to grant permissions.
-- Execute schema inspection first. JSON projection tolerates absent optional columns,
-- but preserve this schema inventory so absent columns are not confused with nulls.
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'shopify_store_index'
ORDER BY ordinal_position;

SELECT now() AS observed_at, count(*) AS indexed_rows
FROM public.shopify_store_index;

-- Page one; subsequent pages use WHERE domain > :last_domain before ORDER BY.
-- Reconcile all page counts to the census. A transactionally consistent snapshot
-- is preferred; document consistency limits if the provider cannot preserve one.
-- No contacts, user IDs, API keys or arbitrary stored JSON blobs are exported.
SELECT jsonb_build_object(
  'domain', j->'domain', 'brand_name', j->'brand_name',
  'status', j->'status', 'category', j->'category',
  'subcategory', j->'subcategory', 'description', j->'description',
  'category_confidence', j->'category_confidence',
  'verification_confidence', j->'verification_confidence',
  'verification_signals', j->'verification_signals',
  'last_verified_at', j->'last_verified_at',
  'knowledge_at', j->'knowledge_at',
  'created_at', j->'created_at', 'updated_at', j->'updated_at',
  'product_titles', j->'product_titles', 'product_types', j->'product_types',
  'product_tags', j->'product_tags', 'collections', j->'collections',
  'product_count', j->'product_count', 'dna_keywords', j->'dna_keywords',
  'target_customer', j->'target_customer', 'pricing_tier', j->'pricing_tier',
  'business_stage', j->'business_stage',
  'median_price', j->'median_price', 'currency', j->'currency',
  'source', j->'source',
  'store_dna', jsonb_build_object('keywords', j->'store_dna'->'keywords',
                                  'summary', j->'store_dna'->'summary')
) AS public_index_record
FROM (SELECT domain, to_jsonb(i) AS j FROM public.shopify_store_index i) q
ORDER BY domain LIMIT 1000;

-- This export is enough for description-only ranking fields, not full provider
-- diagnostics/history. Do not invent unknown column mappings; match schema first.
