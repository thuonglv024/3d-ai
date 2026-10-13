import json

prods = json.load(open('all_160_products.json', encoding='utf-8'))
orig_22 = {
    'ao-khoac-blazer-linen', 'ao-khoac-bomber-minimal', 'ao-khoac-cardigan-len', 'ao-khoac-trench-coat-ngan',
    'ao-thun-essential', 'ao-thun-oversized-heavyweight', 'ao-thun-striped-relaxed', 'ao-thun-supima-crewneck', 'ao-thun-waffle-long-sleeve',
    'chan-vay-chu-a-linen', 'chan-vay-jean-xe-ta', 'chan-vay-pleated-midi', 'dam-suong-linen-minimal',
    'quan-jeans-regular-selvedge', 'quan-khaki-chino-straight', 'quan-linen-cap-chun', 'quan-tay-pleated-wide-leg',
    'so-mi-co-tru-minimal', 'so-mi-cuban-collar', 'so-mi-denim-nhe', 'so-mi-linen-thoang-khi', 'so-mi-oxford-classic'
}

with open('catalog_breakdown.txt', 'w', encoding='utf-8') as out:
    for cat in ['ao-khoac', 'ao-thun', 'quan', 'so-mi', 'vay']:
        cat_prods = [p for p in prods if p['cat_slug'] == cat]
        rem = [p for p in cat_prods if p['slug'] not in orig_22]
        out.write(f"\n=== Category: {cat} (total {len(cat_prods)}, remaining {len(rem)}) ===\n")
        for p in rem:
            out.write(f"  {p['slug']} | {p['name']} | {p['material']} | {p['fit']}\n")

print("Done writing breakdown.")
