import json

data = []
with open("data/linkedin.json", "r") as f:
	data = json.load(f)

relevant = [d for d in data if d.get('content', None) and "ketan patel" in d.get("content", "").lower()]

clean = []

for r in relevant:
	obj = {
		"date": r.get("postedAt", {}).get("date", ""),
		"content": r.get("content", ""),
		"article_title": r.get("article", {}).get("title", ""),
		"author_domain": r.get("article", {}).get("subtitle", ""),
		"article_url": r.get("article", {}).get("link", "")
	}
	clean.append(obj)

with open("clean_linkedin.json", "w") as f:
	f.write(json.dumps(clean))
