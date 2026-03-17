import json

with open("output/raw_data.json") as f:
    data = json.load(f)

detail_fields = ["has_video", "description_length", "tags", "has_portfolio"]
total = len(data)
filled = sum(
    1 for item in data
    if any(item.get(f) is not None for f in detail_fields)
)
print(f"Покрытие: {filled}/{total} = {filled/total*100:.1f}%")
print("✅ OK" if filled/total >= 0.9 else "❌ Ниже 90% — смотрим errors.log")
