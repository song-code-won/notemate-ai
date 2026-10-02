"""
NoteMate AI — FastAPI Main Application
Tagline: Your thoughts, organized by AI. Your notes, under your control.
Hacktoberfest 2026 DEV Challenge — Build for a Friend.
"""

import os
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.database import init_db
from app.models import (
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    SummarizeRequest,
    SummarizeResponse,
    AskQuestionRequest,
    AskQuestionResponse,
    QuizResponse,
    TranscriptStructureResponse,
    PDFExtractResponse,
    SettingsPayload,
    SystemStatus,
)
from app.services.note_service import NoteService
from app.services.ai_service import ai_service
from app.services.audio_service import audio_service, SUPPORTED_AUDIO_EXTENSIONS
from app.services.pdf_service import pdf_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database on startup
    init_db()
    os.makedirs(os.path.join("app", "uploads"), exist_ok=True)
    os.makedirs("data", exist_ok=True)
    yield


app = FastAPI(
    title="NoteMate AI",
    description="A Personal AI Note-Taking Assistant powered by local open-weight AI (Gemma 3 & faster-whisper)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# System & Health Endpoints
# -------------------------------------------------------------

@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """Check connectivity to Ollama and status of local open-weight AI models."""
    health = await ai_service.check_health()
    stt_status = True
    try:
        import faster_whisper  # noqa
    except ImportError:
        stt_status = False

    offline_status = (
        "100% Local Inference — All notes, speech transcription, and AI generation "
        "run entirely on your machine. No external cloud APIs are called."
    )

    return SystemStatus(
        ollama_reachable=health["ollama_reachable"],
        model_available=health["model_available"],
        active_model=health["active_model"],
        base_url=health["base_url"],
        available_models=health.get("available_models", []),
        stt_available=stt_status,
        stt_model=f"faster-whisper ({audio_service.model_size})",
        offline_status=offline_status,
    )


@app.post("/api/settings", response_model=SystemStatus)
async def update_settings(payload: SettingsPayload):
    """Update Ollama base URL and model name at runtime."""
    ai_service.update_config(payload.ollama_base_url, payload.ollama_model)
    return await get_system_status()


# -------------------------------------------------------------
# Notes CRUD Endpoints
# -------------------------------------------------------------

@app.get("/api/notes", response_model=List[NoteResponse])
def get_notes(
    q: Optional[str] = Query(None, description="Search query in title, content, or tags"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
):
    """List notes with optional search or tag filtering."""
    return NoteService.list_notes(search_query=q, tag=tag)


@app.post("/api/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(note: NoteCreate):
    """Create a new note."""
    return NoteService.create_note(note)


@app.get("/api/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int):
    """Get a single note by ID."""
    note = NoteService.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.put("/api/notes/{note_id}", response_model=NoteResponse)
def update_note(note_id: int, note: NoteUpdate):
    """Update an existing note."""
    updated = NoteService.update_note(note_id, note)
    if not updated:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated


@app.delete("/api/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int):
    """Delete a note by ID."""
    success = NoteService.delete_note(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    return None


# -------------------------------------------------------------
# AI Operations on Notes
# -------------------------------------------------------------

@app.post("/api/notes/{note_id}/summarize", response_model=SummarizeResponse)
async def summarize_note_endpoint(note_id: int, request: Optional[SummarizeRequest] = None):
    """
    Summarize a note using Gemma 3 via Ollama.
    Returns concise summary, key points, important concepts, and action items.
    """
    note = NoteService.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    content_to_summarize = (request.content if request and request.content else note.content)
    if not content_to_summarize.strip():
        raise HTTPException(status_code=400, detail="Note content is empty. Cannot summarize.")

    try:
        summary_result = await ai_service.summarize_note(content_to_summarize)
        # Store summary in note model for fast subsequent viewing
        NoteService.update_note(note_id, NoteUpdate(summary=summary_result.raw_markdown))
        return summary_result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI Summarization failed: {str(e)}")


@app.post("/api/notes/{note_id}/ask", response_model=AskQuestionResponse)
async def ask_note_question_endpoint(note_id: int, request: AskQuestionRequest):
    """
    Ask AI a question strictly based on the content of the selected note.
    If the answer is not in the note, the AI will explicitly say so.
    """
    note = NoteService.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        response = await ai_service.ask_question(
            note_content=note.content,
            question=request.question,
            note_title=note.title,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Question answering failed: {str(e)}")


@app.post("/api/notes/{note_id}/quiz", response_model=QuizResponse)
async def generate_note_quiz_endpoint(note_id: int):
    """
    Generate 5 multiple-choice revision questions grounded strictly in the note's content.
    Each question has 4 options, a correct answer, and an explanation.
    """
    note = NoteService.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if not note.content.strip():
        raise HTTPException(status_code=400, detail="Note content is empty. Cannot generate quiz.")

    try:
        quiz = await ai_service.generate_quiz(
            note_content=note.content,
            note_title=note.title,
        )
        quiz.note_id = note.id
        return quiz
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Quiz generation failed: {str(e)}")


# -------------------------------------------------------------
# Standalone AI Processing
# -------------------------------------------------------------

@app.post("/api/ai/summarize", response_model=SummarizeResponse)
async def summarize_custom_text(request: SummarizeRequest):
    """Summarize arbitrary text without saving it first."""
    if not request.content or not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    try:
        return await ai_service.summarize_note(request.content)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Summarization error: {str(e)}")


# -------------------------------------------------------------
# Voice-to-Notes (Audio Transcription & AI Structuring)
# -------------------------------------------------------------

@app.post("/api/audio/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    auto_structure: bool = Form(default=True),
):
    """
    Voice-to-Notes pipeline:
    1. Upload audio recording (WAV, MP3, M4A, etc.)
    2. Transcribe speech using local faster-whisper model
    3. Restructure transcript into organized notes with headings, summary, and action items using Gemma 3
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}",
        )

    content_bytes = await file.read()
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty (0 bytes).")

    try:
        transcription_result = audio_service.transcribe_bytes(content_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")

    raw_text = transcription_result["transcript"]
    if not raw_text.strip():
        return {
            "success": True,
            "raw_transcript": "",
            "organized_content": "",
            "summary": "No spoken words could be recognized in the audio file.",
            "key_points": [],
            "action_items": [],
            "audio_info": transcription_result,
        }

    structured = None
    if auto_structure:
        try:
            structured = await ai_service.restructure_transcript(raw_text)
        except Exception as e:
            # If Ollama is offline, return transcript so user doesn't lose work
            structured = TranscriptStructureResponse(
                raw_transcript=raw_text,
                organized_content=raw_text,
                summary=f"(AI structuring unavailable: {str(e)})",
                key_points=[],
                action_items=[],
            )

    return {
        "success": True,
        "raw_transcript": raw_text,
        "structured": structured.dict() if structured else None,
        "audio_info": transcription_result,
    }


# -------------------------------------------------------------
# PDF-to-Notes
# -------------------------------------------------------------

@app.post("/api/pdf/extract", response_model=PDFExtractResponse)
async def extract_pdf_endpoint(file: UploadFile = File(...)):
    """Extract text from a text-based PDF using PyMuPDF."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF (.pdf).")

    content_bytes = await file.read()
    try:
        return pdf_service.extract_text_from_bytes(content_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF extraction error: {str(e)}")


@app.post("/api/pdf/process")
async def process_pdf_endpoint(
    file: UploadFile = File(...),
    auto_summarize: bool = Form(default=True),
):
    """
    PDF-to-Notes pipeline:
    Extracts text using PyMuPDF, then generates structured notes and summary with Gemma 3.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF (.pdf).")

    content_bytes = await file.read()
    extract_res = pdf_service.extract_text_from_bytes(content_bytes, file.filename)

    if extract_res.is_scanned_or_empty:
        return {
            "extract_result": extract_res.dict(),
            "summary_result": None,
            "message": extract_res.message,
        }

    summary_result = None
    if auto_summarize:
        try:
            summary_result = await ai_service.summarize_note(extract_res.extracted_text)
        except Exception as e:
            summary_result = {"error": f"AI summarization failed: {str(e)}"}

    return {
        "extract_result": extract_res.dict(),
        "summary_result": summary_result.dict() if isinstance(summary_result, SummarizeResponse) else summary_result,
        "message": "PDF text extracted and processed successfully.",
    }


# -------------------------------------------------------------
# Frontend Static Asset Serving
# -------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        {"message": "NoteMate AI API is running. Place index.html into app/static to access web UI."}
    )
