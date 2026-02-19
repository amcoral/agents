import json

seen= []
clean = []

with open("data/web2.json", "r") as f:
	data = json.load(f)
	print(f"Total: {len(data)}")
	for d in data:
		url = d.get("url", None)
		if not url:
			continue
		title = d.get("title", "")
		if d.get("openGraph", None):
			try_title = [o.get("content", None) for o in d.get("openGraph", []) if o.get("property", None) == "og:title"]
			if len([t for t in try_title if t]) == 1:
				title = try_title
		content = d.get("text", None)
		if not content:
			continue
		obj = {
			"url": url,
			"title": title,
			"content": content
		}
		if not url in seen:
			clean.append(obj)
			seen.append(url)

print(f"Final: {len(clean)}")

with open("unique_youtube.json", "r") as f:
	data = json.load(f)
	clean += data

all_pdf_links = {}
with open("serpclean1pdfs.json", "r") as f:
	data = json.load(f)
	for d in data:
		title = d.get("text", "").split(" - ")[0].replace("[PDF]", "").strip()
		url = d.get("url", None)
		if not url:
			continue
		if not url in all_pdf_links:
			all_pdf_links[url] = title

with open("data/pdfs.json", "r") as f:
	data = json.load(f)
	for d in data:
		url = d.get("pdfUrl", None)
		if not url:
			continue
		title = all_pdf_links.get(url, "")
		content = d.get("extractedText", "").strip().replace("\n\n\n", "\n\n").replace("\t", " ")
		if not len(content):
			continue
		obj = {
			"url": url,
			"title": title,
			"content": content
		}
		if not url in seen:
			clean.append(obj)
			seen.append(url)

print(len(clean))
with open("all_res.json", "w") as f:
	f.write(json.dumps(clean))
