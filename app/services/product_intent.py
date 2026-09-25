"""Conservative product nouns, independent of merchant identity or benchmark labels.

Families describe substitutable product uses. Broad category, audience, color,
material and marketing words alone are not evidence of those uses.
"""
import re

FAMILIES = {
    'keyboard': r'\bkeyboards?\b',
    'keyboard_accessory': r'\b(?:keycaps?|keyboard[ -]+(?:covers?|cases?|skins?|switches?))\b',
    'complexion': r'\b(?:skin[ -]+tints?|tinted[ -]+(?:mineral[ -]+)?(?:moisturi[sz]ers?|sunscreens?)|(?:bb|cc)[ -]+creams?|foundations?|concealers?|complexion|makeup|cosmetics?|sunscreens?|lipsticks?|mascaras?|eyeliners?|eyeshadows?|bronzers?|blush|lip[ -]+(?:gloss|liners?|oils?)|(?:face|setting|pressed)[ -]+powder)\b',
    'sleepwear': r'\b(?:pajamas?|pyjamas?|sleepwear|sleepsuits?|sleep[ -]+(?:bags?|sacks?)|rompers?|footies?)\b',
    'apparel': r'\b(?:clothing|apparel|shirts?|tees?|dress(?:es)?|jeans|pants|skirts?|jackets?|hoodies?|sweaters?)\b',
    'bags': r'\b(?:bags?|handbags?|purses?|wallets?|backpacks?|cardholders?)\b',
    'jewelry': r'\b(?:jewelry|jewellery|necklaces?|bracelets?|earrings?|signet)\b',
    'nursery': r'\b(?:strollers?|prams?|cribs?|bassinets?|baby[ -]+carriers?|car[ -]+seats?)\b',
    'skincare': r'\b(?:skin[ -]?care|lotions?|ointments?|cleansers?|moisturi[sz]ers?|serums?)\b',
    'coffee': r'\b(?:coffee|espresso)\b',
    'dog_food': r'\b(?:(?:dog|canine|pet)[ -]+(?:foods?|treats?|chews?)|bully[ -]+sticks?|freeze[ -]+dried|air[ -]+dried|raw[ -]+(?:foods?|treats?))\b',
    'shelter': r'\b(?:tents?|shelters?|tarps?)\b',
    'backpack': r'\b(?:backpacks?|rucksacks?|hiking[ -]+packs?)\b',
    'bedding': r'\b(?:bedding|sheets?|comforters?|duvets?|quilts?|bath[ -]+linens?)\b',
}

def families(text):
    text = str(text or '').lower()
    found = {name for name, pattern in FAMILIES.items() if re.search(pattern, text)}
    if re.search(r'\b(?:canvas|posters?|wall[ -]+art|shirts?|dress(?:es)?|skirts?|pants|cardigans?|sweaters?|bags?|pouches?|cases?|brushes?|organizers?|makeup[ -]+tools?)\b',text):
        # Cosmetic words used as garment colors, artwork or accessory themes
        # do not change the product's physical use.
        found.discard('complexion')
    # An accessory mentioning its host product is not that product. Apply per
    # item so a merchant selling both complete keyboards and covers remains eligible.
    if 'keyboard_accessory' in found and re.search(r'\bkeyboard[ -]+(?:covers?|cases?|skins?|switches?)\b',text):
        found.discard('keyboard')
    if re.search(r'\bcoffee[ -]+tables?\b',text):
        found.discard('coffee')
    if re.search(r'\b(?:sticker|blotting|silicone|metal)[ -]+sheets?|\bsheet[ -]+(?:mask|music)|\bmask[ -]+sheets?|\b(?:laundry|hamper|poultry|chicken|coop)\b',text):
        found.discard('bedding')
    return found

def product_intent_check(row, user):
    query = ((user or {}).get('sells') or (user or {}).get('description')
             or ' '.join((user or {}).get('dna_keywords') or []))
    requested = families(query)
    if 'sleepwear' in requested:
        requested.discard('apparel')
        requested.discard('bags')  # sleep bags name a sleep product, not luggage
    if 'backpack' in requested:
        requested.discard('bags')
    if 'complexion' in requested:
        requested.discard('skincare')
    titles = row.get('product_titles') or []
    types = row.get('product_types') or []
    items = [*types, *titles]
    title_families = [families(item) for item in titles]
    actual = set().union(*(families(item) for item in items)) if items else set()
    # Preserve unknown intents and metadata-only legacy behavior. For a recognized
    # intent and an observed catalog, require an actual product-family match.
    supported = not requested or not items or bool(requested & actual)
    reason = None if supported else 'observed_catalog_missing_requested_product_family'
    # A type label has no frequency or title association in historical rows.
    # When titles exist, an unrelated type alone cannot establish a niche.
    # Type-only legacy rows retain their existing fallback behavior.
    title_support = [item for item, found in zip(titles, title_families) if requested & found]
    if requested and titles and not title_support:
        supported = False
        reason = 'sampled_titles_missing_requested_product_family'
    child_pattern = r'\b(?:infants?|toddlers?|newborns?|children|kids?|babies|baby)\b(?![ -]+(?:blue|pink|tee|blender))'
    needs_child = bool(re.search(child_pattern,query.lower()))
    # Audience and product must describe the same item. "Baby toy" plus
    # "adult lotion" must never manufacture evidence for baby lotion.
    evidence_items = titles if titles else types
    child_evidence = any(requested & families(t) and re.search(child_pattern,str(t).lower())
                         for t in evidence_items)
    if requested and items and needs_child and not child_evidence:
        supported = False
        reason = 'requested_audience_not_linked_to_product'
    return {'supported': supported, 'requested_families':sorted(requested),
            'matching_title_count':len(title_support),'sampled_title_count':len(titles),
            'child_audience_required':needs_child,'child_audience_evidenced':child_evidence,
            'observed_families':sorted(actual),
            'reason':reason}
