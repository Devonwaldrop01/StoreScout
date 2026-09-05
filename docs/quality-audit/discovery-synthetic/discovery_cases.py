"""Synthetic, hand-labelled review cases, not real merchants or live index data.
Labels: 3=direct substitute; 2=related; 1=weak; 0=irrelevant. Domain .test.
Product/audience/price assumptions are explicitly supplied to isolate ranking.
"""
CASES = [
    ('ceramics', 'Home & Living', 'handmade ceramic ashtrays', 'adult collectors', 'budget',
     [('ceramic ashtrays handmade',3,'adult collectors','budget'),('ceramic ashtray handmade',3,'adult collectors','budget'),('ceramic vases home decor',1,'adult collectors','budget'),('ceramic ashtrays handmade',1,'luxury hospitality','luxury'),('sofa furniture cushions',0,'adult collectors','budget')]),
    ('running', 'Footwear', 'running shoes trainers', 'adult runners', 'mid-market',
     [('running shoes trainers',3,'adult runners','mid-market'),('running sneaker trainer',3,'adult runners','mid-market'),('running shoes trainers',1,'children school','mid-market'),('running shoes trainers',1,'adult runners','luxury'),('leather formal boots',0,'adult runners','mid-market')]),
    ('pets', 'Pets', 'sensitive dog food', 'adult dog owners', 'premium',
     [('sensitive dog food',3,'adult dog owners','premium'),('sensitive dog foods',3,'adult dog owners','premium'),('dog food bowl ceramic',1,'adult dog owners','premium'),('cat litter toys',0,'cat owners','premium'),('sensitive dog food',1,'adult dog owners','budget')]),
    ('baby', 'Kids & Baby', 'organic infant sleepwear', 'parents infants', 'mid-market',
     [('organic infant sleepwear',3,'parents infants','mid-market'),('organic infant sleepsuit',3,'parents infants','mid-market'),('organic infant sleepwear',1,'parents infants','luxury'),('teen school backpacks',0,'teen students','mid-market'),('organic cotton blankets',1,'parents infants','mid-market')]),
    ('coffee', 'Food & Beverage', 'espresso coffee beans', 'home espresso brewers', 'premium',
     [('espresso coffee beans',3,'home espresso brewers','premium'),('espresso coffee bean',3,'home espresso brewers','premium'),('espresso coffee beans',1,'wholesale restaurants','premium'),('coffee candy chocolates',1,'gift shoppers','premium'),('tea infusion leaves',0,'home espresso brewers','premium')]),
    ('skincare', 'Beauty', 'fragrance free eczema moisturizer', 'sensitive skin adults', 'mid-market',
     [('fragrance free eczema moisturizer',3,'sensitive skin adults','mid-market'),('fragrance free eczema moisturiser',3,'sensitive skin adults','mid-market'),('fragrance perfume spray',0,'sensitive skin adults','mid-market'),('eczema moisturizer',1,'sensitive skin adults','luxury'),('nail polish manicure',0,'sensitive skin adults','mid-market')]),
    ('broad_store', 'Home & Living', 'ergonomic office chair', 'home office workers', 'mid-market',
     [('ergonomic office chair',3,'home office workers','mid-market'),('ergonomic office chairs',3,'home office workers','mid-market'),('chair sofa candles mugs kitchen rug towel bedding lamp desk',1,'general shoppers','mid-market'),('ergonomic office chair',1,'children classroom','budget'),('office poster decor',0,'home office workers','mid-market')]),
    ('weak_metadata', 'Outdoors', 'ultralight hiking tent', 'backpacking hikers', 'premium',
     [('ultralight hiking tent',3,'backpacking hikers','premium'),('ultralight hiking tents',3,'backpacking hikers','premium'),('hiking jacket waterproof',1,'backpacking hikers','premium'),('ultralight hiking tent',1,'car camping families','budget'),('surf board wetsuit',0,'backpacking hikers','premium')]),
]


def cases():
    for name, cat, query, audience, tier, specs in CASES:
        user = dict(category=cat, dna_keywords=query.split(), target_customer=audience, pricing_tier=tier)
        pool=[]
        # Deliberately high verification on weak rows: platform certainty isn't relevance.
        for i,(products,label,aud,price) in enumerate(specs):
            pool.append(dict(domain=f'{name}-{i}.test', category=cat, category_confidence=90,
                verification_confidence=70 if label==3 else 100, _by_category=True,
                product_types=products.split(), product_titles=[products], dna_keywords=products.split(),
                target_customer=aud, pricing_tier=price, label=label, status='verified',
                verification_signals=['Product catalog accessible'],last_verified_at='2026-09-05T12:00:00+00:00'))
        yield name,user,pool


def baseline_score(row,user):
    # Pinned from competitors.py::_relevance at local pre-quality commit 70af98e.
    from app.services.store_dna import dna_match_score
    return row['verification_confidence'] + 60 + min(20,row['category_confidence']/5) + .45*dna_match_score(row,user) + (12 if row['pricing_tier']==user['pricing_tier'] else 0)


def evaluate(score):
    results=[]
    for name,user,pool in cases():
        ranked=sorted(pool,key=lambda row:score(row,user),reverse=True)
        top=ranked[:3]
        results.append(dict(case=name,top3=[r['domain'] for r in top],labels=[r['label'] for r in top],
            direct_precision_at_3=round(sum(r['label']==3 for r in top)/3,3),
            missed_direct=[r['domain'] for r in ranked[3:] if r['label']==3]))
    return results

# Held-out wording challenges added after the initial scorer was implemented.
# Do not silently expand aliases to make these pass; keep misses visible.
WORDING_HOLDOUT = [
    ('skin_wording','Beauty','unscented skin repair balm','fragrance-free eczema moisturizer','skin repair cleansing brush'),
    ('shelter_wording','Outdoors','hiking shelter','ultralight backpacking tent','hiking backpack'),
    ('pet_wording','Pets','raw dog treats','freeze dried chicken reward bites','dog treat storage jar'),
]
