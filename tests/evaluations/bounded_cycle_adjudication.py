"""Explicit analyst labels. These decisions never enter application code."""
import json,os,runpy
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'outputs/bounded-cycle'
SOURCE=ROOT/'docs/quality-audit/real-world/evidence'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
decisions={
 'bmilourban.com':(1,'Character/streetwear merchandise, collectibles and logo bags overlap apparel/accessories broadly; everyday household/bedding and affordable-basics substitution are not established.'),
 'baukjen.com':(1,'Adult sleepwear/loungewear and womenswear are adjacent; children bamboo pajamas are not established.'),
 'stylesgalorevintage.com':(0,'Vintage adult lingerie and fashion do not establish children bamboo sleepwear; baby tee is an adult garment style.'),
 'dlacosmetics.com':(2,'Captured lip gloss, lip liner and lip oils overlap everyday lip makeup; perfume-heavy assortment makes this a partial competitor.'),
 'tailoredcanvases.com':(0,'Canvas wall art uses blush as a color, not a makeup product.'),
 'tower28beauty.com':(1,'Sensitive-skin adult cosmetics/skincare are adjacent; infant lotion or ointment suitability is not established.'),
 'peachandlily.com':(1,'Human skincare is adjacent, without evidence of infant-specific fragrance-free formulations.'),
 'kallureskloset.com':(0,'Observed handbags and mixed fashion accessories, not evidenced infant lotion or ointment.'),
 'monstersink.com':(0,'Tattoo supplies and tattoo aftercare target a different use and audience from sensitive infant skincare.'),
 'queensupplies.com':(0,'Professional nail/pedicure supply and salon products do not establish infant skincare substitution.'),
 'medicalsupplysurplus.com':(1,'Skin and wound-care supplies provide functional adjacency, not demonstrated infant skincare suitability.'),
 'thebizzbybabs.com':(0,'Adult intimacy and personal-care products do not satisfy fragrance-free infant skincare intent.'),
 'memoky.com':(0,'Furniture catalog contains coffee tables. The modifying word coffee does not establish roasted beans or subscriptions.'),
 'luxechiccouture.com':(0,'Public boutique offers adult fashion rompers and event outfits, not bamboo infant/family sleepwear.'),
 'de.silksilky.com':(1,'Adult silk pajamas are adjacent sleepwear; infant bamboo or matching-family substitution is not established.'),
 'pehr.com':(2,'Official infant sleepwear and sleep bags overlap the sleep use case. Cotton/modal differs from bamboo; adult matching is not established.'),
 'babysprouts.com':(2,'Captured catalog and merchant description establish baby/children clothing, bamboo and sleep/play garments. Useful partial overlap; adult matching and every requested sleep-bag type are not established.'),
 'babyelaine.com':(1,'Designer children daywear and rompers are adjacent; captured evidence does not establish bamboo pajamas or sleep bags.'),
 'apolina-kids.com':(1,'Embroidered children daywear and rompers are adjacent, without established bamboo pajama or sleep-bag substitution.'),
 'babymel.com':(None,'Preserved public checks fail with 502. Historical MORI products are insufficient to establish the current merchant/redirect identity; original uncertainty retained.'),
 'blessviva.com':(0,'Preserved public catalog shows pet food, conflicting with older mixed merchandise metadata; bamboo children sleepwear is not established.'),
 'kensfish.com':(0,'Observed fish/aquarium assortment does not establish freeze-dried raw training treats for dogs.'),
 'vessi.com':(1,'Waterproof footwear with accessory apparel/bags is adjacent to broad clothing/home retail; broad household or bedding overlap is not evidenced.'),
 'pearlizumi.com':(1,'Cycling-specific apparel and footwear overlap clothing broadly, not the stated broad everyday clothing/home assortment.'),
 'fuegodance.com':(1,'Dance sneakers and accessory apparel are adjacent to broad clothing/home retail, without meaningful household overlap.'),
 'shopshowroom.com':(2,'Public assortment includes women clothing, bags, jewelry and home accessories. Useful partial merchandise overlap; affordable price equivalence is not established.'),
 'shop.friendsofcabrilloaquarium.org':(0,'Aquarium gift shop sells books, puzzles and sticker sheets; sheet wording is not bedding.'),
 'hydrusboardtech.com':(1,'Paddleboards and carry accessories share an outdoor audience, without evidenced lightweight hiking shelters or hiking pack substitution.'),
 'bagsandshoes.net':(1,'General backpacks and footwear are adjacent; lightweight hiking shelter/pack functionality is not established.'),
 'wildkin.com':(1,'Children school backpacks are adjacent bags, not demonstrated lightweight hiking packs or shelters.'),
 'jamesleather.com':(1,'Leather/canvas backpacks and travel luggage are adjacent, without lightweight hiking-pack functionality.'),
 'lheureuxinc.com':(2,'Previously adjudicated merchant sells whole-bean coffee with recurring delivery; equipment-led Canadian retail is a partial competitor.'),
 'corkcicle.com':(1,'Coffee drinkware serves the audience but does not substitute for specialty-roasted beans/subscriptions.'),
 'babyletto.com':(1,'Crib bedding and nursery furniture are adjacent; adult linen bedding and bath-linen substitution is not established.'),
 'fashionfinderhub.com':(0,'Captured assortment mixes adult fashion and artificial nails; printed bamboo children sleepwear is not evidenced.'),
}
reviews=[]; summaries={}
for variant in ['frozen','controlled']:
 p=OUT/variant; labels=load(p/'known-labels.json')
 for entry in load(p/'pending.json'):
  label,reason=decisions[entry['domain']]
  item={**entry,'label':label,'rationale':reason,'reviewer':'single analyst, not blind independent review',
    'checked_at':datetime.now(timezone.utc).isoformat(),'public_urls':['https://'+entry['domain']],
    'access_unknown':label is None,'provenance':'bounded cycle explicit product-evidence adjudication'}
  labels.append(item);reviews.append({'variant':variant,**item})
 runs=load(p/'evidence/replay-results.json')
 expected={(r['case_id'],r['mode'],d,i) for r in runs for i,d in enumerate(r['returned_domains'],1)}
 assert len(labels)==len(expected)
 assert {(r['case_id'],r['mode'],r['domain'],r['rank']) for r in labels}==expected
 (p/'evidence/relevance-labels.json').write_text(json.dumps(labels,indent=2),encoding='utf8')
 os.chdir(p);runpy.run_path(str(SOURCE/'measure.py'))
 metrics=load(p/'evidence/benchmark-metrics.json');metrics['benchmark']='Bounded cycle, unchanged reference panel, rebuilt JSONB retrieval and product-intent filter; no paid AI'
 (p/'evidence/benchmark-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf8')
 summaries[variant]=metrics
(OUT/'adjudications.json').write_text(json.dumps(reviews,indent=2),encoding='utf8')
(OUT/'benchmark-comparison.json').write_text(json.dumps(summaries,indent=2),encoding='utf8')
