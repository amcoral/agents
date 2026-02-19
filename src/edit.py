import json

data = []
with open("combined_facts.json") as f:
	data = json.load(f).get("LEDE", [])

clean = []
for d in data:
	text = d.get("text", "")
	if len(text.split(" ")) < 4:
		continue
	clean.append(d)

print(clean)
