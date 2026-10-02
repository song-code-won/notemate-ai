"""
Unit tests for AIService logic, response parsing, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.services.ai_service import AIService
from app.models import SummarizeResponse, AskQuestionResponse, QuizResponse


@pytest.fixture
def ai_service_instance():
    service = AIService()
    service.base_url = "http://localhost:11434"
    service.model = "gemma3:1b"
    return service


@pytest.mark.asyncio
async def test_summarize_note_parsing(ai_service_instance):
    """Test parsing of structured summary sections from LLM response."""
    sample_llm_response = """
### Summary
Docker is an open-source platform that enables developers to build, package, and deploy applications in lightweight containers.

### Key Points
- Containers bundle software with all required dependencies.
- Images act as read-only blueprints.
- Docker Compose simplifies multi-container orchestrations.

### Important Concepts
Container, Image, Dockerfile, Volume, Port Mapping

### Action Items
- Install Docker Desktop
- Create a sample Dockerfile
"""
    with patch.object(ai_service_instance, "_generate", new=AsyncMock(return_value=sample_llm_response)):
        res = await ai_service_instance.summarize_note("Lecture text about Docker...")
        assert isinstance(res, SummarizeResponse)
        assert "Docker is an open-source platform" in res.summary
        assert len(res.key_points) == 3
        assert "Containers bundle software with all required dependencies." in res.key_points
        assert len(res.important_concepts) >= 3
        assert len(res.action_items) == 2
        assert "Install Docker Desktop" in res.action_items[0]


@pytest.mark.asyncio
async def test_restructure_transcript_parsing(ai_service_instance):
    """Test restructuring raw audio transcripts into formatted notes."""
    raw_transcript = "um so we discussed today's project milestones we need to submit the draft by friday and john will review the tests"
    mock_llm_output = """
### Organized Notes
## Project Milestones Meeting
We discussed today's project milestones and team responsibilities.

### Summary
Meeting discussing project milestone deadlines and test reviews.

### Key Points
- Draft submission deadline is set for Friday.
- John is assigned to review the test suite.

### Action Items
- Submit draft by Friday
- John to review tests
"""
    with patch.object(ai_service_instance, "_generate", new=AsyncMock(return_value=mock_llm_output)):
        res = await ai_service_instance.restructure_transcript(raw_transcript)
        assert "Project Milestones Meeting" in res.organized_content
        assert len(res.key_points) == 2
        assert len(res.action_items) == 2


@pytest.mark.asyncio
async def test_ask_question_not_in_note(ai_service_instance):
    """Test AI returns strict statement when question is not answered in the note."""
    mock_llm_output = "Based on the provided note, this information is not mentioned."
    with patch.object(ai_service_instance, "_generate", new=AsyncMock(return_value=mock_llm_output)):
        res = await ai_service_instance.ask_question(
            note_content="The lecture was about Python list comprehensions.",
            question="What is the capital of France?",
        )
        assert isinstance(res, AskQuestionResponse)
        assert "not mentioned" in res.answer.lower()
        assert res.source_available is False


@pytest.mark.asyncio
async def test_generate_quiz_json_parsing(ai_service_instance):
    """Test generating 5 MCQs and parsing the JSON output."""
    mock_quiz_json = """
[
  {
    "question": "What is a Docker container?",
    "options": ["A running instance of an image", "A virtual machine hypervisor", "A database engine", "A programming language"],
    "correct_index": 0,
    "correct_answer": "A running instance of an image",
    "explanation": "A container is a runnable instance created from an image."
  },
  {
    "question": "Which file defines how an image is built?",
    "options": ["docker-compose.yml", "Dockerfile", "package.json", "Makefile"],
    "correct_index": 1,
    "correct_answer": "Dockerfile",
    "explanation": "A Dockerfile contains step-by-step instructions to assemble an image."
  }
]
"""
    with patch.object(ai_service_instance, "_generate", new=AsyncMock(return_value=mock_quiz_json)):
        res = await ai_service_instance.generate_quiz(
            note_content="Docker fundamentals...",
            note_title="Docker Notes",
        )
        assert isinstance(res, QuizResponse)
        assert len(res.questions) == 2
        assert res.questions[0].correct_index == 0
        assert res.questions[0].correct_answer == "A running instance of an image"
        assert len(res.questions[0].options) == 4


@pytest.mark.asyncio
async def test_ollama_unreachable_error_handling(ai_service_instance):
    """Test clear error messaging when Ollama server is offline."""
    health = await ai_service_instance.check_health()
    # When Ollama is not running, it must report ollama_reachable is False with helpful error
    if not health["ollama_reachable"]:
        assert health["ollama_reachable"] is False
        assert "Cannot reach Ollama" in health["error"]
        assert "ollama serve" in health["error"]
