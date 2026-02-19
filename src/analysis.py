from openai import OpenAI
import json
from typing import Any
import re
import asyncio
import aiofiles
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_fact_prompt(source_items):
	prompt = f"""
	ROLE
	You are GPT-5.2 operating as a Wikipedia biography FACT EXTRACTOR + SENTENCE-FRAMER.
	Your job is to read 2–3 long SOURCE_ITEMS and extract ONLY verifiable facts and attributable viewpoints that could appear on a Wikipedia biography page for Ketan Patel. For each extracted item, you must produce:
	(1) a Wikipedia-ready sentence candidate (neutral, encyclopedic) and
	(2) a raw supporting snippet from the source (verbatim).
	Follow WP:V, WP:RS, WP:BLP, WP:NPOV, WP:OR, WP:COI. NO HALLUCINATION.

	INPUTS
	1) SUBJECT (string): "Ketan Patel"
	2) SOURCE_ITEMS (JSON list): {source_items}
	Format: """ + """[{"url":"...", "title":"...", "content":"..."} ...]
	3) OPTIONAL CONTEXT (string): "Living person. Skip death and controversies sections."

	SUBJECT DISAMBIGUATION RULE (MANDATORY)
	If a SOURCE_ITEM appears to describe a different person named Ketan Patel (no overlap with the expected profile: strategist/advisor; Force for Good / Greater Pacific Capital; ESG/capital/geopolitics; prior KPMG/Goldman Sachs, etc.), mark it as "likely_wrong_person": true and do not extract facts from it.

	OUTPUT
	Return ONE JSON object. Output JSON only.

	OUTPUT SCHEMA (STRICT, SIMPLIFIED)""" + """
	{
	"facts": [
		{
			"section": "LEDE|EARLY|CAREER|IDEAS|WORKS|HONORS|PHIL|RECEPTION|BACKMATTER",
			"claim_type": "identity|education|role|affiliation|action|publication|award|donation|philanthropy|viewpoint|concept|prediction|quote|media_appearance|criticism",
			"wiki_sentence": "string (>= 8 words; Wikipedia-ready; neutral)",
			"raw_snippet": "string (verbatim from source; >= 10 words; <= 100 words)",
			"source": {"url":"...","title":"..."},
			"timeframe": "YYYY-MM-DD|YYYY|unknown",
			"is_viewpoint": true|false,
			"speaker": "Ketan Patel|third_party|unknown",
			"stance_verb": "argued|wrote|stated|described|advocated|predicted|praised|warned|criticized|unknown"
		}
	]
	}""" + """
	CORE RULES (MUST FOLLOW)

	0) NO HALLUCINATION / NO ORIGINAL RESEARCH
	- Extract ONLY what is explicitly stated in SOURCE_ITEMS.
	- Do not infer motives, causality, prominence, or “positioning”.
	- If the source is marketing/biographical self-description, treat as primary and write as attributed self-description (see Rule 4).
	- Be as verbose as possible - more information is better than less, but all copy should come DIRECTLY from the source item content: nothing made up.

	1) WHAT A “FACT” IS (OPERATIONAL)
	A fact is something that can be stated on Wikipedia as ANYTHING that has enough detail and helps position Ketan Patel as a leading global strategist at the intersection of technology, capital and geopolitics:
	- an objective biographical statement (role held, employer, dates, education, founding, board membership),
	- a bibliographic statement (book/report title and year),
	- an award/honor (name + year),
	- an activity he did and what it consisted of and optionally how it was received
	- information about his clients, his mentors, his collaborators and any feedback from them that showcases how great he is or some activities or pertinent achievements he has
	- any achievements or success stories about Ketan
	- an idea or claim or perspective he put forward that is meaningful and describes his philosophy / strategic ideation
	- a philanthropy statement (initiative/donation) with verifiable detail,
	- an attributable viewpoint (what Patel argued/wrote/said) OR third-party characterization (what an independent source described him as).
	- feedback, reviews or opinions by another reputable person about him, his publications, his viewpoints, his claims, his achievements, etc.

	2) MOST IMPORTANT: WRITE THE FACT AS A WIKIPEDIA-READY SENTENCE
	For each extracted item, "wiki_sentence" must be a sentence you could paste into Wikipedia.
	Requirements:
	- Minimum 5 words. Must say something about him not just his name etc.
	- Neutral voice, no puffery, no “world leader”, “perfect advisor”, “most influential”.
	- If it reflects Patel’s mission/framing (“civilizational transition”, “Information Era”, “colonisation of the mind”, “sovereignty”), it MUST be attributed:
	- “Patel has argued that …” / “Patel has described his work as …” / “In [source], Patel stated …”
	- If it reflects a third-party evaluation, it MUST be attributed:
	- “[Outlet/author] described Patel as …”

	3) RAW SUPPORT: ALWAYS INCLUDE A VERBATIM SNIPPET
	- "raw_snippet" must be copied verbatim from the source content.
	- Its purpose is to provide additional context around the Wiki sentence in order to give it more meaning and more bbackground.
	- Do not change wording.

	4) MULTI-FACT EXTRACTION FROM ONE CHUNK
	If one paragraph contains multiple extractable facts, output multiple fact objects.
	Example:
	Source chunk: “He founded X in 2018… advises governments… authored *Book* (2021)…”
	→ Output 3 facts:
	- founding/date (CAREER)
	- org description (CAREER; attributed if primary)
	- publication (WORKS)

	5) SECTION ASSIGNMENT RULES
	- LEDE: identity + 1–3 strongest notability anchors only (top roles, signature works, major awards, quotes or feedback or reviews or opinions from other famous individuals).
	- EARLY: birth/education/early background (avoid private trivia).
	- CAREER: roles/timeline, orgs founded/led, advisory roles, major projects.
	- IDEAS: views, frameworks, predictions (always attributed).
	- WORKS: books/reports/articles (bibliographic), reviews / opinions from others thereof and critical reception.
	- HONORS: awards/recognition (name + year).
	- PHIL: philanthropy/donations/initiatives (verify amounts carefully), charitable work.
	- RECEPTION: independent third-party descriptions/evaluations (attributed).
	- BACKMATTER: official site, major institutional profile pages (only if present).
	- OTHER: unknown classification of information


	QUALITY CHECKS (RUN BEFORE OUTPUT)
	- Every fact has: section, claim_type, wiki_sentence (>=5 words), raw_snippet (>=10 words), source url/title, and timeframe (or unknown).
	- No marketing tone; any mission/positioning language is attributed and belongs in IDEAS or CAREER, not LEDE unless independently covered.
	- IF THE BASE CONTENT DOES NOT MENTION ANY OF THE KEY DEFINING ATTRIBUTES ABOUT THIS ENTITY KETAN PATEL DO NOT INCLUDE THE FACT AND DISREGARD THE SOURCE_ITEM altogether: i.e., worked at Goldman Sachs, KPMG; studied at london School of economics; Chair, force for good and CEO / chairman of Greater Pacific Capital; studied neuroscience; wrote master strategist and is widely regarded as a strategist at the intersection of geopolitics, capital and technology. Basic example: if the source content represents something about a Ketan Patel who is in medicine, or runs a startup, that is not him - disregard it.
	- Output JSON only.
	"""
	return prompt

def parse_json(completion: str) -> dict[str, Any] | None:
	"""
	Parse an LLM completion into a dict.
	Tries multiple strategies to be robust against bad JSON.
	"""
	try:
		parsed = json.loads(completion)
		return parsed
	except:
		m = re.search(r"(\{.*\}|\[.*\])", completion, flags=re.DOTALL)
		candidate = m.group(1) if m else completion

		for attempt in [candidate, re.sub(r",(\s*[\]\}])", r"\1", candidate)]:
			try:
				parsed = json.loads(attempt)
				return parsed
			except json.JSONDecodeError:
				continue
		return None


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_gpt(prompt):
	try:
		# Run the synchronous OpenAI call in an executor to avoid blocking
		loop = asyncio.get_event_loop()
		response = await loop.run_in_executor(
			None,
			lambda: client.responses.create(
				model="gpt-5.2",
				input=prompt
			)
		)
		return response.output_text
	except:
		return None

async def get_facts(source_items):
	prompt = create_fact_prompt(source_items)
	try:
		fact_res = await get_gpt(prompt)
		facts = parse_json(fact_res)
		return facts
	except:
		return {}

async def get_all_facts():
	data = []
	with open("all_res.json", "r") as f:
		data = json.load(f)
	parallel = 24

	# Create chunks based on character limits (3-10 items, max 85k chars)
	chunks = []
	idx = 0

	while idx < len(data):
		current_chunk = []

		# Try to add 3-10 items, respecting the 85k character limit
		while idx < len(data) and len(current_chunk) < 10:
			test_chunk = current_chunk + [data[idx]]
			test_str = json.dumps(test_chunk)

			if len(test_str) < 85000:
				current_chunk.append(data[idx])
				idx += 1
			else:
				# Can't add this item without exceeding limit
				if len(current_chunk) >= 3:
					# We have enough items, break
					break
				elif len(current_chunk) > 0:
					# We have 1-2 items, but can't add more
					# Save what we have and move on
					break
				else:
					# Edge case: single item is >= 85k
					# Add it anyway
					current_chunk.append(data[idx])
					idx += 1
					break

		if current_chunk:
			chunks.append(current_chunk)

	# Lock for file writing
	write_lock = asyncio.Lock()

	# Track progress
	total_chunks = len(chunks)
	total_items = len(data)
	processed_items = 0

	async def process_and_write_chunk(chunk):
		nonlocal processed_items
		result = await get_facts(chunk)

		# Write to facts.jsonl with lock
		async with write_lock:
			loop = asyncio.get_event_loop()
			await loop.run_in_executor(
				None,
				lambda: write_result(result)
			)
			processed_items += len(chunk)
			print(f"Processed {processed_items}/{total_items} items ({len(chunk)} in this batch)")

		return result

	def write_result(result):
		with open("facts3.jsonl", "a") as f:
			if result and result != {} and len(list(result.keys())) and len(result.get("facts", [])):
				f.write(json.dumps(result) + "\n")

	# Process in batches of `parallel` concurrent tasks
	for i in range(0, len(chunks), parallel):
		batch = chunks[i:i+parallel]
		tasks = [process_and_write_chunk(chunk) for chunk in batch]
		await asyncio.gather(*tasks)

	print(f"Completed processing all {total_items} items in {total_chunks} chunks")

if __name__ == "__main__":
	asyncio.run(get_all_facts())
