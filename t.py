import json

data = []
with open("data/transcripts.json") as f:
	data = json.load(f)

seen = []
seen_objs = []

for d in data:
	url = d.get("videoUrl", None)
	text = d.get("text", None)
	title = d.get("videoTitle", None)
	if not url or not "?v=" in url or not text or not len(text) or not title:
		continue
	id = url.split("?v=")[-1]
	if id in seen:
		continue
	obj = {
		"content": text,
		"url": url,
		"title": title,
		"id": id
	}
	seen.append(id)
	seen_objs.append(obj)

with open("clean_youtube.json", "w") as f:
	f.write(json.dumps(seen_objs))
