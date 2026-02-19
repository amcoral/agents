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

def create_fact_content_prompt(source_objs):
	prompt = """You are GPT-5.2. You are acting as a “Wikipedia biography source-extraction agent” for a living person (BLP). You DO NOT browse the web in this mode. You must use ONLY the provided page objects (url/title/content) as your evidence corpus.

	MISSION
	Given a list of page objects containing scraped text (e.g., article text, PDF text, YouTube transcript, event page copy), extract an exhaustive set of Wikipedia-relevant *verbatim excerpts* (snippets copied exactly from the provided content) about Ketan Patel. Your output is NOT rewritten facts; it is primarily verbatim excerpts + precise locators so the facts can be structured later.

	CORE POLICIES (NON-NEGOTIABLE)
	- Verifiability: include only what the provided content explicitly says.
	- No original research: do not infer, connect dots, or declare outcomes (e.g., “predictions came true”) unless the provided content explicitly states that.
	- Neutral point of view: you may capture praise/criticism, but only as attributed excerpts; do not add your own evaluative language.
	- BLP safety: avoid private/personal info unless widely published and relevant; do not include addresses, minors’ names, private contacts, etc.
	- Copyright caution: excerpts must be short. Prefer many short excerpts over fewer long ones.

	INPUT
	Use the following:""" + """
	{
	"subject_name": "Ketan Patel",
	"subject_disambiguation_hint": "Chair of Force for Good; founder/CEO Greater Pacific Capital; former Goldman Sachs Strategic Group; author",
	"pages": """ + f"""{source_objs}""" + """
	}

	CRITICAL CONSTRAINTS
	1) Use ONLY the provided pages[]. Do NOT invent facts. Do NOT reference knowledge outside pages[].
	2) If content appears truncated or incomplete, note it in the source metadata and extract only what is present.
	3) If the subject’s identity is ambiguous (multiple Ketan Patels), extract only excerpts that clearly refer to the intended person; otherwise mark as “identity_ambiguous”.

	WHAT TO EXTRACT (COMPREHENSIVE WIKIPEDIA BIO EXCERPT LIBRARY)
	Extract verbatim excerpts for ANY of the following section-types (include everything you find; do not assume something is “obvious”):

	1) Lead-ready identity
	- How the page identifies him (occupation labels, roles, “strategist”, “investor”, etc.)
	- Current notable titles/positions
	- Nationality/citizenship ONLY if explicitly stated

	2) Early life and education
	- Birth date/place ONLY if explicitly stated
	- Upbringing locations ONLY if explicitly stated
	- Education: degrees, institutions, fields, years; professional qualifications/certifications

	3) Career (chronology + mandates)
	- Employment roles, promotions, dates, responsibilities, regions (only if stated)
	- Founding/co-founding: org name + year + role
	- Government advisory/service roles; institutional roles; consulting/advisory engagements (as stated)

	4) Organizations / initiatives / institutional affiliations
	- Force for Good Platform/Initiative: role, mission, outputs (reports), partners, dates
	- Greater Pacific Capital: role, investment thesis, focus areas, research agenda
	- Boards, trusteeships, fellowships, councils, commissions, working groups (org + role + dates)

	5) Publications / works / outputs
	- Books (title, publisher, year), reports, white papers, essays, op-eds, chapters
	- Authorship role, publication date, publisher/outlet

	6) Viewpoints / ideas / frameworks / doctrines
	Extract verbatim excerpts where:
	- Patel articulates positions on geopolitics, technology, capital, sovereignty/agency, security, governance, climate, industrial strategy, AI, inclusion, etc.
	- Named concepts/frameworks/theses
	IMPORTANT: attribute who is speaking (Patel vs narrator vs interviewer vs third party). Do NOT summarize.

	7) Predictions / foresight (high precision)
	Extract verbatim excerpts that contain:
	- The prediction statement itself (what will happen), and the date/context when made (if stated)
	- If and ONLY if explicitly stated in pages[]: validation that it was accurate (“proved correct”, “was borne out”, etc.)
	Rules:
	- Never claim a prediction “came true” unless the content explicitly says so.
	- No validation by your own knowledge. No synthesis.

	8) Reception / influence / legacy (third-party opinions & validation quotes)
	REQUIRED when present:
	- Quotes by credible third parties describing him or his work (praise, assessment, critique)
	- “Leading strategist”, “influential”, etc. ONLY as attributed excerpts, with who said it and context
	- Impact claims ONLY if explicitly stated

	9) Criticism / controversies / disputes (if any)
	- Allegations, criticism, conflicts, disputed claims; outcomes; responses
	- Strictly neutral and attributed

	10) Philanthropy / civic engagement / public service
	- Charitable initiatives, platforms, pro-social programs, public-benefit projects, donations (if stated)

	11) Awards / honors / recognition
	- Awards, honors, rankings, lists (awarder + year + basis, if stated)

	12) Public engagement
	- Keynotes, panels, interviews, major conferences, institutional events (event name + organizer + date if stated)

	13) Notability signals / recurring strategist-page elements
	- Independent profile language, mainstream coverage markers, institutional roles, citation claims (as stated)
	- “Selected works” lists and infobox-style fields

	SOURCE QUALITY & INDEPENDENCE (HEURISTIC, TEXT-ONLY)
	Because you cannot browse, classify each page using only internal cues in the provided content:
	- source_type: “independent secondary”, “independent primary” (interview/transcript), “affiliated/PR/official bio”, “self-published”, “unclear”
	- independence_from_subject: independent / partially affiliated / affiliated / unclear
	- reliability: high / medium / low (brief reasoning based on publisher cues, bylines, editorial tone, presence of press-release language, etc.)
	If uncertain, mark “unclear”.

	EXCERPT EXTRACTION RULES (IMPORTANT)
	- Output should prioritize verbatim excerpts over reformatted facts.
	- Excerpt length: aim 10–40 words; hard cap 50 words per excerpt.
	- Copy EXACT text as printed in content. Preserve capitalization and punctuation.
	- Do NOT paraphrase.
	- Do NOT splice non-contiguous fragments into one excerpt.
	- If you must omit, select a smaller contiguous excerpt rather than using ellipses.
	- De-duplicate: if identical text appears multiple times in the same page, keep once.

	LOCATORS (TEXT-ONLY, REQUIRED)
	Because content is plain text, use these locator rules:
	- Always compute a paragraph index: split content into paragraphs by blank lines. Locator format: "para:<N>".
	- If the content includes headings (lines in ALL CAPS or Markdown-style #/##), include the nearest preceding heading: "heading:'…' para:<N>".
	- If the content resembles a transcript, also include an approximate timestamp if present in text; otherwise include "segment:<N>" where segments are blocks separated by blank lines.
	- If you cannot reliably segment, use character offsets: "chars:<start>-<end>".
	You MUST provide at least one locator form per excerpt.

	WORKFLOW
	Step 1 — For each page, create a source record with metadata inferred from url/title/content.
	Step 2 — Read the full content; harvest excerpts per the category library above.
	Step 3 — De-duplicate and reconcile:
	- If pages disagree (different dates/titles), keep both as separate excerpts and record a conflict entry.
	Step 4 — Output STRICT JSON ONLY (no prose, no markdown).

	OUTPUT JSON SCHEMA (STRICT)
	Return a single JSON object with ONLY these top-level keys:

	{
	"sources": [
		{
		"source_id": "S1",
		"url": "...",
		"title": "...",
		"publisher": "as inferred from url/title/content (or 'unknown')",
		"author": ["..."] ,
		"publication_date": "YYYY-MM-DD|YYYY-MM|YYYY|unknown",
		"content_format": "article|press release|pdf text|video transcript|podcast transcript|event page|other",
		"access_status": "provided_text",
		"source_type": "independent secondary|independent primary|affiliated/PR/official bio|self-published|unclear",
		"independence_from_subject": "independent|partially affiliated|affiliated|unclear",
		"reliability": "high|medium|low",
		"reliability_notes": "1–2 sentences max, based only on cues in content"
		}
	],
	"excerpts": [
		{
		"excerpt_id": "E1",
		"source_id": "S1",
		"category": "Lead|Early life and education|Career|Organizations and initiatives|Publications|Viewpoints|Predictions|Reception|Criticism and controversies|Philanthropy and civic|Awards and honors|Public engagement|Notability signals|Other",
		"subcategory": "optional finer label",
		"speaker": "Ketan Patel|Interviewer|Narrator/Author|Third party (name if stated)|Unknown",
		"stance_if_opinion": "praise|criticism|neutral|unknown",
		"excerpt_text": "VERBATIM TEXT FROM PROVIDED content",
		"entities_mentioned": ["..."],
		"dates_mentioned": ["... (as written or normalized if explicit)"],
		"locator": "heading:'…' para:27 | para:27 | segment:14 | chars:12030-12110",
		"source_quality_flags": {
			"supported_by_independent_secondary": true|false,
			"needs_independent_confirmation": true|false,
			"blp_sensitivity": "low|medium|high",
			"identity_ambiguous": true|false
		},
		"notes": "only if needed (ambiguity, truncation, context limits)"
		}
	],
	"prediction_records": [
		{
		"prediction_id": "P1",
		"prediction_excerpt_id": "E##",
		"prediction_context": "book|report|speech|interview|op-ed|unknown",
		"prediction_date": "YYYY-MM-DD|YYYY-MM|YYYY|unknown",
		"validation": {
			"explicitly_validated_by_provided_text": true|false,
			"validation_excerpt_id": "E##|null"
		},
		"notes": "No synthesis; if not explicitly validated, keep validation false."
		}
	]
	}

	FINAL OUTPUT RULES
	- Output MUST be valid JSON and ONLY JSON.
	- Do not rewrite excerpts into your own words; excerpt_text must be verbatim.
	- Every excerpt must include source_id + locator.
	- Prefer many short, information-dense excerpts.

	Now process the provided pages[] content.
	"""
	return prompt

def create_fact_prompt(sources):
	prompt = f"""
	You are GPT-5.2 with web-browsing enabled. You are acting as a “Wikipedia biography source-extraction agent” for a living person (BLP).

	MISSION
	Given EXACTLY THREE (3) URLs per run about Ketan Patel, open and read each source and extract an exhaustive set of Wikipedia-relevant *verbatim excerpts* (snippets copied exactly from the source) that contain biography-relevant information. Your output is NOT rewritten facts; it is primarily quotes/snippets + metadata so the facts can be structured later.

	CORE POLICIES (NON-NEGOTIABLE)
	- Verifiability: include only what the sources explicitly say.
	- No original research: do not infer, connect dots, or declare outcomes (e.g., “predictions came true”) unless a source explicitly states that.
	- Neutral point of view: you may capture praise/criticism, but only as attributed excerpts; do not add your own evaluative language.
	- BLP safety: avoid private/personal info unless widely published and relevant; do not include addresses, minors’ names, private contacts, etc.
	- Copyright caution: excerpts must be short. Prefer many short excerpts over fewer long ones.

	INPUT URLs:
	{sources}

	BROWSING CONSTRAINTS
	1) Use ONLY the provided URLs as evidence in this run.
	2) You may follow redirects required to access the page, and open transcripts/embedded pages ONLY if they are clearly part of the same source item.
	3) If paywalled/unavailable, record that and extract only accessible metadata/snippets. Never guess missing content.

	WHAT TO EXTRACT (COMPREHENSIVE WIKIPEDIA BIO EXCERPT LIBRARY)
	Extract verbatim excerpts for ANY of the following section-types (include everything you find; do not assume something is “obvious”):

	1) Lead-ready identity
	- How the source identifies him (occupation labels, roles, “strategist”, “investor”, etc.)
	- Current notable titles/positions (chair, founder, CEO, managing director, etc.)
	- Nationality/citizenship ONLY if explicitly stated

	2) Early life and education
	- Birth date/place ONLY if explicitly stated
	- Upbringing locations (London/India etc.) ONLY if explicitly stated
	- Education: degrees, institutions, fields, years; professional qualifications/certifications

	3) Career (chronology + mandates)
	- Employment roles, promotions, dates, responsibilities, coverage regions (only if stated)
	- Major clients/mandates ONLY if explicitly stated
	- Founding/co-founding: org name + year + role
	- Government advisory/service roles; institutional roles; consulting/advisory engagements (as stated)

	4) Organizations / initiatives / institutional affiliations
	- Force for Good Platform/Initiative: role, mission, outputs (reports), partners, dates
	- Greater Pacific Capital: role, investment thesis, focus areas, research agenda
	- Boards, trusteeships, fellowships, councils, commissions, working groups (org + role + dates)
	- Appointments (formal) and memberships/directorships

	5) Publications / works / outputs
	- Books (title, publisher, year), reports, white papers, essays, op-eds, chapters
	- Authorship role (author/co-author/editor), publication date, publisher/outlet
	- Any bibliographic confirmations

	6) Viewpoints / ideas / frameworks / doctrines (key for strategist pages)
	Capture *verbatim excerpts* where:
	- Patel articulates positions on geopolitics, technology, capital, sovereignty/agency, security, governance, climate, industrial strategy, AI, inclusion, etc.
	- Named concepts, frameworks, theses, “strategic intelligence/foresight”, “transition architectures”, etc.
	- IMPORTANT: attribute who is speaking (Patel vs narrator vs interviewer). Do NOT summarize; copy the relevant lines.

	7) Predictions / foresight (high precision)
	Extract *verbatim excerpts* that contain:
	- The prediction statement itself (what will happen), and the date/context when made (if stated)
	- If and ONLY if explicitly stated by a source: an excerpt validating accuracy (“was borne out”, “proved correct”, etc.)
	Rules:
	- Never claim a prediction “came true” unless a source explicitly says so.
	- Do not validate by your own knowledge. No synthesis.

	8) Reception / influence / legacy (third-party opinions & validation quotes)
	This is REQUIRED extraction when present:
	- Quotes by credible third parties describing him or his work (praise, assessment, critique)
	- “Leading strategist”, “influential”, “renowned”, etc. ONLY as attributed excerpts, with who said it and in what context
	- Impact claims (e.g., “helped shape…”, “advised…”) ONLY if stated, and tag whether it’s independent or affiliated

	9) Criticism / controversies / disputes (if any)
	- Allegations, criticism, conflicts, or disputed claims; outcomes; responses
	- Be strictly neutral and fully attributed; avoid sensational detail

	10) Philanthropy / civic engagement / public service
	- Charitable initiatives, platforms, pro-social programs, public-benefit projects, donations (if stated)

	11) Awards / honors / recognition
	- Awards, honors, rankings, lists (who awarded + year + basis, if stated)

	12) Public engagement
	- Keynotes, panels, interviews, testimonies, major conferences, institutional events (event name + organizer + date if stated)

	13) Other recurring strategist-page elements
	Extract excerpts for:
	- “Notability signals”: independent profile pieces, mainstream coverage, academic citations, institutional roles
	- “Selected works” lists
	- Any structured biography sections resembling Wikipedia infobox fields

	SOURCE QUALITY & INDEPENDENCE (WIKIPEDIA RS ORIENTATION)
	For each source, classify:
	- source_type: “independent secondary”, “independent primary” (e.g., interview/transcript), “affiliated/PR/official bio”, “self-published”, “unclear”
	- independence_from_subject: independent / partially affiliated / affiliated / unclear
	- reliability: high / medium / low (brief justification)
	Then, for EACH excerpt, tag:
	- supported_by_independent_secondary: true/false
	- needs_independent_confirmation: true/false (true if only primary/affiliated/self-published supports it)
	- blp_sensitivity: low/medium/high

	EXCERPT EXTRACTION RULES (IMPORTANT)
	- Prioritize “information-dense” snippets (credentials, dates, titles, institutional roles, direct assessments, clearly stated viewpoints).
	- Excerpt length: aim 10–40 words; hard cap 50 words.
	- Copy EXACT text as printed (preserve capitalization and punctuation). Do NOT paraphrase.
	- If you must skip words, do NOT insert ellipses; instead, capture a smaller contiguous excerpt that stands on its own.
	- Always include a precise locator:
	- Articles: paragraph number + section heading
	- PDFs: page number + section/table reference
	- Video/podcast: timestamp
	- Slide decks: slide number
	- De-duplicate: if identical excerpt appears multiple places, keep once with multiple evidence entries.

	WORKFLOW (DO THIS IN ORDER)
	Step 1 — Open each URL; capture bibliographic metadata and access status.
	Step 2 — Read all accessible content; harvest excerpts per the category library above.
	Step 3 — De-duplicate and reconcile:
	- If two sources disagree (e.g., different dates/titles), keep both as separate excerpts and record a conflict entry.
	Step 4 — Output STRICT JSON ONLY (no prose, no markdown).

	OUTPUT JSON SCHEMA (STRICT; NO SUBJECT/RUN METADATA)
	Return a single JSON object with ONLY these top-level keys:
	""" + """
	{
		"sources": [
			{
			"source_id": "S1",
			"url": "...",
			"title": "...",
			"author": ["..."],
			"publisher": "...",
			"publication_date": "YYYY-MM-DD|YYYY-MM|YYYY|unknown",
			"content_format": "article|press release|pdf report|video|podcast|transcript|other",
			"access_status": "ok|partial|paywalled|error",
			"access_notes": "...",
			"source_type": "independent secondary|independent primary|affiliated/PR/official bio|self-published|unclear",
			"independence_from_subject": "independent|partially affiliated|affiliated|unclear",
			"reliability": "high|medium|low",
			"reliability_notes": "1–2 sentences max, factual"
			}
		],
		"excerpts": [
			{
			"excerpt_id": "E1",
			"category": "Lead|Early life and education|Career|Organizations and initiatives|Publications|Viewpoints|Predictions|Reception|Criticism and controversies|Philanthropy and civic|Awards and honors|Public engagement|Notability signals|Other",
			"subcategory": "optional finer label (e.g., 'Goldman Sachs role', 'Force for Good report', 'AI viewpoint', 'Third-party praise')",
			"speaker": "Ketan Patel|Interviewer|Narrator/Author|Third party (name if stated)|Unknown",
			"stance_if_opinion": "praise|criticism|neutral|unknown",
			"excerpt_text": "VERBATIM TEXT FROM SOURCE",
			"entities_mentioned": ["Greater Pacific Capital", "Force for Good", "..."],
			"dates_mentioned": ["YYYY-MM-DD|YYYY-MM|YYYY (as written or normalized if explicit)"],
			"locator": "section 'X' paragraph 7|page 12|timestamp 14:22|slide 5",
			"evidence": [
				{
				"source_id": "S1",
				"quote_snippet": "SAME AS excerpt_text (or shorter if needed)",
				"locator": "repeat locator here if necessary for clarity"
				}
			],
			"source_quality_flags": {
				"supported_by_independent_secondary": true|false,
				"needs_independent_confirmation": true|false,
				"blp_sensitivity": "low|medium|high"
			},
			"notes": "only if needed (ambiguity, identity disambiguation, context limits)"
			}
		],
		"prediction_records": [
			{
			"prediction_id": "P1",
			"prediction_excerpt_id": "E##",
			"prediction_context": "book|report|speech|interview|op-ed|unknown",
			"prediction_date": "YYYY-MM-DD|YYYY-MM|YYYY|unknown",
			"validation": {
				"explicitly_validated_by_source": true|false,
				"validation_excerpt_id": "E##|null"
			},
			"notes": "No synthesis; if not explicitly validated, keep validation false."
			}
		]
	}

	FINAL OUTPUT RULES
	- Output MUST be valid JSON and ONLY JSON.
	- Do not rewrite excerpts into your own words; excerpt_text must be verbatim.
	- Every excerpt must include source_id + locator.
	- If you cannot access a source, still include it in sources[] with access_status and extract only what is visible.
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
	import time
	start_time = time.time()
	try:
		print(f"[{time.strftime('%H:%M:%S')}] Calling GPT API with prompt length: {len(prompt)}")
		# Run the synchronous OpenAI call in an executor to avoid blocking
		loop = asyncio.get_event_loop()

		# Add a 5 minute timeout for processing (reduced from 10 since we're not browsing)
		response = await asyncio.wait_for(
			loop.run_in_executor(
				None,
				lambda: client.responses.create(
					model="gpt-5.2",
					input=prompt
				)
			),
			timeout=300.0  # 5 minutes
		)
		elapsed = time.time() - start_time
		print(f"[{time.strftime('%H:%M:%S')}] Got response from GPT API (took {elapsed:.1f}s)")
		return response.output_text
	except asyncio.TimeoutError:
		elapsed = time.time() - start_time
		print(f"[{time.strftime('%H:%M:%S')}] Timeout: GPT API call took longer than 5 minutes (elapsed: {elapsed:.1f}s)")
		return None
	except Exception as e:
		elapsed = time.time() - start_time
		print(f"[{time.strftime('%H:%M:%S')}] Error in get_gpt after {elapsed:.1f}s: {e}")
		return None

async def get_facts(source_items):
	prompt = create_fact_content_prompt(source_items)
	try:
		fact_res = await get_gpt(prompt)
		if fact_res is None:
			print(f"Warning: get_gpt returned None for chunk")
			return {}
		facts = parse_json(fact_res)
		if facts is None:
			print(f"Warning: parse_json failed to parse response")
			return {}
		return facts
	except Exception as e:
		print(f"Error in get_facts: {e}")
		return {}

async def get_all_facts():
	print("get_all_facts() started")

	# Load the URL list
	print("About to open final_urls.json")
	with open("final_urls.json", "r") as f:
		url_list = json.load(f)
	print(f"Loaded {len(url_list)} URLs from final_urls.json")

	# Load the scraped content files
	print("Loading scraped content files...")
	with open("url_scrapes/all_res.json", "r") as f:
		all_res_data = json.load(f)
	print(f"Loaded {len(all_res_data)} entries from url_scrapes/all_res.json")

	with open("url_scrapes/unique_youtube.json", "r") as f:
		youtube_data = json.load(f)
	print(f"Loaded {len(youtube_data)} entries from url_scrapes/unique_youtube.json")

	# Create lookup dictionaries for fast access
	all_res_lookup = {item["url"]: item for item in all_res_data if "url" in item}
	youtube_lookup = {item["url"]: item for item in youtube_data if "url" in item}
	print(f"Created lookup dictionaries")

	parallel = 24  # Process 10 chunks in parallel (50 URLs at a time)

	# Create chunks of 5 URLs each and look up their content
	chunks = []
	idx = 0

	while idx < len(url_list):
		# Get the next 5 URLs
		url_batch = url_list[idx:idx+5]

		# Look up the content for each URL
		content_batch = []
		for url in url_batch:
			# Determine which lookup to use
			if "youtube" in url.lower():
				content_obj = youtube_lookup.get(url)
			else:
				content_obj = all_res_lookup.get(url)

			if content_obj:
				content_batch.append(content_obj)
			else:
				print(f"Warning: No content found for URL: {url}")

		if content_batch:
			chunks.append(content_batch)
		idx += 5

	print(f"Created {len(chunks)} chunks with content")

	# Lock for file writing
	write_lock = asyncio.Lock()

	# Track progress
	total_chunks = len(chunks)
	total_items = len(url_list)
	processed_items = 0

	async def process_and_write_chunk(chunk, chunk_index):
		nonlocal processed_items
		import time
		start_time = time.time()
		try:
			# Extract URLs for logging
			urls_preview = [item.get("url", "unknown") for item in chunk[:2]]
			print(f"[{time.strftime('%H:%M:%S')}] Chunk {chunk_index}: Starting to process {len(chunk)} content objects: {urls_preview}...")
			result = await get_facts(chunk)
			elapsed = time.time() - start_time
			print(f"[{time.strftime('%H:%M:%S')}] Chunk {chunk_index}: Finished processing after {elapsed:.1f}s, result has {len(result.keys()) if result else 0} keys")

			# Write to facts.jsonl with lock
			async with write_lock:
				loop = asyncio.get_event_loop()
				await loop.run_in_executor(
					None,
					lambda: write_result(result)
				)
				processed_items += len(chunk)
				print(f"[{time.strftime('%H:%M:%S')}] Chunk {chunk_index}: Written. Progress: {processed_items}/{total_items} items")

			return result
		except Exception as e:
			elapsed = time.time() - start_time
			print(f"[{time.strftime('%H:%M:%S')}] Chunk {chunk_index}: Error after {elapsed:.1f}s: {e}")
			processed_items += len(chunk)
			return {}

	def write_result(result):
		with open("final_facts2.jsonl", "a") as f:
			if result and result != {} and len(list(result.keys())) and (len(result.get("excerpts", [])) or len(result.get("sources", []))):
				f.write(json.dumps(result) + "\n")

	# Process in batches of `parallel` concurrent tasks
	import time
	for i in range(0, len(chunks), parallel):
		batch = chunks[i:i+parallel]
		batch_start = time.time()
		print(f"\n[{time.strftime('%H:%M:%S')}] ===== Processing batch {i//parallel + 1}/{(len(chunks) + parallel - 1)//parallel}, with {len(batch)} chunks =====")
		tasks = [process_and_write_chunk(chunk, i+idx) for idx, chunk in enumerate(batch)]
		results = await asyncio.gather(*tasks, return_exceptions=True)

		# Log any exceptions
		for idx, result in enumerate(results):
			if isinstance(result, Exception):
				print(f"[{time.strftime('%H:%M:%S')}] Chunk {i+idx} in batch {i//parallel + 1} failed with: {result}")

		batch_elapsed = time.time() - batch_start
		print(f"[{time.strftime('%H:%M:%S')}] ===== Completed batch {i//parallel + 1} in {batch_elapsed:.1f}s =====\n")

	print(f"Completed processing all {total_items} items in {total_chunks} chunks")

if __name__ == "__main__":
	print("Starting extract.py script...")
	try:
		asyncio.run(get_all_facts())
	except Exception as e:
		print(f"Fatal error: {e}")
		import traceback
		traceback.print_exc()
