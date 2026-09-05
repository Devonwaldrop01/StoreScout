-- Prepared only: not executed against production. Requires applied index migrations.
-- No mutations. "verified" is pipeline status, NOT an independently audited active-store rate.
SELECT count(*) AS indexed_domains,
 count(*) FILTER (WHERE status='verified') AS pipeline_verified,
 count(*) FILTER (WHERE status='verified' AND last_verified_at >= now()-interval '60 days') AS recently_verified,
 count(*) FILTER (WHERE status='verified' AND (last_verified_at IS NULL OR last_verified_at < now()-interval '60 days')) AS stale_verified,
 count(*) FILTER (WHERE status='verified' AND category IS NOT NULL AND category <> 'Other' AND category_confidence>=55) AS classified,
 count(*) FILTER (WHERE status='verified' AND cardinality(product_titles)>0) AS titles_present,
 count(*) FILTER (WHERE status='verified' AND cardinality(dna_keywords)>0) AS dna_present
FROM public.shopify_store_index;

SELECT status, category, count(*) AS rows,
 min(last_verified_at) AS oldest_verification, max(last_verified_at) AS newest_verification,
 avg(cardinality(product_titles)) AS mean_sampled_titles
FROM public.shopify_store_index GROUP BY status, category ORDER BY rows DESC;

-- Domain normalization candidates only. Same-brand domains require canonical/redirect evidence.
SELECT regexp_replace(lower(domain),'^www[.]','') AS normalized_domain, count(*) AS rows
FROM public.shopify_store_index GROUP BY 1 HAVING count(*)>1;
SELECT brand_name, count(*) AS domains
FROM public.shopify_store_index WHERE status='verified' AND brand_name IS NOT NULL
GROUP BY brand_name HAVING count(*)>1 ORDER BY domains DESC LIMIT 50;

SELECT status, count(*) AS refs, max(attempts) AS maximum_attempts
FROM public.discovery_queue GROUP BY status;

-- Reproducible stratified candidates for a later permitted HTTP/independent label review.
WITH ranked AS (
 SELECT domain, category, last_verified_at, verification_confidence, category_confidence,
 product_types, product_titles,
 row_number() OVER (PARTITION BY category ORDER BY md5(domain)) AS sample_rank
 FROM public.shopify_store_index WHERE status='verified'
)
SELECT * FROM ranked WHERE sample_rank<=5 ORDER BY category, sample_rank;
