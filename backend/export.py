from io import BytesIO
from fpdf import FPDF
from typing import List, Dict, Any

class BilingualPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 15)
        self.cell(0, 10, "Antiqua Lens - Bilingual Translation Export", border=0, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
        
    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

def generate_bilingual_pdf(source_text: str, translation_data: Dict[str, Any]) -> bytes:
    """
    Generates a PDF comparing the original source text with its translation.
    NOTE: Complex scripts (Arabic, Tamil) may not render perfectly without TTF font injection.
    """
    pdf = BilingualPDF()
    pdf.add_page()
    
    # We use a built-in font for the backend demo, which covers Latin/Greek well.
    # For full Arabic/Tamil support, TTF fonts like NotoSans must be embedded.
    pdf.set_font("helvetica", size=12)
    
    # Document Metadata
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, f"Language / Script: {translation_data.get('language_detected', 'Unknown')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Confidence Score: {translation_data.get('confidence', 0):.0%}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Original Text Section
    pdf.set_font("helvetica", "B", 12)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 10, "Original Source Text (OCR)", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=11)
    
    # Using multi_cell to handle wrapping. We encode/decode to replace missing chars with '?'
    safe_source = source_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, safe_source, border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Transliteration Section
    translit = translation_data.get("transliteration", "")
    if translit:
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Transliteration", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=11)
        safe_translit = translit.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, safe_translit, border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
    # Readable Translation Section
    readable = translation_data.get("readable_translation", "")
    if readable:
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Fluent Translation", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=11)
        safe_readable = readable.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, safe_readable, border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
    # Literal Translation Section
    literal = translation_data.get("literal_translation", "")
    if literal:
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Literal (Word-for-Word) Translation", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=11)
        safe_literal = literal.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, safe_literal, border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
    # Notes Section
    notes = translation_data.get("translator_notes", [])
    if notes:
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Translator Notes", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=11)
        for i, note in enumerate(notes, 1):
            safe_note = note.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 8, f"{i}. {safe_note}", border=1, new_x="LMARGIN", new_y="NEXT")
    
    return pdf.output()
