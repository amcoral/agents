# PDF Translator Application

A Streamlit-based application that translates PDF files from any language to English while preserving the original formatting.

## Features

- Upload PDF files in any language
- Automatic translation to English using DeepL API
- Preserves original PDF formatting, structure, and layout
- Download the translated PDF with a single click
- Simple and intuitive user interface

## Architecture

### Files

1. **[app.py](app.py)** - Main Streamlit application
   - Simple UI with file upload
   - "Translate" button (activated when file is uploaded)
   - Loading indicator during translation
   - Download link for translated PDF

2. **[src/pdf_translator.py](src/pdf_translator.py)** - PDF processing module
   - Uses PyMuPDF to iterate through xref objects
   - Extracts text from each PDF element
   - Translates text using DeepL API (via [src/utils/deepl_cmds.py](src/utils/deepl_cmds.py))
   - Reconstructs PDF with translated text while maintaining formatting

3. **[src/utils/deepl_cmds.py](src/utils/deepl_cmds.py)** - DeepL API integration
   - Handles translation API calls
   - Returns translated text and detected source language

## Setup

1. Make sure your `.env` file contains your DeepL API key:
   ```
   DEEPL_API_KEY=your_api_key_here
   ```

2. Install dependencies (already done):
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Running the Application

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

3. Open your browser to the URL shown (typically http://localhost:8501)

4. Upload a PDF and click "Translate"

5. Download your translated PDF

## How It Works

1. User uploads a PDF file through the Streamlit interface
2. The file is saved to a temporary location
3. `translate_pdf()` function processes the PDF:
   - Opens the PDF with PyMuPDF (fitz)
   - Iterates through each page
   - Extracts individual text spans with their bbox, font size, and color
   - Combines all spans from a page using separator tokens (` ⟨SEP⟩ `)
   - **Translates entire page at once** (one API call per page)
   - Removes all separator artifacts from translated output
   - Splits translated text back to individual pieces
   - Covers original text spans with white rectangles
   - Inserts each translated piece at its original position with original font size and color
4. Saves the translated PDF to a new file
5. User can download the translated PDF

### Translation Strategy

The application attempts to preserve the original PDF layout by:
- Processing text span-by-span to maintain precise positioning
- Collecting all spans from a page and translating them together (one API call per page)
- Using separator tokens (` ⟨SEP⟩ `) to batch spans, then removing all separator artifacts from output
- Maintaining the exact position, font size, and color of each text span
- Fallback to proportional distribution if separator-based splitting fails

**How it works:**
1. Extract all individual text spans from a page with their bbox, font size, and color
2. Combine spans with separator token: `span1 ⟨SEP⟩ span2 ⟨SEP⟩ span3...`
3. Send combined text to DeepL API for translation
4. **Clean all separator variations** (`·SEP·`, `⟨SEP⟩`, etc.) from translated output
5. Split cleaned text back to individual pieces
6. Place each translated piece at its original position with original formatting

**Limitations:**
- Original fonts cannot be perfectly replicated (uses Helvetica)
- Text length changes may cause text to extend beyond original boundaries
- Complex layouts (tables, multi-column) may not be perfectly preserved
- Images and non-text elements are not translated

## Deployment to Streamlit Community Cloud

### Prerequisites
- GitHub repository (already set up)
- DeepL API key

### Steps to Deploy

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub

2. Click "New app" and select:
   - Repository: `andybry/agents`
   - Branch: `master`
   - Main file path: `app.py`

3. Click "Advanced settings" and add your secrets:
   ```toml
   DEEPL_API_KEY = "your_deepl_api_key_here"
   ```

4. Click "Deploy"

Your app will be live at: `https://share.streamlit.io/andybry/agents/master/app.py`

### Managing Secrets

After deployment, you can update secrets from:
- App menu → Settings → Secrets

## Technical Details

- **PyMuPDF (fitz)**: Used for PDF manipulation and text extraction
- **DeepL API**: Provides high-quality translation
- **Streamlit**: Powers the web interface
- **Session State**: Maintains translated file in memory for download
