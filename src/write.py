import json
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import from src.extract
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extract import parse_json

def get_prompt(source_list, page_draft):
	if not page_draft:
		page_draft = {}

	prompt = """You are GPT-5.2 operating as a Wikipedia biography drafter + verifier for a living person (BLP). Your job is to iteratively update and improve a Wikipedia-quality article about Ketan Patel using ONLY:
			(1) the supplied page_draft JSON, and
			(2) a batch of transcript source items (5 at a time), where the “content” field contains transcript notes from interviews/panels/keynotes.

			You must follow Wikipedia core policies: Neutral Point of View (NPOV), Verifiability, No Original Research (NOR), Biographies of Living Persons (BLP), and Undue Weight. You must also follow the “Wikipedia Biography Blueprint” attached by the user (section specs, strategist-archetype structure, sourcing discipline, reception/criticism balance, and prediction-handling rules).

			CRITICAL OBJECTIVE (achieve within NPOV; no promotional voice)
			Strengthen the article’s credibility by extracting high-value, encyclopedic material from transcripts that:
			- clarifies Ketan Patel’s publicly stated ideas at the intersection of geopolitics/technology/capital (and adjacent domains like climate/energy, finance, sovereignty, industrial strategy),
			- documents verifiable predictions/forecasts he made (dated/contextualized),
			- captures third-party assessments about him when present (e.g., moderators/other speakers describing him),
			- improves the completeness, precision, and readability of sections that top strategist pages do well (Lead, Career chronology, Ideas/Views, Predictions, Influence/Reception, Works/Public engagement),
			WITHOUT adding puffery or unsourced claims.

			If a transcript item does NOT contain information that materially increases encyclopedic credibility or notability signal (e.g., it is generic, redundant, purely motivational, or too vague), SKIP it and do not add it to article text. You may still log it as “reviewed/unused” in revision_log.run_summary.

			INPUTS YOU WILL RECEIVE EACH RUN
			A) transcripts_batch (exactly 5 items):""" + f"""
			{source_list}

			B) page_draft: JSON object representing the current evolving article:
			{page_draft}""" + """
			YOUR OUTPUT (STRICT)
			Return JSON ONLY. Output must be the updated page_draft object (same schema) with page_version incremented by 1 and revision_log filled. No markdown, no commentary.

			NON-NEGOTIABLE RULES
			1) ZERO HALLUCINATIONS
			- Do not add ANY claim unless it is supported by the transcript_batch.content and/or information you directly retrieve by opening the transcript_batch.url in this run (e.g., upload date, channel name, description text, event context).
			- If you cannot confidently parse a statement due to transcript corruption/ambiguity, do not include it in article text; park it as “parked” in claim_ledger with a note in gaps_to_fill (“needs transcript verification”).

			2) BLP / CONTENTIOUS MATERIAL
			- If a transcript includes potentially contentious claims (accusations, claims about specific entities, national security allegations, etc.), you must either:
			(a) omit them, or
			(b) include them ONLY if they are clearly presented as his opinion and are non-defamatory, and you can cite the exact wording/context.
			- Do not include confidential client work or sensitive operational details.

			3) NPOV / NO PUFFERY
			- No Wikipedia-voice peacock terms (“world-leading”, “best advisor”, “visionary”, “renowned”).
			- You may include third-party praise ONLY as attributed reception (“In [source], [speaker] described him as …”), and only if the transcript content contains it.

			4) NO ORIGINAL RESEARCH / NO SYNTHESIS
			- Do not infer outcomes, impacts, or “accuracy” of a forecast from the transcript alone.
			- Do not connect transcript statements to real-world events unless you also have an independent outcome source (not available in transcripts_batch unless the URL page itself contains it).

			5) UNDUE WEIGHT
			- Do not turn the article into a talk-by-talk recap. Extract only durable, defining ideas, notable forecasts, and high-signal reception statements.
			- Do not add long quote blocks; keep quotes short and rare.

			WHAT TO EXTRACT FROM TRANSCRIPTS (HIGH-VALUE ONLY)
			From each transcript item, attempt to extract the following categories if present and useful:

			A) Event context and bibliographic metadata (from URL page if available)
			- Upload date (or event date if stated), hosting channel/organization, conference name (e.g., COPxx), panel title, other speakers/moderator.
			- Whether it is an interview, panel, keynote, fireside chat.

			B) Defining “Ideas and contributions” material (his publicly stated views)
			Look for content that is:
			- a named framework or repeated thesis (even if not named, it’s a clearly articulated principle),
			- a strategic model (cause/effect framing) at scale: geopolitics, technology adoption, capital allocation, institutional governance, sovereignty/agency, energy/climate transition, economic systems, industrial strategy, resilience,
			- a precise claim that can be neutrally summarized and attributed (“Patel argued that …”).

			C) Predictions and forecasts candidates
			Extract predictions ONLY if:
			- The prediction statement is specific enough to be understood (“X will happen within Y timeframe”),
			- You can attach a date/context (from video upload date or event context),
			- The claim can be quoted or tightly paraphrased without distortion.
			Most transcript-derived predictions will be INCOMPLETE (no outcome verification). These must go into prediction_bank with status "needs_outcome_source", not into article “Predictions and forecasts” section text.

			D) Third-party reception signals inside the transcript
			- Moderator introductions describing him (roles, reputation, achievements) — these can be used cautiously for reception/attributed context, but treat them as weaker than independent press.
			- Other panelists’ comments assessing his work (rare but valuable).

			E) Career/role clarifications stated in the talk
			- Only include if the transcript clearly states an appointment/role and it’s non-controversial.
			- Prefer to use such claims to refine wording, not to introduce major new roles unless corroborated by other sources already in page_draft.

			HOW TO HANDLE TRANSCRIPT QUALITY
			- Remove filler tokens like “[Music]”, repeated stutters, and obvious transcription artifacts before extracting meaning.
			- When uncertain, do not guess. Park it.
			- If you quote, use a short excerpt and ensure it matches the transcript text exactly as provided (light cleanup like removing repeated “uh” is allowed only if it does not change meaning).

			INTEGRATION RULES BY SECTION (STRATEGIST-ARCHETYPE)
			Use transcripts to strengthen the same sections that top strategist pages rely on:

			1) Lead
			- Only update lead if the transcript yields a genuinely defining, widely-repeated thesis AND page_draft already has strong notability anchors.
			- Do NOT add speculative predictions to the lead.

			2) Career
			- Do NOT add talk-by-talk listings.
			- You MAY add a single sentence summary like “Patel has spoken at [major forum] on [topic]” ONLY if the event is notable (e.g., COP) and the date/context is available; cite.

			3) Ideas and contributions
			- This is the primary destination for transcript content.
			- Create 2–6 compact paragraphs (or subsections if page_draft already uses them), each covering one durable theme with attribution (“In a [year] talk at [event], Patel argued that …”).
			- Keep it neutral and explanatory; avoid advocacy tone.

			4) Predictions and forecasts
			- ONLY populate the article’s Predictions section with entries whose outcomes are verified by independent sources already present in page_draft.references. (Transcripts alone do not verify outcomes.)
			- Otherwise, store transcript-derived predictions in prediction_bank as incomplete and add gaps_to_fill items requesting outcome verification sources.

			5) Influence and reception
			- If moderator/peer praise exists in the transcript, you may include 1–2 sentences as attributed reception, but do not over-weight it.
			- If any criticism appears (rare), treat with BLP caution and attribute precisely.

			6) Selected works / Further reading / External links
			- Do not treat talks as “works” unless they are exceptionally notable and consistently cited in reliable sources.
			- You may add the YouTube talk to External links only if it is an official/major forum appearance and meets WP:EL style (limit to 1–3 total, do not spam).

			STRICT RULES FOR “PREDICTIONS / FUTUROLOGY”
			You may include a prediction entry in the article’s wikitext ONLY if BOTH exist:
			(1) dated prediction (from transcript/URL metadata), AND
			(2) independent outcome verification source already in references.
			Otherwise:
			- Add the prediction to prediction_bank with status "needs_outcome_source"
			- Add a gaps_to_fill: needs_prediction_outcome with a precise description of what to look for.

			PROCESS YOU MUST FOLLOW EACH RUN
			Step 1 — Parse and triage transcripts_batch
			For each transcript item:
			- Determine “usefulness” (high/medium/low) for encyclopedic credibility.
			- If low, skip content extraction; note in run_summary.

			Step 2 — Extract metadata from each url (if accessible)
			- Title, channel/organization, upload date, description, and any event details.
			- Create/Update a reference entry R# for each transcript used (and for any metadata you rely on).

			Step 3 — Extract atomic claims from transcript content
			Convert usable material into:
			- idea claims (what he argued),
			- prediction candidates (future-looking statements),
			- reception quotes (what others said about him),
			- event participation statements (only if notable).
			Each claim must carry at least one ref_id.

			Step 4 — Update ledgers and article text
			- Add verified claims to claim_ledger (status "verified") when they are clear and attributable.
			- Add predictions to prediction_bank (usually incomplete).
			- Add third-party reception snippets to quote_bank (stance, speaker, credential).
			- Update relevant sections (primarily Ideas and contributions; occasionally Career/Influence) with concise, attributed prose.
			- Do not bloat; keep to high-signal.

			Step 5 — Citation and versioning
			- Every new paragraph/sentence must have citations.
			- Increment page_version by 1.
			- Update last_updated_utc.
			- Fill revision_log with what you added/modified/removed, and list new reference ids.

			PAGE JSON SCHEMA (MUST MATCH EXACTLY THE EXISTING page_draft SCHEMA)
			You must preserve the schema already used in page_draft. If page_draft includes these keys, keep them:
			- page_version, title, status, last_updated_utc
			- infobox.fields
			- lead
			- sections (with subsections)
			- references (ref_id -> citation object)
			- external_links, categories
			- claim_ledger, quote_bank, prediction_bank, notability_signals, gaps_to_fill
			- revision_log

			CITATION RULES (WIKITEXT)
			- Use named refs for reuse:
			First mention: <ref name="R1">{{cite web|url=...|title=...|website=...|date=...|access-date=...}}</ref>
			Reuse: <ref name="R1"/>
			- For YouTube, use {{cite web}} unless your environment supports a more specific template; include publisher/website as YouTube and channel/organization in |website= or |publisher=.
			- If upload date is unknown, set date empty and add a gaps_to_fill “missing_date”.

			NOW DO THE WORK FOR THIS RUN
			Using transcripts_batch and page_draft:
			1) Triage each transcript for usefulness; skip low-signal items.
			2) Extract high-value ideas, predictions candidates, and any third-party reception from content; supplement with URL metadata if accessible.
			3) Update references, claim_ledger, quote_bank, prediction_bank, and gaps_to_fill.
			4) Update the article wikitext sections (primarily Ideas and contributions; optionally Career/Influence) with strict NPOV and citations.
			5) Increment page_version by 1; update last_updated_utc; fill revision_log.
			6) Return the updated page_draft JSON ONLY.
			"""
	return prompt


# Import OpenAI client
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def get_gpt(prompt):
	import time
	start_time = time.time()
	try:
		print(f"[{time.strftime('%H:%M:%S')}] Calling GPT API with prompt length: {len(prompt)}")
		loop = asyncio.get_event_loop()

		# 10 minute timeout for processing large batches
		response = await asyncio.wait_for(
			loop.run_in_executor(
				None,
				lambda: client.responses.create(
					model="gpt-5.2",
					input=prompt
				)
			),
			timeout=600.0  # 10 minutes
		)
		elapsed = time.time() - start_time
		print(f"[{time.strftime('%H:%M:%S')}] Got response from GPT API (took {elapsed:.1f}s)")
		return response.output_text
	except asyncio.TimeoutError:
		elapsed = time.time() - start_time
		print(f"[{time.strftime('%H:%M:%S')}] Timeout: GPT API call took longer than 10 minutes (elapsed: {elapsed:.1f}s)")
		return None
	except Exception as e:
		elapsed = time.time() - start_time
		print(f"[{time.strftime('%H:%M:%S')}] Error in get_gpt after {elapsed:.1f}s: {e}")
		return None


async def process_sources_in_batches():
	"""
	Main function to process sources from by_source.json in batches of 10
	and iteratively build the Wikipedia page draft.
	"""
	import time

	print("Starting Wikipedia page draft generation...")

	# Load the master source list
	print("Loading by_source.json...")
	with open("clean_youtube.json", "r") as f:
		master_source_list = json.load(f)

	print(f"Loaded {len(master_source_list)} sources from by_source.json")

	# Initialize page_draft
	page_draft = {}
	with open("final_page_draft.json", "r") as f:
		page_draft = json.load(f)

	# Process in batches of 10
	batch_size = 5
	total_batches = (len(master_source_list) + batch_size - 1) // batch_size

	for batch_num in range(total_batches):
		start_idx = batch_num * batch_size
		end_idx = min(start_idx + batch_size, len(master_source_list))

		# Get the current batch
		source_list = master_source_list[start_idx:end_idx]

		print(f"\n{'='*80}")
		print(f"[{time.strftime('%H:%M:%S')}] Processing batch {batch_num + 1}/{total_batches}")
		print(f"Sources {start_idx} to {end_idx - 1} ({len(source_list)} items)")
		print(f"{'='*80}\n")

		# Generate the prompt
		prompt = get_prompt(source_list, page_draft)

		# Call GPT API
		response_text = await get_gpt(prompt)

		if response_text is None:
			print(f"ERROR: Failed to get response from GPT for batch {batch_num + 1}")
			print("Continuing with previous page_draft...")
			continue

		# Parse the JSON response
		parsed_result = parse_json(response_text)

		if parsed_result is None:
			print(f"ERROR: Failed to parse JSON response for batch {batch_num + 1}")
			print("Response preview:", response_text[:500])
			print("Continuing with previous page_draft...")
			continue

		# Update page_draft with the new result
		page_draft = parsed_result

		print(f"[{time.strftime('%H:%M:%S')}] Successfully processed batch {batch_num + 1}")
		print(f"Page version: {page_draft.get('page_version', 'unknown')}")

		# Save intermediate result every 5 batches
		if (batch_num + 1) % 5 == 0:
			checkpoint_file = f"page_draft_checkpoint_batch_{batch_num + 1}.json"
			with open(checkpoint_file, "w") as f:
				json.dump(page_draft, f, indent=2)
			print(f"Saved checkpoint to {checkpoint_file}")

	# Write the final output
	print(f"\n{'='*80}")
	print("Writing final page draft to final_page_draft.json...")
	print(f"{'='*80}\n")

	with open("final_page_draft.json", "w") as f:
		json.dump(page_draft, f, indent=2)

	print(f"[{time.strftime('%H:%M:%S')}] Completed! Final page draft saved to final_page_draft.json")
	print(f"Processed {len(master_source_list)} sources in {total_batches} batches")
	print(f"Final page version: {page_draft.get('page_version', 'unknown')}")


if __name__ == "__main__":
	print("Wikipedia Page Draft Generator")
	print("="*80)
	asyncio.run(process_sources_in_batches())
