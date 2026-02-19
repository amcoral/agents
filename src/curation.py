import json

def combine_facts():
	# Initialize the combined object with empty arrays
	combined = {
		"LEDE": [],
		"EARLY": [],
		"CAREER": [],
		"IDEAS": [],
		"WORKS": [],
		"HONORS": [],
		"PHIL": [],
		"RECEPTION": [],
		"BACKMATTER": []
	}

	# Read through all JSONL objects
	with open("facts2.jsonl", "r") as f:
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

			# Combine each key's array into the combined object
			for key in combined.keys():
				if key in obj and isinstance(obj.get(key, []), list):
					combined[key].extend(obj[key])

	# Write the combined object to combined_facts.json
	with open("combined_facts.json", "w") as f:
		json.dump(combined, f, indent=2)

	print(f"Combined facts written to combined_facts.json")
	print(f"Total facts by category:")
	for key, value in combined.items():
		print(f"  {key}: {len(value)} facts")

if __name__ == "__main__":
	combine_facts()
