import streamlit as st
import json
import re
from typing import Dict, List, Any

# Set page config
st.set_page_config(
    page_title="Wikipedia Page Viewer",
    page_icon="📖",
    layout="wide"
)

# Wikipedia-like CSS styling
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        max-width: 1200px;
        padding-top: 2rem;
    }

    /* Wikipedia-style typography */
    .wiki-title {
        font-family: 'Linux Libertine', 'Georgia', 'Times', serif;
        font-size: 2em;
        line-height: 1.3;
        margin-bottom: 0.25em;
        border-bottom: 1px solid #a2a9b1;
        padding-bottom: 0.2em;
        font-weight: normal;
    }

    .wiki-content {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Lato, Helvetica, Arial, sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: #202122;
    }

    /* Infobox */
    .infobox {
        float: right;
        clear: right;
        width: 300px;
        margin: 0 0 1em 1em;
        padding: 0.2em;
        border: 1px solid #a2a9b1;
        background-color: #f8f9fa;
        font-size: 88%;
        line-height: 1.5;
    }

    .infobox-title {
        font-size: 125%;
        font-weight: bold;
        text-align: center;
        padding: 0.2em;
        background-color: #e1e4e8;
    }

    .infobox-image {
        text-align: center;
        padding: 0.5em 0;
        background-color: #f8f9fa;
    }

    .infobox-image img {
        max-width: 100%;
        height: auto;
        border: 1px solid #a2a9b1;
    }

    .infobox-row {
        padding: 0.2em 0.4em;
        vertical-align: top;
    }

    .infobox-label {
        font-weight: bold;
        width: 40%;
        display: inline-block;
        vertical-align: top;
    }

    .infobox-data {
        display: inline-block;
        width: 58%;
    }

    /* Lead section */
    .lead-section {
        font-size: 14px;
        margin-bottom: 1em;
    }

    /* Section headings */
    .section-heading {
        font-family: 'Linux Libertine', 'Georgia', 'Times', serif;
        font-weight: normal;
        border-bottom: 1px solid #a2a9b1;
        margin-top: 1em;
        margin-bottom: 0.5em;
        overflow: hidden;
    }

    .section-h2 {
        font-size: 1.5em;
        line-height: 1.3;
    }

    .section-h3 {
        font-size: 1.2em;
        line-height: 1.6;
        font-weight: 600;
    }

    /* References */
    .reference {
        font-size: 80%;
        vertical-align: super;
        color: #0645ad;
        text-decoration: none;
    }

    .references-section {
        font-size: 90%;
        margin-top: 2em;
    }

    .reference-item {
        margin-bottom: 0.5em;
        padding-left: 1.6em;
        text-indent: -1.6em;
    }

    /* Links */
    a {
        color: #0645ad;
        text-decoration: none;
    }

    a:hover {
        text-decoration: underline;
    }

    /* External links section */
    .external-links {
        margin-top: 1em;
    }

    .external-link-item {
        margin-bottom: 0.3em;
    }

    /* Quote styling */
    blockquote {
        border-left: 3px solid #a2a9b1;
        padding-left: 1em;
        margin: 1em 0;
        font-style: italic;
        color: #54595d;
    }

    /* Clear float after infobox */
    .clear {
        clear: both;
    }
</style>
""", unsafe_allow_html=True)


def parse_wikitext_to_html(wikitext: str, references: Dict) -> str:
    """Convert simplified wikitext to HTML with references."""
    if not wikitext:
        return ""

    html = wikitext

    # Handle bold text
    html = re.sub(r"'''(.*?)'''", r"<strong>\1</strong>", html)

    # Handle italic text
    html = re.sub(r"''(.*?)''", r"<em>\1</em>", html)

    # Handle internal wiki links [[Link]]
    html = re.sub(r'\[\[([^\]|]+)\]\]', r'<a href="#">\1</a>', html)

    # Handle internal wiki links with display text [[Link|Display]]
    html = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'<a href="#">\2</a>', html)

    # Handle external links
    html = re.sub(r'\[([^\s]+) ([^\]]+)\]', r'<a href="\1" target="_blank">\2</a>', html)

    # Handle citations <ref name="R1">...</ref>
    ref_counter = 1
    ref_mapping = {}

    def replace_ref(match):
        nonlocal ref_counter
        ref_name = match.group(1)
        # Check if group(2) exists (for refs with content)
        ref_content = match.group(2) if match.lastindex >= 2 else ""

        if ref_name not in ref_mapping:
            ref_mapping[ref_name] = ref_counter
            ref_counter += 1

        ref_num = ref_mapping[ref_name]
        return f'<sup class="reference"><a href="#ref{ref_num}">[{ref_num}]</a></sup>'

    # Match <ref name="R1">content</ref>
    html = re.sub(r'<ref\s+name="([^"]+)"[^>]*>(.*?)</ref>', replace_ref, html)

    # Match <ref name="R1"/>
    html = re.sub(r'<ref\s+name="([^"]+)"\s*/>', replace_ref, html)

    # Handle paragraphs (double newline = new paragraph)
    paragraphs = html.split('\n\n')
    html = ''.join(f'<p>{p.strip()}</p>' for p in paragraphs if p.strip())

    return html


def render_infobox_streamlit(infobox: Dict):
    """Render the Wikipedia-style infobox using Streamlit components."""
    if not infobox or not infobox.get('fields'):
        return

    fields = infobox.get('fields', {})

    # Container for infobox styling with border
    st.markdown("""
    <style>
    .infobox-container {
        border: 1px solid #a2a9b1;
        background-color: #f8f9fa;
        padding: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Title
    if fields.get('name'):
        st.markdown(f"### {fields['name']}")

    # Image (biographical profile picture)
    image_url = "https://londonspeakerbureau.com/wp-content/uploads/2020/04/Ketan-Patel-Keynote-Speaker.jpg"
    st.image(image_url, use_container_width=True)

    st.markdown("---")

    # Fields
    field_labels = {
        'birth_date': 'Born',
        'birth_place': 'Birth place',
        'nationality': 'Nationality',
        'occupation': 'Occupation',
        'known_for': 'Known for',
        'alma_mater': 'Alma mater',
        'notable_works': 'Notable work',
        'organization': 'Organization'
    }

    for field_key, label in field_labels.items():
        value = fields.get(field_key)
        if value and value.strip():
            st.markdown(f"**{label}**")
            st.markdown(f"{value}")
            st.markdown("")


def render_section(section: Dict, references: Dict, level: int = 2) -> str:
    """Render a section with its content and subsections."""
    html = ""

    # Section heading
    heading = section.get('heading', '')
    if heading:
        h_class = f"section-h{level}"
        html += f'<div class="section-heading {h_class}"><h{level}>{heading}</h{level}></div>'

    # Section content
    wikitext = section.get('wikitext', '')
    if wikitext:
        html += parse_wikitext_to_html(wikitext, references)

    # Subsections
    subsections = section.get('subsections', [])
    for subsection in subsections:
        html += render_section(subsection, references, level + 1)

    return html


def render_references(references: Dict) -> str:
    """Render the references section."""
    if not references:
        return ""

    html = '<div class="references-section">'
    html += '<h2 class="section-heading section-h2">References</h2>'
    html += '<ol>'

    # Sort references by ref_id
    sorted_refs = sorted(references.items(), key=lambda x: x[0])

    for ref_id, ref_data in sorted_refs:
        citation = ref_data.get('citation_wikitext', '')
        if not citation:
            # Build basic citation
            url = ref_data.get('url', '')
            title = ref_data.get('title', 'Untitled')
            publisher = ref_data.get('publisher', '')
            date = ref_data.get('published_date', '')

            citation = f'"{title}"'
            if publisher:
                citation += f'. {publisher}'
            if date:
                citation += f'. {date}'
            if url:
                citation += f'. <a href="{url}" target="_blank">{url}</a>'

        html += f'<li class="reference-item" id="ref{ref_id}">{citation}</li>'

    html += '</ol>'
    html += '</div>'

    return html


def render_external_links(external_links: List) -> str:
    """Render external links section."""
    if not external_links:
        return ""

    html = '<div class="external-links">'
    html += '<h2 class="section-heading section-h2">External links</h2>'
    html += '<ul>'

    for link in external_links:
        label = link.get('label', '')
        url = link.get('url', '')
        if url:
            html += f'<li class="external-link-item"><a href="{url}" target="_blank">{label or url}</a></li>'

    html += '</ul>'
    html += '</div>'

    return html


def convert_wikitext_to_markdown(wikitext: str) -> str:
    """Convert wikitext to markdown for Streamlit display."""
    if not wikitext:
        return ""

    text = wikitext

    # Handle subsection headings ===Heading=== -> ### Heading
    text = re.sub(r'===([^=]+)===', r'### \1', text)

    # Handle section headings ==Heading== -> ## Heading
    text = re.sub(r'==([^=]+)==', r'## \1', text)

    # Handle bold text
    text = re.sub(r"'''(.*?)'''", r"**\1**", text)

    # Handle italic text
    text = re.sub(r"''(.*?)''", r"*\1*", text)

    # Handle internal wiki links [[Link]] or [[Link|Display]]
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)

    # Handle external links [url text]
    text = re.sub(r'\[([^\s]+) ([^\]]+)\]', r'[\2](\1)', text)

    # Handle citations - convert to superscript links to references section
    # For <ref name="R1">...</ref> and <ref name="R1"/>
    def citation_to_link(match):
        ref_name = match.group(1)
        return f'<sup>[{ref_name}](#ref-{ref_name})</sup>'

    # Apply both patterns - order matters, do full tags before self-closing
    text = re.sub(r'<ref\s+name="([^"]+)"[^>]*>.*?</ref>', citation_to_link, text)
    text = re.sub(r'<ref\s+name="([^"]+)"\s*/>', citation_to_link, text)

    return text


def main():
    # Load the page draft
    try:
        with open("final_page_draft.json", "r") as f:
            page_draft = json.load(f)
    except FileNotFoundError:
        st.error("Could not find final_page_draft.json. Please make sure the file exists.")
        return
    except json.JSONDecodeError:
        st.error("Error parsing final_page_draft.json. Please make sure it's valid JSON.")
        return

    # Display page info in sidebar
    with st.sidebar:
        st.header("Page Information")
        st.write(f"**Version:** {page_draft.get('page_version', 'Unknown')}")
        st.write(f"**Status:** {page_draft.get('status', 'Unknown')}")
        st.write(f"**Last Updated:** {page_draft.get('last_updated_utc', 'Unknown')}")

        # Show statistics
        st.subheader("Statistics")
        references = page_draft.get('references', {})
        st.write(f"📚 References: {len(references)}")

        claim_ledger = page_draft.get('claim_ledger', [])
        st.write(f"📝 Claims: {len(claim_ledger)}")

        quote_bank = page_draft.get('quote_bank', [])
        st.write(f"💬 Quotes: {len(quote_bank)}")

        prediction_bank = page_draft.get('prediction_bank', [])
        st.write(f"🔮 Predictions: {len(prediction_bank)}")

        gaps = page_draft.get('gaps_to_fill', [])
        st.write(f"⚠️ Gaps to Fill: {len(gaps)}")

    # Create two-column layout: content on left, infobox on right
    col_main, col_info = st.columns([7, 3])

    with col_main:
        # Title
        title = page_draft.get('title', 'Untitled')
        st.title(title)

        # Lead section
        lead = page_draft.get('lead', '')
        if isinstance(lead, dict):
            lead_text = lead.get('wikitext', '')
        else:
            lead_text = lead

        if lead_text:
            lead_md = convert_wikitext_to_markdown(lead_text)
            st.markdown(lead_md, unsafe_allow_html=True)
            st.markdown("---")

        # All sections go in the left column
        sections = page_draft.get('sections', [])
        references_dict = page_draft.get('references', {})

        for section in sections:
            heading = section.get('heading', '')
            wikitext = section.get('wikitext', '')

            # Skip references section - we'll handle it separately
            if heading.lower() == 'references':
                continue

            # Display section heading
            if heading:
                st.header(heading)

            # Display section content
            if wikitext:
                section_md = convert_wikitext_to_markdown(wikitext)
                st.markdown(section_md, unsafe_allow_html=True)

            # Display subsections if present
            subsections = section.get('subsections', [])
            for subsection in subsections:
                sub_heading = subsection.get('heading', '')
                sub_wikitext = subsection.get('wikitext', '')

                if sub_heading:
                    st.subheader(sub_heading)

                if sub_wikitext:
                    sub_md = convert_wikitext_to_markdown(sub_wikitext)
                    st.markdown(sub_md, unsafe_allow_html=True)

        # References section
        st.header("References")
        if references_dict:
            st.markdown(f"*{len(references_dict)} references*")
            st.markdown("")

            # Display references with anchor IDs for linking
            for ref_id, ref_data in sorted(references_dict.items()):
                ref_title = ref_data.get('title', 'Untitled')
                url = ref_data.get('url', '')

                # Add anchor ID for this reference
                if url:
                    st.markdown(f'<span id="ref-{ref_id}"></span>**[{ref_id}]** [{ref_title}]({url})', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span id="ref-{ref_id}"></span>**[{ref_id}]** {ref_title}', unsafe_allow_html=True)

        # External links section
        external_links = page_draft.get('external_links', [])
        if external_links:
            st.header("External links")
            for link in external_links:
                label = link.get('label', '')
                url = link.get('url', '')
                if url:
                    st.markdown(f"- [{label or url}]({url})")

    with col_info:
        # Display infobox in right column
        infobox = page_draft.get('infobox', {})
        if infobox:
            render_infobox_streamlit(infobox)

    # Show raw JSON in expander
    with st.expander("🔍 View Raw JSON"):
        st.json(page_draft)


if __name__ == "__main__":
    main()
