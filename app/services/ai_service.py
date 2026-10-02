"""
AI Service module for NoteMate AI.
Interfaces with local open-weight models (Gemma 3) via Ollama.
No proprietary cloud AI APIs (OpenAI, Claude, Gemini) are used as core intelligence.
"""

import os
import json
import re
import httpx
from typing import Dict, Any, List, Optional
from app.models import SummarizeResponse, AskQuestionResponse, QuizQuestion, QuizResponse, TranscriptStructureResponse


class AIService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "gemma3:1b")
        self.timeout = 120.0  # Allow adequate time for local CPU/GPU inference

    def update_config(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def check_health(self) -> Dict[str, Any]:
        """Check if Ollama is running and query available models."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    model_found = any(self.model in m or m.startswith(self.model) for m in models)
                    return {
                        "ollama_reachable": True,
                        "model_available": model_found,
                        "available_models": models,
                        "active_model": self.model,
                        "base_url": self.base_url,
                        "error": None,
                    }
                return {
                    "ollama_reachable": False,
                    "model_available": False,
                    "available_models": [],
                    "active_model": self.model,
                    "base_url": self.base_url,
                    "error": f"Ollama returned HTTP status {res.status_code}",
                }
        except Exception as e:
            return {
                "ollama_reachable": False,
                "model_available": False,
                "available_models": [],
                "active_model": self.model,
                "base_url": self.base_url,
                "error": (
                    f"Cannot reach Ollama at {self.base_url}. "
                    "Make sure Ollama is installed and running (`ollama serve`). "
                    f"Error details: {str(e)}"
                ),
            }

    async def _generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Execute text generation request to local Ollama instance."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("response", "").strip()
                elif res.status_code == 404:
                    raise RuntimeError(
                        f"Model '{self.model}' not found in Ollama. "
                        f"Please run `ollama pull {self.model}` in your terminal."
                    )
                else:
                    raise RuntimeError(
                        f"Ollama returned error HTTP {res.status_code}: {res.text}"
                    )
        except httpx.ConnectError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Please ensure Ollama is running (`ollama serve`) and the model `{self.model}` is available."
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Inference request timed out after {self.timeout}s. "
                "Your local machine might be under heavy load or running a large model on CPU."
            )
        except Exception as e:
            if isinstance(e, (RuntimeError, ConnectionError, TimeoutError)):
                raise e
            raise RuntimeError(f"AI inference error: {str(e)}")

    async def summarize_note(self, content: str) -> SummarizeResponse:
        """Summarize note into structured summary, key points, concepts, and action items."""
        if not content.strip():
            raise ValueError("Note content is empty. Cannot summarize.")

        prompt = f"""You are NoteMate AI, an intelligent personal note-taking assistant.
Analyze the following note content and provide a well-structured summary.

Note Content:
\"\"\"
{content}
\"\"\"

Format your response strictly using these markdown sections:

### Summary
(A concise, well-written paragraph explaining the main topic and core takeaways)

### Key Points
(Bulleted list with '-' of the most important takeaways and details)

### Important Concepts
(Comma-separated or bulleted list of essential keywords, terminology, and concepts)

### Action Items
(Bulleted list with '-' of any tasks, follow-ups, or actionable items mentioned. If none exist, state 'None identified.')
"""
        raw_output = await self._generate(prompt)

        # Parse sections
        summary_text = ""
        key_points = []
        important_concepts = []
        action_items = []

        summary_match = re.search(r"###\s*Summary\s*\n(.*?)(?=###|\Z)", raw_output, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary_text = summary_match.group(1).strip()

        key_points_match = re.search(r"###\s*Key Points\s*\n(.*?)(?=###|\Z)", raw_output, re.DOTALL | re.IGNORECASE)
        if key_points_match:
            lines = [l.strip().lstrip("-*• ") for l in key_points_match.group(1).strip().split("\n") if l.strip()]
            key_points = [l for l in lines if l]

        concepts_match = re.search(r"###\s*Important Concepts\s*\n(.*?)(?=###|\Z)", raw_output, re.DOTALL | re.IGNORECASE)
        if concepts_match:
            raw_c = concepts_match.group(1).strip()
            if "," in raw_c and "\n" not in raw_c:
                important_concepts = [c.strip() for c in raw_c.split(",") if c.strip()]
            else:
                lines = [l.strip().lstrip("-*• ") for l in raw_c.split("\n") if l.strip()]
                important_concepts = [l for l in lines if l]

        actions_match = re.search(r"###\s*Action Items\s*\n(.*?)(?=###|\Z)", raw_output, re.DOTALL | re.IGNORECASE)
        if actions_match:
            lines = [l.strip().lstrip("-*• ") for l in actions_match.group(1).strip().split("\n") if l.strip()]
            action_items = [l for l in lines if l and "none identified" not in l.lower()]

        if not summary_text:
            summary_text = raw_output

        return SummarizeResponse(
            summary=summary_text,
            key_points=key_points,
            important_concepts=important_concepts,
            action_items=action_items,
            raw_markdown=raw_output,
        )

    async def restructure_transcript(self, raw_transcript: str) -> TranscriptStructureResponse:
        """Restructure raw voice transcription into organized notes with headings, summary, and actions."""
        if not raw_transcript.strip():
            raise ValueError("Transcript is empty.")

        prompt = f"""You are NoteMate AI, an intelligent personal note assistant.
A user recorded spoken thoughts, a meeting, or a lecture. Here is the raw speech transcript:

\"\"\"
{raw_transcript}
\"\"\"

Your task:
1. Organize the transcript into clean, readable paragraphs with clear headings.
2. Extract important points.
3. Generate a short summary.
4. Identify any action items or tasks mentioned.

STRICT RULE: Do NOT invent or hallucinate information that was not present in the recording.

Format your output strictly using these sections:

### Organized Notes
(Readable formatted notes with headings and clean paragraphs)

### Summary
(Brief summary of what was discussed)

### Key Points
(Bulleted list with '-' of main points)

### Action Items
(Bulleted list with '-' of tasks or next steps mentioned. If none, state 'None')
"""
        raw_output = await self._generate(prompt)

        organized_notes = ""
        summary = ""
        key_points = []
        action_items = []

        notes_match = re.search(r"###\s*Organized Notes\s*\n(.*?)(?=###|\Z)", raw_output, re.DOTALL | re.IGNORECASE)
        if notes_match:
            organized_notes = notes_match.group(1).strip()
        else:
            organized_notes = raw_output

        summary_match = re.search(r"###\s*Summary\s*\n(.*?)(?=###|\Z)", raw_output, re.DOTALL | re.IGNORECASE)
        if summary_match:
            summary = summary_match.group(1).strip()

        points_match = re.search(r"###\s*Key Points\s*\n(.*?)(?=###|\Z)", raw_output, re.DOTALL | re.IGNORECASE)
        if points_match:
            lines = [l.strip().lstrip("-*• ") for l in points_match.group(1).strip().split("\n") if l.strip()]
            key_points = [l for l in lines if l]

        actions_match = re.search(r"###\s*Action Items\s*\n(.*?)(?=###|\Z)", raw_output, re.DOTALL | re.IGNORECASE)
        if actions_match:
            lines = [l.strip().lstrip("-*• ") for l in actions_match.group(1).strip().split("\n") if l.strip()]
            action_items = [l for l in lines if l and "none" not in l.lower()]

        return TranscriptStructureResponse(
            raw_transcript=raw_transcript,
            organized_content=organized_notes,
            summary=summary,
            key_points=key_points,
            action_items=action_items,
        )

    async def ask_question(self, note_content: str, question: str, note_title: Optional[str] = None) -> AskQuestionResponse:
        """Answer question strictly based on the selected note's content."""
        if not note_content.strip():
            return AskQuestionResponse(
                answer="The selected note has no content to answer questions from.",
                source_available=False,
                context_title=note_title,
            )

        prompt = f"""You are NoteMate AI. You answer user questions strictly based on the provided note.

Note Title: {note_title or 'Untitled Note'}
Note Content:
\"\"\"
{note_content}
\"\"\"

User Question: {question}

STRICT INSTRUCTIONS:
1. Use ONLY the information in the note above to answer.
2. If the answer is NOT mentioned or cannot be inferred directly from the note, respond explicitly:
   "Based on the provided note, this information is not mentioned."
3. Do not speculate or use outside knowledge to invent answers not present in the note.
4. Keep the answer direct, clear, and helpful.
"""
        raw_output = await self._generate(prompt)
        not_mentioned = (
            "not mentioned" in raw_output.lower()
            or "not found in the note" in raw_output.lower()
            or "does not contain" in raw_output.lower()
        )

        return AskQuestionResponse(
            answer=raw_output,
            source_available=not not_mentioned,
            context_title=note_title,
        )

    async def generate_quiz(self, note_content: str, note_title: Optional[str] = None) -> QuizResponse:
        """Generate 5 multiple choice questions grounded strictly in the note content."""
        if not note_content.strip():
            raise ValueError("Note content is empty. Cannot generate quiz.")

        prompt = f"""You are an educational AI assistant for NoteMate AI.
Based ONLY on the note content below, generate 5 multiple-choice questions to test the user's comprehension.

Note Title: {note_title or 'Untitled Note'}
Note Content:
\"\"\"
{note_content}
\"\"\"

STRICT RULES:
1. Generate exactly 5 questions based solely on facts in this note.
2. Each question MUST have exactly 4 choices (A, B, C, D).
3. Specify exactly one correct choice (0 for A, 1 for B, 2 for C, 3 for D).
4. Provide a brief explanation referencing the note.
5. Return the result ONLY as a valid JSON array of objects. Do not write markdown text before or after the JSON.

Expected JSON format:
[
  {{
    "question": "What is ...?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "correct_answer": "Option A",
    "explanation": "According to the note, ..."
  }}
]
"""
        raw_output = await self._generate(prompt)

        # Extract JSON array from output
        json_str = raw_output
        array_match = re.search(r"\[\s*\{.*\}\s*\]", raw_output, re.DOTALL)
        if array_match:
            json_str = array_match.group(0)

        questions: List[QuizQuestion] = []
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                for item in parsed:
                    opts = item.get("options", [])
                    c_idx = int(item.get("correct_index", 0))
                    c_ans = item.get("correct_answer", "")
                    if opts and not c_ans and 0 <= c_idx < len(opts):
                        c_ans = opts[c_idx]
                    questions.append(
                        QuizQuestion(
                            question=item.get("question", ""),
                            options=opts,
                            correct_answer=c_ans,
                            correct_index=c_idx,
                            explanation=item.get("explanation", ""),
                        )
                    )
        except Exception:
            # Fallback regex parsing if model returned loose formatting
            q_blocks = re.findall(r"(?:Question|\d+[\.\)])\s*(.*?)(?=(?:Question|\d+[\.\)]|\Z))", raw_output, re.DOTALL | re.IGNORECASE)
            for idx, block in enumerate(q_blocks[:5]):
                lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
                if not lines:
                    continue
                q_text = lines[0]
                opts = []
                for line in lines[1:]:
                    if re.match(r"^[A-Da-d][\.\)]", line):
                        opts.append(re.sub(r"^[A-Da-d][\.\)]\s*", "", line))
                while len(opts) < 4:
                    opts.append(f"Option {chr(65 + len(opts))}")
                opts = opts[:4]
                questions.append(
                    QuizQuestion(
                        question=q_text,
                        options=opts,
                        correct_answer=opts[0],
                        correct_index=0,
                        explanation="Derived from note concepts.",
                    )
                )

        if not questions:
            raise RuntimeError("The model could not format quiz questions. Please try again.")

        return QuizResponse(
            note_title=note_title,
            questions=questions[:5],
        )


ai_service = AIService()
