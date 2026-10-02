# NoteMate AI — A Personal AI Note-Taking Assistant

> **Tagline:** *Your thoughts, organized by AI. Your notes, under your control.*  
> Built for the **Hacktoberfest 2026 DEV Challenge — Build for a Friend**.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Gemma_3-orange.svg)](https://ollama.com/)
[![Speech-to-Text](https://img.shields.io/badge/Speech--to--Text-faster--whisper-purple.svg)](https://github.com/SYSTRAN/faster-whisper)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Project Overview

**NoteMate AI** is a lightweight, simple, and functional AI-powered note-taking application designed to capture, organize, summarize, and retrieve knowledge effortlessly.

Rather than being another generic AI chat wrapper, NoteMate AI is engineered as an active cognitive assistant that converts raw thoughts, recorded audio, and PDF documents into clean, structured notes—running **100% locally** using open-weight AI models.

---

## 2. The Problem & Who It Is Built For

### The Friend & The Use Case
This project was built for my friend, who is actively balancing intense study sessions, university lectures, and collaborative team meetings.

### The Pain Points
1. **Scattered Information:** Information arrives in unpredictable formats—spoken audio from lectures, lecture slide PDFs, and messy quick thoughts.
2. **Cognitive Overload:** Manually reading through hour-long transcripts or 40-page PDFs to extract action items and core concepts wastes valuable study time.
3. **Privacy & API Costs:** Commercial AI services charge recurring monthly subscriptions and upload private notes and voice recordings to cloud servers.
4. **Study & Revision Prep:** Preparing flashcards or revision questions from notes requires extensive manual effort.

NoteMate AI solves these problems by providing a unified, local note workspace where open-weight AI does the heavy lifting without sacrificing privacy or paying API fees.

---

## 3. Key Features

### 📝 Feature 1: Note Creation & Organization
- Clean, distraction-free markdown note editor with debounced auto-save.
- Tag-based organization and instant real-time search across titles, content, and tags.
- Persistent local SQLite database in Write-Ahead Logging (WAL) mode for concurrency and zero data loss.

### ✨ Feature 2: AI Note Summarization
- One-click **"Summarize with AI"** powered by local **Gemma 3** (1B or 4B) via Ollama.
- Extracts:
  - **Concise Summary:** High-level executive synthesis.
  - **Key Points:** Bulleted core takeaways.
  - **Important Concepts:** Key terms and vocabulary.
  - **Action Items:** Tasks and next steps.
- Separated from original content (preserves original notes, with one-click "Copy" or "Append to Note").

### 🎙️ Feature 3: Voice-to-Notes (Audio Transcription)
- Upload recordings in `.mp3`, `.wav`, `.m4a`, `.ogg`, or `.webm`.
- High-speed local transcription using `faster-whisper`.
- Multi-stage pipeline: **Audio File → Speech-to-Text → AI Structuring → Clean Notes**.
- Adds readable headings, key points, and action items while strictly avoiding hallucinations.

### 📄 Feature 4: PDF-to-Notes (Document Processing)
- Upload study guides, papers, or lecture slides.
- Text extraction powered by PyMuPDF (`fitz`).
- Automatic detection of scanned/image-only PDFs with clear user warnings.
- Instant conversion of raw PDF text into structured study notes.

### 💬 Feature 5: Ask AI About Your Notes (Strict Q&A)
- Scoped strictly to the active note.
- The AI uses the selected note as its primary source of truth.
- If an answer is not mentioned in the note, the AI explicitly states: *"Based on the provided note, this information is not mentioned."*

### 🧠 Feature 6: AI Revision Quiz Generator
- Generates 5 multiple-choice questions (MCQs) grounded exclusively in the selected note.
- Interactive in-browser quiz mode: select options (A, B, C, D), submit, and receive an instant score with detailed explanations for each answer.

---

## 4. Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                       Browser Web UI                        │
│          (HTML5 / Modern Responsive CSS / Vanilla JS)       │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST / Multipart API
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend (app/)                   │
│                                                             │
│   ┌───────────────┐  ┌──────────────────┐  ┌────────────┐   │
│   │  NoteService  │  │   AudioService   │  │ PDFService │   │
│   │   (CRUD)      │  │ (faster-whisper) │  │ (PyMuPDF)  │   │
│   └───────┬───────┘  └────────┬─────────┘  └─────┬──────┘   │
│           │                   │                  │          │
│           │          ┌────────▼──────────┐       │          │
│           │          │     AIService     │◄──────┘          │
│           │          │  (Ollama Client)  │                  │
│           │          └────────┬──────────┘                  │
└───────────┼───────────────────┼─────────────────────────────┘
            │                   │ HTTP (localhost:11434)
┌───────────▼──────────┐ ┌──────▼─────────────────────────────┐
│  SQLite (data/*.db)  │ │      Ollama Local Inference        │
│  WAL Mode Persistence│ │   (Gemma 3 1B/4B Open-Weight LLM)  │
└──────────────────────┘ └────────────────────────────────────┘
```

---

## 5. Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript | Fast, zero build step, responsive, accessible on any browser |
| **Backend** | Python 3.11+, FastAPI, Uvicorn | High-performance asynchronous API framework |
| **Local LLM** | Gemma 3 (1B or 4B) via Ollama | Lightweight open-weight AI optimized for consumer hardware |
| **Speech-to-Text** | `faster-whisper` (CTranslate2) | 4x faster than vanilla Whisper, runs locally on CPU |
| **PDF Extraction** | PyMuPDF (`pymupdf`) | Fast, accurate text and page layout extraction |
| **Database** | SQLite 3 | Zero-configuration, file-backed, ACID-compliant persistence |
| **Deployment** | Docker & Docker Compose | Consistent reproducible container setup |

---

## 6. Why Open Innovation Matters

NoteMate AI is designed around the principles of open innovation and open-weight AI:

1. **Privacy & Data Sovereignty:**  
   Notes, voice recordings, and academic documents contain personal, proprietary, or sensitive thoughts. By running models locally with Ollama and `faster-whisper`, data never leaves your laptop.
2. **True Accessibility:**  
   Users are not gated by \$20/month cloud subscriptions, credit card requirements, or sudden API rate limits.
3. **Model Flexibility:**  
   Because the backend uses open protocols, you can seamlessly switch between `gemma3:1b`, `gemma3:4b`, `llama3:8b`, or `mistral` by changing one environment variable.
4. **Transparency & Inspectability:**  
   Every prompt template, database table, and extraction script is transparent and inspectable in this repository.

---

## 7. Installation & Quick Start

### Prerequisites
- Python 3.11 or higher
- [Ollama](https://ollama.com/) installed and running
- Git

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/notemate-ai.git
cd notemate-ai
```

### Step 2: Set Up Python Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Pull the Open-Weight AI Model
Make sure Ollama is running, then pull Gemma 3:
```bash
# Pull lightweight 1B model (ideal for standard laptops)
ollama pull gemma3:1b

# Or pull the 4B model (if you have 8GB+ RAM / GPU)
ollama pull gemma3:4b
```

### Step 5: Configure Environment
Copy the example environment file:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Default settings in `.env`:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
DATABASE_URL=sqlite:///./data/notes.db
WHISPER_MODEL_SIZE=tiny
WHISPER_DEVICE=cpu
```

### Step 6: Start the Application
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 8. Docker Deployment

NoteMate AI includes full Docker and Docker Compose support.

```bash
docker-compose up --build
```

The Docker container connects to Ollama running on your host machine via `host.docker.internal` and mounts `./data` for persistent SQLite storage.

---

## 9. Running Tests

NoteMate AI features a comprehensive automated test suite covering note CRUD, persistence, PyMuPDF extraction, audio error handling, and AI parsing:

```bash
python -m pytest -v
```

All 19 test cases verify:
- Note creation, editing, deletion, and tag filtering
- SQLite transactional persistence
- Mocked LLM summary and transcript parsing
- Scanned PDF detection
- Audio format validation and 0-byte error handling

---

## 10. Demo Script for DEV Submission

When recording a 2-minute video walkthrough or writing the DEV submission post:

1. **Introduction (15s):**  
   Introduce NoteMate AI as an open-weight personal note assistant built for Hacktoberfest 2026.
2. **Note Creation & Summarization (30s):**  
   Create a note with sample lecture content on "Docker & Container Architecture". Click **"Summarize with AI"** and showcase the extracted summary, key points, and action items generated by Gemma 3.
3. **Voice-to-Notes (30s):**  
   Upload a recorded voice thought (`.mp3` or `.wav`). Show how `faster-whisper` transcribes the audio and Gemma 3 automatically structures it into headings and next steps.
4. **PDF-to-Notes (20s):**  
   Upload a study guide PDF. Show instant text extraction and structured notes generation.
5. **Interactive Revision Quiz (25s):**  
   Click **"Generate Quiz"**, answer the 5 multiple choice questions, submit, and display the score and explanations.

---

## 11. Real User Feedback (Friend's Testing Experience)

> *This section documents real feedback from my friend after using NoteMate AI for study sessions and lecture notes.*

### Testing Environment
- **Hardware:** Intel Core i7 Laptop (16GB RAM, integrated GPU)
- **Model:** `gemma3:1b` via Ollama
- **Audio sample:** 3-minute lecture recording on Computer Networks

### Friend's Feedback Notes
- **What worked best:**  
  *"The voice-to-notes feature saved me 20 minutes after my morning lecture. Having the audio transcribed and then immediately organized into clean headings made reviewing so much simpler."*
- **Revision Quiz:**  
  *"The 5-question quiz was surprisingly accurate. It tested the exact definitions from the note and helped me check if I actually remembered what I wrote."*
- **Suggestions for improvement:**  
  - Add dark mode toggle for late-night study sessions.
  - Add direct microphone recording button in browser for live voice capture.

---

## 12. Limitations & Offline Capabilities

- **Offline Capability:** Once the Ollama model (`gemma3:1b`) and the `faster-whisper` weights are downloaded on initial setup, the application operates **100% offline** without needing an active internet connection.
- **Hardware Performance:** On CPU-only laptops, `gemma3:1b` takes approximately 3–7 seconds per summary. Larger models (`4B` or `8B`) run faster with Apple Silicon or an NVIDIA GPU.
- **PDF Scanned Documents:** NoteMate AI processes text-based digital PDFs. Image-only scanned PDFs are detected and flagged for the user.

---

## 13. Hacktoberfest 2026 Checklist

- [x] **Built for a real person:** Solves the specific lecture and study note challenge for my friend.
- [x] **Open-weight AI at core:** Uses Google Gemma 3 via Ollama for note intelligence and `faster-whisper` for local speech recognition.
- [x] **No proprietary cloud lock-in:** Does not rely on OpenAI, Claude, or proprietary cloud APIs.
- [x] **Functional MVP:** Note creation, audio transcription, PDF processing, AI Q&A, and interactive quiz generation work end-to-end.
- [x] **Open innovation highlighted:** Privacy, zero subscription costs, model modularity, and transparency documented.
- [x] **Automated test suite:** 19 automated tests passing with Pytest.
- [x] **Docker support:** `Dockerfile` and `docker-compose.yml` included.
- [x] **Documented for DEV:** Includes project overview, architecture diagram, demo script, and installation guide.

---

## 14. License

Distributed under the [MIT License](LICENSE).
