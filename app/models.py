"""
Pydantic data models and schemas for NoteMate AI.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=300, description="Title of the note")
    content: str = Field(..., description="Main markdown or plain text note content")
    tags: Optional[str] = Field(default="", description="Comma-separated tags for organization")


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    content: Optional[str] = None
    tags: Optional[str] = None
    summary: Optional[str] = None


class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    tags: str
    summary: Optional[str] = ""
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class SummarizeRequest(BaseModel):
    content: Optional[str] = Field(None, description="Optional custom content to summarize if not from existing note")


class SummarizeResponse(BaseModel):
    summary: str
    key_points: List[str] = []
    important_concepts: List[str] = []
    action_items: List[str] = []
    raw_markdown: str


class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question asked by the user")
    note_id: Optional[int] = None
    context: Optional[str] = None


class AskQuestionResponse(BaseModel):
    answer: str
    source_available: bool = True
    context_title: Optional[str] = None


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    correct_index: int
    explanation: str


class QuizResponse(BaseModel):
    note_id: Optional[int] = None
    note_title: Optional[str] = None
    questions: List[QuizQuestion]


class TranscriptStructureResponse(BaseModel):
    raw_transcript: str
    organized_content: str
    summary: str
    key_points: List[str] = []
    action_items: List[str] = []


class PDFExtractResponse(BaseModel):
    filename: str
    page_count: int
    char_count: int
    extracted_text: str
    is_scanned_or_empty: bool = False
    message: Optional[str] = None


class SettingsPayload(BaseModel):
    ollama_base_url: str = Field(..., description="Ollama API base URL")
    ollama_model: str = Field(..., description="Ollama model tag, e.g. gemma3:1b")


class SystemStatus(BaseModel):
    ollama_reachable: bool
    model_available: bool
    active_model: str
    base_url: str
    available_models: List[str] = []
    stt_available: bool
    stt_model: str
    offline_status: str
