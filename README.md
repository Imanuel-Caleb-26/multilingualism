# Antiqua Lens

Antiqua Lens is a full-stack AI-powered application designed for translating and transcribing ancient manuscripts. 

It provides an intuitive UI for researchers to upload manuscript scans, run them through state-of-the-art Optical Character Recognition (OCR) pipelines, and instantly generate scholarly translations and transliterations powered by Google's Gemini LLMs.

### Features
* **Multi-Engine OCR:** Supports fallback mechanisms utilizing Google Gemini Vision and Transkribus HTR+.
* **Line-by-Line Confidence:** Get visual confidence score indicators for transcription fidelity.
* **Intelligent Translation:** Provides Transliteration (IAST/Romanised), Fluent translation, Literal word-for-word translation, and scholarly Translator Notes.
* **Bilingual PDF Export:** Export the transcribed and translated manuscript into a structured bilingual PDF.


## 🛠️ Usage
1. Open your browser and go to `http://localhost:3000`.
2. Drag and drop a manuscript image (or PDF) into the upload zone.
3. Select your preferred OCR Engine (Auto, Gemini, or Transkribus).
4. Click **Extract Text (OCR)**.
5. Review the transcribed text, edit if necessary, and click **Translate to English**.
6. When finished, you can click **Export Bilingual PDF** to save your work!
