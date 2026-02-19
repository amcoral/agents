import json

clean = []
seen = []
with open("data/transcripts.json", "r") as f:
	data = json.load(f)
	print(f"Total: {len(data)}")
	for d in data:
		url = d.get("videoUrl", None)
		text = d.get("text", None)
		title = d.get("videoTitle", None)
		if not url or not text:
			continue
		obj = {
			"url": url,
			"title": title,
			"context": text
		}
		if not url in seen:
			seen.append(url)
			clean.append(obj)

print(f"Deduped total: {len(clean)}")

with open("unique_youtube.json", "w") as f:
	f.write(json.dumps(clean))
