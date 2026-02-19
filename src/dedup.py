import json



def get_clean_facts(file_name, all, raw_list):
	with open("final_facts.jsonl", "r") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			# Parse the JSON object
			try:
				obj = json.loads(line)
			except json.JSONDecodeError:
				continue

			# Skip if obj is None or not a dictionary
			if not obj or not isinstance(obj, dict):
				continue
			sources = obj.get("sources", [])
			if not len(sources):
				continue
			clean_sources = {}
			for s in sources:
				access_status = s.get("access_status", "")
				access_notes = s.get("access_notes", "")
				source_id = s.get("source_id", None)
				url = s.get("url", None)
				if "error" in access_status or "error" in access_notes or "not access" in access_notes or not source_id or "blocked" in access_notes.lower() or "forbidden" in access_notes.lower() or "failed" in access_notes.lower() or not url:
					continue
				new_source = {
					"url": url,
					"title": s.get("title", "unknown"),
					"authors": s.get("authors", []),
					"publisher": s.get("publisher", "unknown"),
					"date": s.get("publication_date", "unknown")
				}
				clean_sources[source_id] = new_source
			excerpts = obj.get("excerpts", [])
			if not len(excerpts):
				continue
			for e in excerpts:
				cat = e.get("category", "")
				subcat = e.get("subcategory", "")
				text = e.get("excerpt_text", None)
				if not text or text in raw_list:
					continue
				evidence = e.get("evidence", [])
				eses = []
				for ev in evidence:
					s_id = ev.get("source_id", None)
					if not s_id:
						continue
					if s_id in clean_sources:
						eses.append(clean_sources[s_id])
				if not len(eses):
					continue
				new_ex = {
					"content": text,
					"sources": eses,
					"category": cat,
					"subcategory": subcat
				}
				if all.get(cat, {}).get(subcat, None):
					all[cat][subcat].append(new_ex)
				elif all.get(cat, None):
					all[cat][subcat] = [new_ex]
				else:
					all[cat] = {}
					all[cat][subcat] = [new_ex]
				raw_list.append(text)
	return all, raw_list

def clean():
	data = None
	cleaned = {}
	num_facts_old = 0
	num_facts_new = 0
	with open("all_facts_clean.json") as f:
		data = json.load(f)
	for cat, subcat_obj in data.items():
		new_cat = {}
		for subcat, facts in subcat_obj.items():
			bad_subcats = ["disclaimer", "controversy", "death", "illness", "bereavement", "obituary", "error", "unauthorized", "access denied", "unavailable", "fail", "coffee", " tea ", "Coffee", " Tea ", "Last updated", "last updated", "last-updated", "Last-Updated", "Last Updated"]
			if not len(facts) or any([k in subcat.lower() for k in bad_subcats]):
				continue
			num_facts_old += len(facts)
			clean_facts = []
			for fact in facts:
				print(fact)
				content = fact.get("content", None)
				source = fact.get("source", None)
				if not content or not source:
					continue
				bad_keys = ["pharma", "hospital", "real estate", "HP", "hotel", "restaurant", "cricket", "lawyer", "law group", "virus", "phd", "medical", "cancer", "clinic", "doctor", "hospital", "tuition", "arrest", "HR", "EdenTree", "attourney", "Attourney", "dystrophin", "cell", "realtor", 'ecommerce', 'shop owner', 'store owner', 'microbiology', 'university of i', 'legal case', 'robbery', 'crime', " visa ", " filing ", ""]
				if any([k.lower() in content.lower() for k in bad_keys]) or any([k in source.get("title", "") for k in bad_keys]):
					continue
				clean_facts.append(
					{
						"content": content,
						"source": source
					}
				)
				num_facts_new += 1
			if not len(clean_facts):
				continue
			new_cat[subcat] = clean_facts
		if not len(list(new_cat.keys())):
			continue
		cleaned[cat] = new_cat
	print(f"Original fact list length: {num_facts_old} | New clean fact list length: {num_facts_new}")
	return cleaned

def clean_list():
	data = None
	cl = []
	with open("all_facts_clean.json") as f:
		data = json.load(f)
	for cat, subcat_obj in data.items():
		for subcat, facts in subcat_obj.items():
			for f in facts:
				f["info_type"] = subcat
				del f["source"]["authors"]
				cl.append(f)
	return cl

def group_by_source():
	data = None
	cl = []
	sources = []
	with open("all_facts_final.json") as f:
		data = json.load(f)
	for d in data:
		source = d.get("source", None)
		if not source:
			continue
		url = source.get("url", None)
		if not url:
			continue
		if not url in cl:
			cl.append(url)
			idx = cl.index(url)
			source["id"] = idx
			sources.append(source)
		else:
			continue
	all = []
	for so in sources:
		s = dict(so)
		url = s["url"]
		vals = [d for d in data if d["source"]["url"] == url]
		clean_facts = []
		for v in vals:
			content = v.get("content", None)
			info_type = v.get("info_type", None)
			if not content or not info_type:
				continue
			f = {
				"content": content,
				"info_type": info_type
			}
			clean_facts.append(f)
		s["facts"] = list(clean_facts)
		all.append(s)
	return all



if __name__ == "__main__":
	cleaned = group_by_source()
	with open("by_source.json", "w") as f:
		f.write(json.dumps(cleaned))
