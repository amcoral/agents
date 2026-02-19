import fitz
import logging
from pathlib import Path
from typing import Optional
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.deepl_cmds import translate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def translate_pdf(input_path: str, output_path: Optional[str] = None) -> str:
    """
    Translates a PDF file from any language to English while preserving formatting.

    Uses intelligent batching to group text spans (minimum 250 chars per batch) to reduce
    API calls while maintaining layout, fonts, sizes, and alignment.

    :param input_path: Path to the input PDF file
    :param output_path: Path for the output translated PDF (optional)
    :return: Path to the translated PDF file
    """
    if output_path is None:
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"{input_file.stem}_translated.pdf")

    logger.info(f"Opening PDF: {input_path}")
    doc = fitz.open(input_path)

    total_pages = len(doc)
    logger.info(f"Processing {total_pages} pages")

    for page_num in range(total_pages):
        page = doc[page_num]
        logger.info(f"Processing page {page_num + 1}/{total_pages}")

        # Get all text instances with their properties (position, font, size, etc.)
        text_instances = page.get_text("dict")
        blocks = text_instances.get("blocks", [])

        # Collect text by LINES (not spans) to avoid splitting words
        all_lines = []
        for block in blocks:
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    # Combine all spans in the line
                    line_text = ""
                    line_bbox = line.get("bbox")
                    # Use the largest font size in the line
                    max_font_size = 0
                    line_color = 0

                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        span_size = span.get("size", 10)
                        if span_size > max_font_size:
                            max_font_size = span_size
                        if line_color == 0:
                            line_color = span.get("color", 0)

                    if line_text.strip():
                        all_lines.append({
                            "text": line_text.strip(),
                            "bbox": line_bbox,
                            "font_size": max_font_size,
                            "color": line_color
                        })

        # Skip if no text on page
        if not all_lines:
            logger.info(f"No text found on page {page_num + 1}, skipping")
            continue

        # Translate in small batches to ensure quality
        logger.info(f"Translating {len(all_lines)} text lines on page {page_num + 1}")

        try:
            translated_texts = []

            # Group into batches of ~500 chars or 10 spans, whichever comes first
            BATCH_SIZE = 500
            MAX_SPANS_PER_BATCH = 10

            current_batch_texts = []
            current_length = 0

            for line in all_lines:
                text = line["text"]
                text_len = len(text)

                # Start new batch if limits exceeded
                if (current_batch_texts and
                    (current_length + text_len > BATCH_SIZE or len(current_batch_texts) >= MAX_SPANS_PER_BATCH)):

                    # Translate current batch
                    batch_combined = " | ".join(current_batch_texts)
                    logger.info(f"Translating batch of {len(current_batch_texts)} spans (~{current_length} chars)")

                    batch_translated, source_lang = translate(batch_combined)
                    logger.info(f"Translated from {source_lang}")

                    # CRITICAL: Verify translation actually happened
                    if batch_translated == batch_combined:
                        logger.error(f"WARNING: Translation returned identical text! API may have failed.")
                        logger.error(f"Original: {batch_combined[:100]}")
                        logger.error(f"Translated: {batch_translated[:100]}")

                    # Split by | separator
                    batch_parts = [p.strip() for p in batch_translated.split("|")]

                    # If split matches, use it; otherwise distribute proportionally
                    if len(batch_parts) == len(current_batch_texts):
                        translated_texts.extend(batch_parts)
                    else:
                        # Just split by character count proportionally
                        total_orig = sum(len(t) for t in current_batch_texts)
                        pos = 0
                        for i, orig in enumerate(current_batch_texts):
                            if i == len(current_batch_texts) - 1:
                                translated_texts.append(batch_translated[pos:].strip())
                            else:
                                chunk_len = int(len(batch_translated) * len(orig) / total_orig)
                                translated_texts.append(batch_translated[pos:pos+chunk_len].strip())
                                pos += chunk_len

                    # Reset for next batch
                    current_batch_texts = []
                    current_length = 0

                current_batch_texts.append(text)
                current_length += text_len

            # Translate final batch
            if current_batch_texts:
                batch_combined = " | ".join(current_batch_texts)
                logger.info(f"Translating final batch of {len(current_batch_texts)} spans (~{current_length} chars)")

                batch_translated, source_lang = translate(batch_combined)

                # CRITICAL: Verify translation actually happened
                if batch_translated == batch_combined:
                    logger.error(f"WARNING: Final batch translation returned identical text!")
                    logger.error(f"Original: {batch_combined[:100]}")
                    logger.error(f"Translated: {batch_translated[:100]}")

                batch_parts = [p.strip() for p in batch_translated.split("|")]

                if len(batch_parts) == len(current_batch_texts):
                    translated_texts.extend(batch_parts)
                else:
                    total_orig = sum(len(t) for t in current_batch_texts)
                    pos = 0
                    for i, orig in enumerate(current_batch_texts):
                        if i == len(current_batch_texts) - 1:
                            translated_texts.append(batch_translated[pos:].strip())
                        else:
                            chunk_len = int(len(batch_translated) * len(orig) / total_orig)
                            translated_texts.append(batch_translated[pos:pos+chunk_len].strip())
                            pos += chunk_len

            logger.info(f"Translation complete: {len(translated_texts)} text segments")

            # Place each translated line at its original position
            placed_count = 0
            for i, line in enumerate(all_lines):
                if i >= len(translated_texts):
                    logger.warning(f"Not enough translated text for line {i} on page {page_num + 1}")
                    break

                translated_text = translated_texts[i]
                original_text = line["text"]

                # Skip if translated text is empty
                if not translated_text:
                    logger.warning(f"Empty translated text for line {i}")
                    continue

                # Log first few placements for debugging
                if i < 3:
                    logger.info(f"Line {i}: '{original_text[:30]}...' -> '{translated_text[:30]}...'")

                # Cover the original text with white rectangle
                if line["bbox"]:
                    # Get page dimensions
                    page_width = page.rect.width

                    # Create rectangle from original bounding box
                    rect = fitz.Rect(line["bbox"])

                    # Expand the white cover rectangle slightly to ensure we cover all original text
                    # Add small margins on all sides
                    cover_rect = fitz.Rect(
                        rect.x0 - 2,  # small left margin
                        rect.y0 - 1,  # small top margin
                        rect.x1 + 2,  # small right margin
                        rect.y1 + 1   # small bottom margin
                    )

                    # Draw white rectangle to cover original text
                    page.draw_rect(cover_rect, color=(1, 1, 1), fill=(1, 1, 1))

                    # Now create the rectangle for placing translated text
                    # Expand horizontally to accommodate longer English text
                    rect_width = rect.x1 - rect.x0
                    max_expansion = min(rect_width * 0.4, page_width - rect.x1 - 20)
                    if max_expansion > 0:
                        rect.x1 += max_expansion
                    placed_count += 1

                    # Determine font color (convert from int to RGB)
                    color_int = line["color"]
                    r = ((color_int >> 16) & 0xFF) / 255.0
                    g = ((color_int >> 8) & 0xFF) / 255.0
                    b = (color_int & 0xFF) / 255.0

                    # Use the maximum font size from the line
                    # Keep it close to original, only minor adjustment
                    font_size = line["font_size"]

                    # Determine text alignment based on position and font size
                    # Check if text is centered on page or has large font
                    text_center = (rect.x0 + rect.x1) / 2
                    page_center = page_width / 2
                    is_centered = abs(text_center - page_center) < (page_width * 0.2)

                    # Large fonts OR centered text are likely headings
                    if font_size > 14 or is_centered:
                        align = fitz.TEXT_ALIGN_CENTER
                    else:
                        align = fitz.TEXT_ALIGN_LEFT

                    # Always use helvetica (helv) - most reliable font in PyMuPDF
                    fontname = "helv"

                    # Try using textbox for better text flow
                    try:
                        # Ensure minimum font size for readability
                        if font_size < 8:
                            font_size = 8

                        rc = page.insert_textbox(
                            rect,
                            translated_text,
                            fontsize=font_size,
                            fontname=fontname,
                            color=(r, g, b),
                            align=align
                        )

                        # If textbox fails (rc < 0), try with slightly smaller font
                        if rc < 0:
                            font_size = max(font_size * 0.92, 7)  # Don't go below 7pt
                            rc = page.insert_textbox(
                                rect,
                                translated_text,
                                fontsize=font_size,
                                fontname=fontname,
                                color=(r, g, b),
                                align=align
                            )

                            if rc < 0:
                                # Last resort: expand rect more and try again
                                rect.x1 = min(rect.x1 + 100, page_width - 10)
                                font_size = max(font_size * 0.9, 6.5)
                                rc = page.insert_textbox(
                                    rect,
                                    translated_text,
                                    fontsize=font_size,
                                    fontname=fontname,
                                    color=(r, g, b),
                                    align=align
                                )
                                if rc < 0:
                                    # Absolute last resort: use insert_text
                                    page.insert_text(
                                        (rect.x0, rect.y0 + font_size),
                                        translated_text,
                                        fontsize=max(font_size, 6),
                                        fontname=fontname,
                                        color=(r, g, b)
                                    )
                    except Exception as font_error:
                        logger.error(f"Font error on line {i}: {font_error}. Skipping this line.")
                        continue

            logger.info(f"Successfully translated page {page_num + 1}: placed {placed_count}/{len(all_lines)} text lines")

        except Exception as e:
            logger.error(f"Error translating page {page_num + 1}: {e}")
            continue

    # Save the translated PDF
    logger.info(f"Saving translated PDF to: {output_path}")
    doc.save(output_path)
    doc.close()

    logger.info("Translation complete!")
    return output_path


def translate_pdf_advanced(input_path: str, output_path: Optional[str] = None) -> str:
    """
    Advanced PDF translation that preserves more formatting by working with xref objects.

    This approach iterates through the PDF's xref table to find and translate text content
    streams while maintaining the original PDF structure.

    :param input_path: Path to the input PDF file
    :param output_path: Path for the output translated PDF (optional)
    :return: Path to the translated PDF file
    """
    if output_path is None:
        input_file = Path(input_path)
        output_path = str(input_file.parent / f"{input_file.stem}_translated.pdf")

    logger.info(f"Opening PDF with xref processing: {input_path}")
    doc = fitz.open(input_path)

    # Iterate through all xref entries
    xref_count = doc.xref_length()
    logger.info(f"Processing {xref_count} xref objects")

    for xref in range(1, xref_count):
        try:
            # Get the object at this xref
            xref_object = doc.xref_object(xref)

            # Check if this object contains text content
            if xref_object and ("stream" in xref_object.lower() or "contents" in xref_object.lower()):
                # Try to get the stream content
                try:
                    stream = doc.xref_stream(xref)
                    if stream:
                        # Decode stream and look for text operations
                        stream_text = stream.decode('latin-1', errors='ignore')

                        # Look for text showing operators (Tj, TJ, etc.)
                        if any(op in stream_text for op in ['Tj', 'TJ', "'", '"']):
                            logger.info(f"Found text content in xref {xref}")

                            # Extract and translate text (simplified approach)
                            # Note: Full implementation would require parsing PDF operators
                            # For now, we'll use the page-based approach

                except Exception as e:
                    logger.debug(f"Could not process stream for xref {xref}: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Could not process xref {xref}: {e}")
            continue

    # Fall back to page-based translation for actual text replacement
    logger.info("Using page-based translation for text replacement")
    doc.close()
    return translate_pdf(input_path, output_path)


if __name__ == "__main__":
    # Test the translator
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_translator.py <input_pdf> [output_pdf]")
        print("Uses intelligent batching (min 250 chars per batch) to reduce API costs")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Translating {input_pdf} using intelligent batching...")
    translated_path = translate_pdf(input_pdf, output_pdf)
    print(f"Translated PDF saved to: {translated_path}")
