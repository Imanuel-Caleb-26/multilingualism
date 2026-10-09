# Antiqua Lens

Antiqua Lens is a full-stack AI-powered application designed for translating and transcribing ancient manuscripts. 

It provides an intuitive UI for researchers to upload manuscript scans, run them through state-of-the-art Optical Character Recognition (OCR) pipelines, and instantly generate scholarly translations and transliterations powered by Google's Gemini LLMs.

### Features
* **Multi-Engine OCR:** Supports fallback mechanisms utilizing Google Gemini Vision and Transkribus HTR+.
* **Line-by-Line Confidence:** Get visual confidence score indicators for transcription fidelity.
* **Intelligent Translation:** Provides Transliteration (IAST/Romanised), Fluent translation, Literal word-for-word translation, and scholarly Translator Notes.
* **Bilingual PDF Export:** Export the transcribed and translated manuscript into a structured bilingual PDF.

---

## 🚀 How to Run the Project

This project uses a **Python (FastAPI)** backend and a **Next.js (React)** frontend. You will need two terminal windows to run the application locally.

### 1. Start the Backend (FastAPI)
The backend handles OCR processing, LLM translation generation, and PDF generation.

1. Open a terminal and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Activate the virtual environment:
   * **Windows:** `venv\Scripts\activate`
   * **Mac/Linux:** `source venv/bin/activate`
3. Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your API Keys:
   * Copy `.env.example` to a new file named `.env`
   * Add your **Google Gemini API Key** (`GOOGLE_API_KEY`)
   * Add your **Transkribus** credentials (`TRANSKRIBUS_USERNAME`, `TRANSKRIBUS_PASSWORD`, and optionally `TRANSKRIBUS_COLLECTION_ID`)
5. Start the server:
   ```bash
   uvicorn main:app --reload
   ```
   *The backend will now be running at `http://localhost:8000`*

### 2. Start the Frontend (Next.js)
The frontend provides the interactive user interface.

1. Open a **second** terminal window and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install the necessary NPM dependencies (if you haven't already):
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   *The frontend will now be running at `http://localhost:3000`*

---

## 🛠️ Usage
1. Open your browser and go to `http://localhost:3000`.
2. Drag and drop a manuscript image (or PDF) into the upload zone.
3. Select your preferred OCR Engine (Auto, Gemini, or Transkribus).
4. Click **Extract Text (OCR)**.
5. Review the transcribed text, edit if necessary, and click **Translate to English**.
6. When finished, you can click **Export Bilingual PDF** to save your work!
