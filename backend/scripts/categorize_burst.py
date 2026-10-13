import json

with open("backend/scripts/burst_discovered_photos.json", "r", encoding="utf-8") as f:
    photos = json.load(f)

print(f"Total discovered photos: {len(photos)}")

categories = {
    "cat-ao-thun": [],
    "cat-so-mi": [],
    "cat-quan": [],
    "cat-ao-khoac": [],
    "cat-vay": []
}

tshirt_keywords = ["tshirt", "t-shirt", "tee", "crewneck", "v-neck"]
shirt_keywords = ["shirt", "oxford", "button", "flannel", "chambray", "blouse", "collar", "tunic"]
pants_keywords = ["pant", "jean", "trouser", "chino", "denim", "khaki", "bottom", "short", "legging", "sweatpant"]
jacket_keywords = ["jacket", "blazer", "coat", "bomber", "cardigan", "sweater", "outerwear", "hoodie", "vest", "poncho", "trench", "parka", "windbreaker", "pullover"]
dress_keywords = ["dress", "skirt", "gown", "midi", "maxi", "mini", "wrap", "sundress"]

unclassified = []

for slug, col in photos.items():
    s = slug.lower()
    # Exclude obvious non-apparel
    if any(x in s for x in ["wall", "camera", "tool", "sign", "mask", "shoe", "boot", "sneaker", "ring", "watch", "makeup", "coffee", "cup", "hanger", "laundry", "table", "store", "rack", "shop", "tag", "counter", "shelf", "pile", "stack", "art", "paint", "flower", "leaf", "plant", "umbrella", "yoga", "sewing"]):
        continue

    matched = False
    if any(k in s for k in jacket_keywords):
        categories["cat-ao-khoac"].append(slug)
        matched = True
    elif any(k in s for k in dress_keywords):
        categories["cat-vay"].append(slug)
        matched = True
    elif any(k in s for k in pants_keywords):
        categories["cat-quan"].append(slug)
        matched = True
    elif any(k in s for k in tshirt_keywords):
        categories["cat-ao-thun"].append(slug)
        matched = True
    elif any(k in s for k in shirt_keywords):
        categories["cat-so-mi"].append(slug)
        matched = True
    
    if not matched:
        unclassified.append(slug)

print("\nApparel matches found in Burst by category:")
for cat, items in categories.items():
    print(f"  {cat}: {len(items)} photos")
    for it in items[:5]:
        print(f"    - {it}")

print(f"\nUnclassified fashion photos: {len(unclassified)}")
for it in unclassified[:15]:
    print(f"  ? {it}")
