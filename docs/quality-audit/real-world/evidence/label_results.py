"""Analyst adjudication of actual returned domains. Labels do not alter frozen references.
Scores 3/2/1/0/None follow the previously saved protocol; domain review uses current
public observations and independently retrieved official product pages.
"""
import json,pathlib,collections
P=pathlib.Path('evidence'); runs=json.loads((P/'replay-results.json').read_text())
annotations={}
def add(niche,label,domains,reason):
 for domain in domains.split():annotations[(niche,domain)]={'label':label,'rationale':reason}
add('ultralight',1,'xopoutdoors.com','Hunting treestands and hunting packs; hiking shelter and long-distance pack comparability not established.')
add('ultralight',1,'nomatic.com jamesleather.com knomo.com','Travel, camera or leather/laptop bags; adjacent carrying function without supported ultralight trail-pack fit.')
add('ultralight',0,'roboskillz.com blueingreensoho.com funwaterboard.com hydrusboardtech.com wildkin.com trpcycling.com benchmarkabrasives.com','Observed trading cards, denim, paddleboards, children school goods, cycling components or industrial abrasives do not satisfy the hiking-pack/shelter query.')
add('ultralight',2,'scouttech.com','Outdoor retailer with tents and hiking backpacks; useful partial assortment comparison, Canadian retail positioning and product weights need review.')
add('ultralight',1,'otsurplus.com','Military surplus packs and shelters are adjacent; heavy/surplus equipment is not established as a lightweight long-distance substitute.')
add('ultralight',1,'beachinsurf.com.au bagsandshoes.net broadrivermercantile.com rumpl.com','Adjacent surf/hunting/footwear/camping-blanket assortment, without verified lightweight shelter or backpack substitution for this query.')
add('tinted_complexion',3,'tower28beauty.com','Independent official evidence supports tinted SPF and complexion makeup; price equivalence is not assumed.')
add('tinted_complexion',2,'peachandlily.com','Official Sun Cover mineral tinted SPF overlaps complexion/suncare; full makeup portfolio or price parity is not assumed.')
add('tinted_complexion',2,'gracebeautybox.co.uk','Official retailer pages list tinted face SPF and CC cream; useful partial product comparison, retailer/UK positioning differs and mineral-only formulation is not established.')
add('tinted_complexion',2,'redaspenlove.com besamecosmetics.com','Observed face/lip makeup assortment overlaps part of the query; SPF, formulation, full portfolio and price comparability require review.')
add('tinted_complexion',1,'sahajan.com','Adult facial skincare is adjacent; no evidenced tint or color-makeup substitute for this request.')
add('tinted_complexion',2,'dlacosmetics.com','Lip cosmetics supply a limited overlap with everyday makeup; does not cover the tinted-SPF/eye-palette intent.')
add('tinted_complexion',1,'toppestanas.com queensupplies.com','Professional lash or nail supplies are adjacent beauty products, not evidenced complexion substitutes.')
add('tinted_complexion',0,'tintstuff.myshopify.com kallureskloset.com hydrusboardtech.com roboskillz.com perfumetogo.com safetygloves.com cart.wearewild.com','Window tint, fashion bags, paddleboards, trading cards, perfume, PPE or deodorant fail the requested complexion/color-makeup use case.')
add('baby_skin',1,'gracebeautybox.co.uk medicalsupplysurplus.com sahajan.com peachandlily.com dlacosmetics.com tower28beauty.com','Human skincare/medical-care adjacency, but the observed evidence does not establish fragrance-free infant lotion/ointment suitability; no medical equivalence inferred.')
add('baby_skin',1,'pureborn.com','Current official storefront sells diapers and calendula-lotion wipes; adjacent baby cleansing, not evidence of a fragrance-free infant lotion/ointment substitute.')
add('baby_skin',0,'apolina-kids.com hibobbie.com primary.com boppy.com pehr.com petunia.com perfumetogo.com chiquel.com toppestanas.com queensupplies.com cart.wearewild.com','Observed apparel, infant formula, pillows, bags, perfume, wigs, salon supplies or adult deodorant do not perform the stated infant-lotion/ointment function.')
add('specialty_coffee',3,'volcanicacoffee.com','Official specialty roasted coffee and subscription offerings directly match; no same-price assertion.')
add('specialty_coffee',2,'madeinnewmexico.com','Regional retailer carries packaged coffee alongside a broad New Mexico food/gift range; useful coffee-assortment comparison, not equivalent roaster/subscription positioning.')
add('specialty_coffee',1,'corkcicle.com ztshpt-cs.myshopify.com tasteofbritain.com','Drinkware/kitchenware or broad imported groceries are adjacent; no demonstrated specialty-roasted-bean/subscription substitute.')
add('specialty_coffee',0,'butchershopdirect.com heatonist.com inspiredgo.ca nutspick.co.uk sourdrops.net cheesebros.com','Observed meat, hot sauce, prepared salads, nuts, candy or cheese; roast/subscription/food wording is not coffee-product overlap.')
add('bamboo_family_sleepwear',None,'babymel.com','Current domain checks return 502; historical MORI description alone cannot independently establish the current redirected business or catalog.')
add('bamboo_family_sleepwear',2,'primary.com pehr.com','Official baby pajamas/sleepwear (and Pehr sleep bags) overlap the sleep use case; cotton/modal differs from bamboo and adult matching is not established.')
add('bamboo_family_sleepwear',1,'wildkin.com apolina-kids.com shop.marigoldmodern.com riotsociety.com 4lmercantile.com de.silksilky.com','Adjacent kids bedding/daywear or adult silk sleepwear, without evidenced bamboo infant/family sleepwear substitution.')
add('bamboo_family_sleepwear',0,'petunia.com hibobbie.com pureborn.com accessprive.com ryderwear.com vessi.com cave-london.com ctc-performance.co.uk asiyathecollection.com hansonstreetwear.com baukjen.com fightjunkiefootwear.com miamiheatstore.com blessviva.com mukama.com','Observed diaper bags/formula/diapers, adult apparel/footwear, car parts, merchandise, pet food or everyday-carry goods fail the stated children bamboo sleepwear use case.')
add('dog_freeze_dried_treats',2,'fetchyourpetneeds.ie petland.ca','Official stores offer freeze-dried/raw dog treats; useful retailer assortment comparison, but geography and reseller-versus-brand positioning differ. A reseller of the query brand is not a newly discovered competing manufacturer.')
add('dog_freeze_dried_treats',2,'redbarn.com','Official single-meat air-dried training treats overlap rewarding/training use; process differs from freeze-dried raw and ingredient equivalence is not assumed.')
add('dog_freeze_dried_treats',1,'wildone.com muttluks.com ruffwear.com freezbone.com','Dog gear, paw-care or refillable enrichment products are adjacent; no evidenced freeze-dried edible dog-treat substitution.')
add('dog_freeze_dried_treats',0,'kensfish.com dear-paw.com','Aquarium supplies or cat toys contradict species/product use.')
add('mechanical_keyboards',1,'bestampcovers.com shop.urbanarmorgear.com cashzone.com.au','Instrument/equipment covers, keyboard/device cases or broad secondhand electronics are adjacent; no evidenced comparable mechanical keyboard model.')
add('mechanical_keyboards',0,'hydrusboardtech.com warsawwireless.com mil-time.com bemodestboutique.com goodvibesbysabrina.com spartanburgsc.clothesmentor.com lukes.store vintagerecordstore.com','Observed paddleboards, phone accessories, watches, apparel, sexual-wellness goods or records do not satisfy mechanical-keyboard intent.')
add('bedding_and_broad_store',None,'rest-ment.com','Bedding navigation persists but the sampled current catalog is dominated by jewelry/storage products and the homepage contains template copy. Actual comparable bedding could not be confidently established from this bounded observation.')
add('bedding_and_broad_store',3,'madisonpark2010.com','Official bedding/sheet/comforter assortment overlaps the bedding use case; no sales or price equivalence claimed.')
add('bedding_and_broad_store',2,'wildkin.com','Children twin/full bedding supplies partial sheet/comforter overlap; audience, designs and material differ.')
add('bedding_and_broad_store',1,'babyletto.com lastaristocrat.com','Nursery-size bedding/furniture or broader home decor is adjacent; standard-size linen sheet/bath overlap is not established.')
add('bedding_and_broad_store',0,'smile-cleanworks.com vintagerecordstore.com signtextile.com blueingreensoho.com redaspenlove.com','Current hobby supplies, vinyl records, printed signage, denim or cosmetics do not satisfy the bedding/bath-linen query.')
add('bedding_and_broad_store',2,'petunia.com shopleatherworld.com kallureskloset.com robertsonmadison.com ryderwear.com asiyathecollection.com uk.ridge.com herschel.com','For Quince only: limited bag/accessory/apparel segment overlap. This does not represent its whole broad business or establish equal price, audience or material.')
add('bedding_and_broad_store',1,'shopelvis.com','Licensed Elvis merchandise differs materially in purchase motivation from Quince general essentials.')
add('bedding_and_broad_store',0,'thebizzbybabs.com','Sexual-wellness positioning and products do not establish useful competition for Quince everyday apparel/home essentials.')
overrides={
 ('tower28beauty','tower28beauty.com'):(0,'Own business returned as its own competitor in the empty-profile description-only scenario; the request supplies no explicit own-domain exclusion.'),
 ('iliabeauty','peachandlily.com'):(3,'Official Sun Cover is a lightly tinted mineral SPF product, directly overlapping the stated ILIA use case.'),
 ('colourpop','redaspenlove.com'):(3,'Observed eyes, lips and face makeup directly overlaps the stated product portfolio; pricing still requires comparable-product review.'),
 ('colourpop','tower28beauty.com'):(2,'Useful face/lip makeup overlap; full affordable eye-palette assortment not established.'),
 ('quince','babyletto.com'):(2,'Nursery furniture/bedding overlaps a limited part of Quince home/baby assortment; not a whole-business comparator.'),
 ('parachutehome','madisonpark2010.com'):(2,'Bedding and bath assortment is useful partial overlap; exact linen material comparability remains unverified.'),
 ('parachutehome','wildkin.com'):(1,'Child-focused bedding does not establish linen sheet and bath-linen substitution.')
}
obs={}
for dn in ['public-observations','supplemental-observations']:
 for f in (P/dn).glob('*.json'):
  o=json.loads(f.read_text())
  if o['domain'] not in obs or o['checked_at']>obs[o['domain']]['checked_at']:obs[o['domain']]=o
extra_sources={
 'peachandlily.com':['https://www.peachandlily.com/products/sun-cover-mineral-sunscreen'],
 'gracebeautybox.co.uk':['https://www.gracebeautybox.co.uk/products/bondi-sands','https://www.gracebeautybox.co.uk/products/embryolisse-complexion-correcting-care-cc-cream-30-ml'],
 'petland.ca':['https://www.petland.ca/products/purebites-freeze-dried-mini-training-lamb-liver-dog-treats'],
 'fetchyourpetneeds.ie':['https://www.fetchyourpetneeds.ie/collections/pet-brushes'],
 'redbarn.com':['https://www.redbarn.com/products/air-dried-chicken-training-treats'],
 'primary.com':['https://www.primary.com/collections/baby-pajamas/color-family-reds'],
 'pehr.com':['https://pehr.com/pages/sleepwear'],
 'volcanicacoffee.com':['https://volcanicacoffee.com/pages/coffee-club'],
}
labels=[]
for c in runs:
 for rank,d in enumerate(c['returned_domains'],1):
  a=annotations.get((c['niche'],d))
  if a is None:raise ValueError(('UNANNOTATED',c['case_id'],d))
  a=dict(a)
  if (c['case_id'],d) in overrides:a['label'],a['rationale']=overrides[(c['case_id'],d)]
  o=obs[d]
  a.update({'case_id':c['case_id'],'mode':c['mode'],'domain':d,'rank':rank,'checked_at':o['checked_at'],'public_urls':[x.get('url') for x in o['checks'].values() if x.get('url')]+extra_sources.get(d,[]),'reviewer':'single analyst; shuffled source review after debugging, not a fully blinded second reviewer','access_unknown':o['unknown_access']})
  labels.append(a)
(P/'relevance-labels.json').write_text(json.dumps(labels,indent=2))
print('Labeled',len(labels),'returned placements; label counts',collections.Counter(str(x['label']) for x in labels))
