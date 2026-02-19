import json
data = []
pdfs = []
youtube = []

with open("data/serp1.json", "r") as f:
	results = json.load(f)
	for r in results:
		res = r.get("results", [])
		for d in res:
			url = d.get("url", None)
			if not url or "linkedin.com/in/ketan" in url or "inkedin.com/posts/ketan-patel" in url or "linkedin.com/posts/ketanpatel" in url or "medic" in url or "health" in url or "instagram" in url or ("facebook" in url and "groups" in url):
				continue
			text = d.get("title", "") + " - " + d.get("description", "")
			if not "ketan patel" in text.lower() and not "k. patel" in text.lower():
				continue
			if "Dr. Ketan Patel" in text or "Executive Networks | LinkedIn - Ketan Patel" in text or "Ketan Patel's Post - LinkedIn" in text or "ketan patel, phd" in text.lower() or "ketan patel phd" in text.lower() or "professor ketan patel" in text.lower() or "kush ketan patel" in text.lower():
				continue
			if "chief human resources" in text.lower() or "HP" in text or "@hp" in text or "pharmaceut" in text.lower() or "HR" in text or 'medical' in text.lower() or 'autism' in text.lower() or "surgery" in text.lower():
				continue
			if "blockchain" in text.lower() or "crunchbase" in text.lower() or "Science of Materials" in text or "CASHe" in text or "mswipe" in text.lower() or "software engineer" in text.lower() or "it leader" in text.lower() or "hospitality" in text.lower() or "physician" in text.lower() or "doctor" in text.lower() or "cmd" in text.lower() or "Todd Lohr" in text or "Institute of Materials" in text or ("healthcare" in text.lower() and "kpmg" in text.lower()) or "Prophylactic" in text:
				continue
			obj = {
				"url": url,
				"text": text
			}
			if "youtube" in url:
				if not obj in youtube:
					youtube.append(obj)
			elif ".pdf" in url:
				if not obj in pdfs:
					pdfs.append(obj)
			else:
				if not obj in data:
					data.append(obj)

with open("serpclean1pdfs.json", "w") as f:
	print(f"Length of pdf results: {len(pdfs)}")
	f.write(json.dumps(pdfs))

with open("serpcleanyoutube1.json", "w") as f:
	print(f"Length of youtube results: {len(youtube)}")
	f.write(json.dumps(youtube))

with open("serpclean1.json", "w") as f:
	print(f"Length of data results: {len(data)}")
	f.write(json.dumps(data))
