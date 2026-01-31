import streamlit as st
import tempfile
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.pdf_translator import translate_pdf

# Page configuration
st.set_page_config(
    page_title="PDF Translator",
    page_icon="📄",
    layout="centered"
)

# Title and description
st.title("PDF Translator 📄 → 🌍 → 🇬🇧")
st.markdown("""
Upload a PDF in any language and get it translated to English while preserving the original formatting.
""")

# Initialize session state
if 'translated_file' not in st.session_state:
    st.session_state.translated_file = None
if 'original_filename' not in st.session_state:
    st.session_state.original_filename = None

# File uploader
uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=['pdf'],
    help="Upload a PDF file in any language to translate it to English"
)

# Translate button (only enabled when file is uploaded)
translate_button = st.button(
    "Translate",
    disabled=(uploaded_file is None),
    type="primary",
    use_container_width=True
)

# Process translation when button is clicked
if translate_button and uploaded_file is not None:
    # Create temporary files for input and output
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_input:
        tmp_input.write(uploaded_file.read())
        tmp_input_path = tmp_input.name

    # Create output path
    tmp_output_path = tmp_input_path.replace('.pdf', '_translated.pdf')

    try:
        # Show loading spinner
        with st.spinner('Translating your PDF... This may take a few moments.'):
            # Translate the PDF
            output_path = translate_pdf(tmp_input_path, tmp_output_path)

            # Verify the file was created and is different from input
            if not os.path.exists(output_path):
                raise Exception(f"Output file was not created: {output_path}")

            input_size = os.path.getsize(tmp_input_path)
            output_size = os.path.getsize(output_path)

            # Read the translated file
            with open(output_path, 'rb') as f:
                translated_pdf_bytes = f.read()

            # Store in session state
            st.session_state.translated_file = translated_pdf_bytes
            st.session_state.original_filename = uploaded_file.name

        # Clean up temporary files
        os.unlink(tmp_input_path)
        if os.path.exists(tmp_output_path):
            os.unlink(tmp_output_path)

        st.success(f"✅ Translation complete! ({output_size:,} bytes)")

    except Exception as e:
        st.error(f"An error occurred during translation: {str(e)}")
        # Clean up on error
        if os.path.exists(tmp_input_path):
            os.unlink(tmp_input_path)
        if os.path.exists(tmp_output_path):
            os.unlink(tmp_output_path)

# Display download button if translation is complete
if st.session_state.translated_file is not None and st.session_state.original_filename is not None:
    # Create download filename
    original_name = Path(st.session_state.original_filename).stem
    download_filename = f"{original_name}_translated.pdf"

    st.divider()
    st.subheader("Download Your Translated PDF")

    st.download_button(
        label="📥 Download Translated PDF",
        data=st.session_state.translated_file,
        file_name=download_filename,
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

    st.info("Right-click the download button to save the file to your computer.")

    # Reset button
    if st.button("Translate Another PDF", use_container_width=True):
        st.session_state.translated_file = None
        st.session_state.original_filename = None
        st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
    Powered by PyMuPDF and DeepL API
</div>
""", unsafe_allow_html=True)
