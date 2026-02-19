import json
from os import write
fb = []
linkedin = []
f4g = []
waas = []
all = []

def write_json_file(filename, json_data):
	with open(filename, "w") as f:
		f.write(json.dumps(json_data))

with open("urls.json", "r") as f:
	data = json.load(f)
	for i in data:
		if "waas" in i or "world-academy" in i or "garry" in i:
			waas.append(i)
		elif "facebook" in i:
			fb.append(i)
		elif "linkedin" in i:
			linkedin.append(i)
		elif "forcegood.org" in i:
			f4g.append(i)
		else:
			all.append(i)


write_json_file("urls_fb.json", fb)
write_json_file("urls_f4g.json", f4g)
write_json_file("urls_waas.json", waas)
write_json_file("urls_linkedin.json", "linkedin")
write_json_file("urls_other.json", all)
