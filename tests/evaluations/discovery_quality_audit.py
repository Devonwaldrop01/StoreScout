"""Audit saved pilot evidence only. No service access or classifier reruns."""
import collections,csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'outputs/index-v2-pilot-100/benchmark'
OUT=ROOT/'docs/quality-audit/discovery-quality'
OUT.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf8'))
rows=load(SOURCE/'v2.json')
# Independent catalog-level judgments, not eligibility decisions or merchant blocklists.
# supported = primary category/subcategory plausible, not exact demographic/price proof.
review_text="""
1036emporium.com|supported|Vintage/designer sportswear resale and rental|Outerwear/apparel and archive resale are explicit.
74manstore.com|subcategory_mismatch|Menswear and gifts|Womenswear contradicts explicit men's mercantile and Western shirts.
amorcustomgifts.com|supported|Personalized graphic gift bedding|Quilts/duvet covers support Bedding; personalization and materials are not encoded.
andyfrisella.com|mixed_or_overbroad|Personal-development merchandise/books/coaching|Tees are real, but Fashion omits the creator-merchandise business model.
aprasi.com|mixed_or_overbroad|Fandom collectibles/plush and apparel|Toys exists; Kids & Baby implies an audience not established by anime/gaming collectibles.
arlingtontx.clothesmentor.com|supported|Secondhand adult designer apparel/accessories|Womenswear supported; resale model explicit only in description.
artonwheels.co|supported|Streetwear/apparel|Hoodies/shorts/tees support Fashion. Baby tee is a garment name, not infant evidence.
aubongoutboutique.com|supported|French home/tableware/gift retailer|Home Decor broadly supported; mixed food/skincare gifts must not define all products.
australian-native.com.au|supported|Australian souvenir apparel|Fashion supported; souvenir/printed-theme positioning not explicit in structured fields.
butteriedish.com|supported|Butter dishes and kitchen utensils|Kitchen supported by consistent dishes/spreaders.
claymoreshop.com|subcategory_mismatch|Tailored apparel/knitwear and footwear|Womenswear not supported by captured tailored menswear-style assortment; gender should stay unknown without explicit evidence.
cougarpaws.com|mixed_or_overbroad|Professional roofing footwear|Footwear supported, Fashion omits explicit professional roofing use.
dc2miami.com|subcategory_mismatch|Men's swimwear and athleisure|Womenswear directly contradicts explicit men's swimwear description.
designerrevival.com|supported|Designer bags/accessories assortment|Captured handbags dominate; resale status not inferred from names alone.
electricpedalpower.com.au|mixed_or_overbroad|E-bike/scooter kits and components|Parts supported; Automotive is too broad to establish car-parts competitors.
fragranceofarabia.com|supported|Perfume oils/sprays and incense|Fragrance supported.
headingprints.com|supported|Printed scarves/bandanas|Scarves supported; literary artwork is not the underlying product type.
highspeedgear.com|mixed_or_overbroad|Tactical equipment with K9 accessories|Pet accessories exist but majority captured titles are holsters/pouches/duty equipment.
jmrhousetohome.ie|mixed_or_overbroad|Tiles/building supplies and home gifts|Home category broad; captured titles dominated by tiles, detached Bedding type not representative evidence.
kbeauty.us|supported|Korean skincare retailer|Skincare supported; tinted makeup substitution not established by broad Beauty classification.
keeprtuned.com|supported|Vehicle replacement parts|Automotive Parts supported by explicit vehicle-component titles.
kpopnw.com|primary_mismatch|K-pop music albums and collectibles|Kids Apparel conflicts with albums/lightsticks/photocards; artist names containing Kids are not an audience.
leahmaria.dk|supported|Designer apparel/jewelry/accessories|Fashion broadly supported; affordability and audience not proven by generated labels.
macromike.com.au|supported|Protein supplements and sports nutrition|Sports Nutrition supported.
madcapcoffee.com|supported|Specialty coffee roaster/subscriptions|Coffee and subscriptions explicitly supported.
meadow-nest.com|primary_mismatch|Poultry supplies, cosmetic bags and decor|Beauty/Cosmetics misreads storage bags; captured poultry products and bag accessories are not makeup.
megafootystore.com.au|subcategory_mismatch|Sports fan apparel/merchandise|Womenswear overstates mixed men's/youth/team products.
memery.eu|supported|Vintage-style footwear|Footwear supported; Boots narrower than total range but real captured boots.
merino.tech|mixed_or_overbroad|Merino performance apparel for adults and children|Kids Apparel exists but adult thermal sets/shirts dominate captured titles.
pintrill.com|mixed_or_overbroad|Collectible pins/keychains/charms|Phone accessories exist; primary Tech/Phone Cases masks collectible-accessory composition.
profilefashion.com|supported|Multi-brand designer apparel|Fashion supported; Womenswear is one segment, not an exclusive audience claim.
riverbendfairhope.com|subcategory_mismatch|Men's and boys' apparel retailer|Womenswear contradicts explicit Men and Boys description.
shopcasinoquest.com|mixed_or_overbroad|Casino-game equipment and merchandise|Apparel exists, but gaming tools/chips/sliders dominate sample.
shoppandcboutique.com|supported|Women's fashion boutique|Dresses/tops/accessories support category.
shopworthandgray.com|supported|Women's fashion/accessories boutique|Explicit description supports category; proprietary titles limit product-type extraction.
shoutandabout.com|mixed_or_overbroad|Gift/stationery boutique with kids clothing|Streetwear is one segment; Lotion and baby gifts do not imply baby lotion.
stagecoachgifts.biz|supported|Artisan turquoise jewelry|Jewelry supported; Fashion Jewelry blurs fine/artisan positioning.
suncoastaudiodirect.com|supported|Audio equipment/cables/connectors|Audio category supported.
supernovacalzature.com|supported|Footwear and accessories retailer|Sneakers strongly supported; non-English product-type variants present.
thatsreallycrafty.com|supported|Craft supplies and tools|Craft Supplies supported.
theclosetinc.com|subcategory_mismatch|Sports/lifestyle footwear and apparel|Womenswear fails to summarize men's footwear/team apparel in captured sample.
thekimyoung.com|supported|Korean skincare/beauty retailer|Skincare strongly supported; sampled sun care not sufficient to assert tint/color.
thesocialdawg.com|mixed_or_overbroad|Dog bakery treats, bandanas and toys|Pet Accessories real, but treats are a major captured segment; freeze-dried/raw not established.
thewindopal.com|subcategory_mismatch|Fine opal/diamond jewelry|Fashion Jewelry understates explicit 14K-gold/diamond gemstone product evidence.
thezerano.com|supported|Discount multi-brand adult fashion|Fashion supported; mixed men/women and price claims should be retained as evidence rather than assumed equivalence.
tuttifruttikidsco.com|subcategory_mismatch|Baby/toddler clothing with matching mom pieces|Womenswear misrepresents predominantly baby/toddler catalog.
uk.sunnylife.com|mixed_or_overbroad|Pool/beach leisure goods and children's swim gear|Kids Apparel exists but pool floats/leisure goods dominate; no basis to treat all goods as apparel.
us.thesomewhereco.com|primary_mismatch|Reusable bags, lunch containers and picnic goods|Food/Snacks is product-container confusion; lunch bags/snack boxes are not edible food.
vie-riche.com|supported|Streetwear brand|Streetwear supported by hoodies/joggers/tees.
welcometowondervalley.com|supported|Olive-oil skincare and home goods|Skincare supported, mixed olive oil/home merchandise must remain visible.
wilkinsandolander.com|supported|Apparel/accessory/gift retailer|Fashion supported; sample spans multiple audiences.
woodtonestrings.com|mixed_or_overbroad|Musical strings/picks with branded merchandise|Tees real but guitar strings/picks dominate; Fashion confidence is not primary-business proof.
wragal.com|mixed_or_overbroad|Mixed apparel/footwear/general merchandise|Fashion exists; shoes, jerseys and industrial shackle demonstrate heterogeneous sample.
zerowastecartel.com|supported|Low-waste haircare and home accessories|Haircare supported by shampoo/conditioner; home assortment is a separate segment.
"""
reviews={}
for line in review_text.strip().splitlines():
 domain,status,niche,note=line.split('|')
 reviews[domain]=(status,niche,note)
assert set(reviews)=={r['domain'] for r in rows} and len(rows)==54
audits=[]
for r in rows:
 status,niche,note=reviews[r['domain']]
 audits.append({'domain':r['domain'],'review_status':status,'observed_niche':niche,'rationale':note,
 'eligible_for_some_query':True,'exclude_globally':False,
 'metadata':{k:r.get(k) for k in ['category','category_confidence','subcategory','target_customer','pricing_tier','description','business_stage','store_dna','category_evidence','catalog_observation','product_types','product_titles']},
 'limits':'Observed sample, not a complete catalog census. Target/price labels are inferred. No business-model/age/material assertions fabricated.'})
(OUT/'eligible-store-audit.json').write_text(json.dumps(audits,indent=2),encoding='utf8')
labels={(r['case_id'],r['mode'],r['domain']):r for r in load(SOURCE/'new-judgments.json')}
placements=[]
for variant in ['v2','combined']:
 for c in load(SOURCE/variant/'evidence/replay-results.json'):
  for rank,domain in enumerate(c['returned_domains'],1):
   if domain not in reviews:continue
   l=labels[c['case_id'],c['mode'],domain]
   trace=next(t for t in c['ranked'] if t['domain']==domain)
   if l['label']>=2: cause='useful_supported_match'
   elif domain in ['kbeauty.us','thekimyoung.com']:cause='beauty_subtype_confusion'
   elif domain=='meadow-nest.com':cause='accessory_or_product_text_collision'
   elif domain=='shoutandabout.com':cause='cross_product_demographic_join'
   elif domain=='jmrhousetohome.ie':cause='detached_type_vs_catalog_composition'
   elif domain=='thesocialdawg.com':cause='preparation_use_case_mismatch'
   elif domain=='tuttifruttikidsco.com':cause='audience_and_subcategory_mismatch'
   elif domain in ['stagecoachgifts.biz','leahmaria.dk','1036emporium.com']:cause='price_or_business_model_mismatch'
   else:cause='legitimate_adjacent_low_business_fit'
   placements.append({'variant':variant,'case_id':c['case_id'],'mode':c['mode'],'domain':domain,'rank':rank,
     'label':l['label'],'primary_cause':cause,'judgment':l['rationale'],
     'retrieval_channels':[t['channel'] for t in c['retrieval'] if domain in t.get('domains',[])],
     'query':c['query'],'context':c['user_match_ctx'],'match':trace['match'],
     'classification_review':reviews[domain][0],
     'cross_cutting':'Category/DNA/lexical retrieval unions candidates; unchanged score rewards token overlap, then permissive family gate admits result. High category confidence is not query relevance.'})
(OUT/'placement-audit.json').write_text(json.dumps(placements,indent=2),encoding='utf8')
unique={(r['case_id'],r['mode'],r['domain']):r for r in placements}
summary={'store_reviews':dict(collections.Counter(r['review_status'] for r in audits)),
 'eligible_stores':54,'globally_disqualified':0,
 'distinct_returned_v2_domains':len({r['domain'] for r in placements}),
 'unique_case_mode_domain_pairs':len(unique),'total_placements_across_two_variants':len(placements),
 'unique_primary_causes':dict(collections.Counter(r['primary_cause'] for r in unique.values())),
 'by_variant':{v:dict(collections.Counter(r['primary_cause'] for r in placements if r['variant']==v)) for v in ['v2','combined']},
 'by_mode':{m:dict(collections.Counter(r['primary_cause'] for r in unique.values() if r['mode']==m)) for m in ['description_only','structured_profile']},
 'metadata_missing':{k:sum(not r.get(k) for r in rows) for k in ['description','product_types','product_titles','target_customer','pricing_tier','business_model']},
 'input_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE/'v2.json',SOURCE/'combined.json',SOURCE/'legacy.json',SOURCE/'clock.json',SOURCE.parent/'pilot-results-20260922.sqlite']},
 'method':'Single-analyst public-evidence review; root causes are mutually exclusive primary explanations, secondary classification/score contributions retained per placement.'}
(OUT/'diagnosis-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps(summary,indent=2))

