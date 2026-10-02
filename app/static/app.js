/**
 * NoteMate AI — Frontend Application Logic
 * Hacktoberfest 2026 DEV Challenge — Build for a Friend
 */

const state = {
  notes: [],
  activeNoteId: null,
  activeFilter: { query: "", tag: "" },
  systemStatus: null,
  autoSaveTimer: null,
  currentQuizData: null,
  userQuizAnswers: {},
  audioFile: null,
  pdfFile: null,
};

// DOM Elements
const views = {
  dashboard: document.getElementById("viewDashboard"),
  editor: document.getElementById("viewEditor"),
  audio: document.getElementById("viewAudio"),
  pdf: document.getElementById("viewPdf"),
  settings: document.getElementById("viewSettings"),
};

// -------------------------------------------------------------
// VIEW SWITCHING & NAVIGATION
// -------------------------------------------------------------

function switchView(viewName) {
  Object.keys(views).forEach((key) => {
    if (views[key]) {
      views[key].classList.toggle("active", key === viewName);
    }
  });

  // Update nav item active states
  document.querySelectorAll(".nav-item").forEach((btn) => btn.classList.remove("active"));
  if (viewName === "dashboard") {
    document.getElementById("navAllNotes")?.classList.add("active");
  } else if (viewName === "audio") {
    document.getElementById("navAudioUpload")?.classList.add("active");
  } else if (viewName === "pdf") {
    document.getElementById("navPdfUpload")?.classList.add("active");
  } else if (viewName === "settings") {
    document.getElementById("navSettings")?.classList.add("active");
  }
}

// -------------------------------------------------------------
// TOAST NOTIFICATIONS
// -------------------------------------------------------------

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${escapeHtml(message)}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// -------------------------------------------------------------
// SYSTEM STATUS & HEALTH CHECK
// -------------------------------------------------------------

async function checkSystemStatus() {
  const badge = document.getElementById("aiStatusBadge");
  const dot = badge?.querySelector(".status-dot");
  const title = document.getElementById("aiStatusTitle");
  const subtitle = document.getElementById("aiStatusSubtitle");

  try {
    const res = await fetch("/api/status");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.systemStatus = data;

    if (data.ollama_reachable) {
      if (dot) {
        dot.className = "status-dot online";
      }
      if (title) title.textContent = `AI: ${data.active_model}`;
      if (subtitle) subtitle.textContent = data.model_available ? "Model Ready (Ollama)" : "Model not downloaded";
    } else {
      if (dot) {
        dot.className = "status-dot offline";
      }
      if (title) title.textContent = "Local AI Offline";
      if (subtitle) subtitle.textContent = "Start Ollama (ollama serve)";
    }
  } catch (err) {
    if (dot) dot.className = "status-dot offline";
    if (title) title.textContent = "Server Connecting...";
    if (subtitle) subtitle.textContent = "Check backend";
  }
}

// -------------------------------------------------------------
// NOTES MANAGEMENT & API CALLS
// -------------------------------------------------------------

async function fetchNotes() {
  try {
    let url = "/api/notes";
    const params = new URLSearchParams();
    if (state.activeFilter.query) params.append("q", state.activeFilter.query);
    if (state.activeFilter.tag) params.append("tag", state.activeFilter.tag);
    if (params.toString()) url += `?${params.toString()}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load notes");
    const notes = await res.json();
    state.notes = notes;
    renderNotesGrid();
    renderSidebarTags();
    updateNotesCount();
  } catch (err) {
    showToast(`Error loading notes: ${err.message}`, "error");
  }
}

function updateNotesCount() {
  const countBadge = document.getElementById("notesCountBadge");
  if (countBadge) {
    countBadge.textContent = state.notes.length;
  }
}

function renderNotesGrid() {
  const grid = document.getElementById("notesGrid");
  const emptyState = document.getElementById("notesEmptyState");
  const filterBanner = document.getElementById("filterBanner");
  const filterText = document.getElementById("filterText");

  if (!grid) return;

  // Filter banner visibility
  if (state.activeFilter.query || state.activeFilter.tag) {
    filterBanner?.classList.remove("hidden");
    const filterDesc = [
      state.activeFilter.query ? `"${state.activeFilter.query}"` : "",
      state.activeFilter.tag ? `tag: #${state.activeFilter.tag}` : "",
    ].filter(Boolean).join(" & ");
    if (filterText) filterText.textContent = filterDesc;
  } else {
    filterBanner?.classList.add("hidden");
  }

  if (state.notes.length === 0) {
    grid.innerHTML = "";
    emptyState?.classList.remove("hidden");
    return;
  }

  emptyState?.classList.add("hidden");

  grid.innerHTML = state.notes
    .map((note) => {
      const tagsList = note.tags
        ? note.tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean)
        : [];

      const tagsHtml = tagsList
        .map((tag) => `<span class="note-card-tag" onclick="event.stopPropagation(); filterByTag('${escapeHtml(tag)}')">#${escapeHtml(tag)}</span>`)
        .join("");

      const formattedDate = formatDate(note.updated_at);
      const hasSummary = Boolean(note.summary && note.summary.trim());

      return `
        <div class="note-card" onclick="openNoteInEditor(${note.id})">
          <h3 class="note-card-title">${escapeHtml(note.title || "Untitled Note")}</h3>
          <p class="note-card-preview">${escapeHtml(note.content || "Empty note...")}</p>
          ${tagsHtml ? `<div class="note-card-tags">${tagsHtml}</div>` : ""}
          <div class="note-card-footer">
            <span>${formattedDate}</span>
            ${hasSummary ? `<span class="card-has-summary" title="AI summary generated">✨ Summarized</span>` : "<span></span>"}
            <div class="note-card-actions">
              <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); deleteNote(${note.id})" title="Delete Note">
                🗑️
              </button>
            </div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderSidebarTags() {
  const container = document.getElementById("sidebarTagList");
  if (!container) return;

  const tagCounts = {};
  state.notes.forEach((n) => {
    if (n.tags) {
      n.tags.split(",").forEach((raw) => {
        const t = raw.trim();
        if (t) tagCounts[t] = (tagCounts[t] || 0) + 1;
      });
    }
  });

  const uniqueTags = Object.keys(tagCounts).sort();
  if (uniqueTags.length === 0) {
    container.innerHTML = `<small style="color: #64748b;">No tags yet</small>`;
    return;
  }

  container.innerHTML = uniqueTags
    .map(
      (tag) => `
      <span class="tag-pill ${state.activeFilter.tag === tag ? "active" : ""}" onclick="filterByTag('${escapeHtml(tag)}')">
        #${escapeHtml(tag)} <small>(${tagCounts[tag]})</small>
      </span>
    `
    )
    .join("");
}

function formatDate(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoStr;
  }
}

function filterByTag(tag) {
  if (state.activeFilter.tag === tag) {
    state.activeFilter.tag = "";
  } else {
    state.activeFilter.tag = tag;
  }
  fetchNotes();
}

function clearFilters() {
  state.activeFilter.query = "";
  state.activeFilter.tag = "";
  const searchInput = document.getElementById("searchInput");
  if (searchInput) searchInput.value = "";
  document.getElementById("clearSearchBtn")?.classList.add("hidden");
  fetchNotes();
}

// -------------------------------------------------------------
// NOTE EDITOR
// -------------------------------------------------------------

function createNewNote() {
  state.activeNoteId = null;
  const titleInput = document.getElementById("noteTitleInput");
  const tagsInput = document.getElementById("noteTagsInput");
  const contentInput = document.getElementById("noteContentInput");
  const saveIndicator = document.getElementById("saveStatusIndicator");

  if (titleInput) titleInput.value = "";
  if (tagsInput) tagsInput.value = "";
  if (contentInput) contentInput.value = "";
  if (saveIndicator) saveIndicator.textContent = "New Note (Unsaved)";

  resetAIPanels();
  switchView("editor");
  titleInput?.focus();
}

function openNoteInEditor(noteId) {
  const note = state.notes.find((n) => n.id === noteId);
  if (!note) return;

  state.activeNoteId = note.id;
  const titleInput = document.getElementById("noteTitleInput");
  const tagsInput = document.getElementById("noteTagsInput");
  const contentInput = document.getElementById("noteContentInput");
  const saveIndicator = document.getElementById("saveStatusIndicator");

  if (titleInput) titleInput.value = note.title;
  if (tagsInput) tagsInput.value = note.tags;
  if (contentInput) contentInput.value = note.content;
  if (saveIndicator) saveIndicator.textContent = `Saved: ${formatDate(note.updated_at)}`;

  resetAIPanels();

  // If note already has a saved summary, render it
  if (note.summary) {
    renderFormattedSummary({
      summary: note.summary,
      key_points: [],
      important_concepts: [],
      action_items: [],
      raw_markdown: note.summary,
    });
  }

  switchView("editor");
}

async function saveCurrentNote(isAutoSave = false) {
  const titleInput = document.getElementById("noteTitleInput");
  const tagsInput = document.getElementById("noteTagsInput");
  const contentInput = document.getElementById("noteContentInput");
  const saveIndicator = document.getElementById("saveStatusIndicator");

  const title = (titleInput?.value || "").trim() || "Untitled Note";
  const tags = (tagsInput?.value || "").trim();
  const content = contentInput?.value || "";

  if (saveIndicator) saveIndicator.textContent = "Saving...";

  try {
    let res;
    if (state.activeNoteId) {
      // Update existing note
      res = await fetch(`/api/notes/${state.activeNoteId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, tags, content }),
      });
    } else {
      // Create new note
      res = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, tags, content }),
      });
    }

    if (!res.ok) throw new Error(`Save failed with HTTP ${res.status}`);
    const savedNote = await res.json();
    state.activeNoteId = savedNote.id;

    if (saveIndicator) saveIndicator.textContent = `Saved: ${formatDate(savedNote.updated_at)}`;
    if (!isAutoSave) {
      showToast("Note saved successfully", "success");
    }
    fetchNotes();
  } catch (err) {
    if (saveIndicator) saveIndicator.textContent = "Error saving";
    showToast(`Error saving note: ${err.message}`, "error");
  }
}

async function deleteNote(noteId) {
  if (!confirm("Are you sure you want to delete this note?")) return;

  try {
    const res = await fetch(`/api/notes/${noteId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    showToast("Note deleted", "info");

    if (state.activeNoteId === noteId) {
      state.activeNoteId = null;
      switchView("dashboard");
    }
    fetchNotes();
  } catch (err) {
    showToast(`Error deleting note: ${err.message}`, "error");
  }
}

// -------------------------------------------------------------
// AI PANEL LOGIC (SUMMARIZE, QA, QUIZ)
// -------------------------------------------------------------

function resetAIPanels() {
  const summaryBox = document.getElementById("summaryResultsContainer");
  const summaryActions = document.getElementById("summaryActionsBar");
  const qaChat = document.getElementById("qaHistory");
  const quizBox = document.getElementById("quizContainer");

  if (summaryBox) {
    summaryBox.innerHTML = `
      <div class="ai-placeholder">
        Click <strong>"Summarize with AI"</strong> to extract key takeaways, core concepts, and action items with Gemma 3.
      </div>
    `;
  }
  summaryActions?.classList.add("hidden");

  if (qaChat) {
    qaChat.innerHTML = `
      <div class="qa-message bot">
        <div class="qa-bubble">
          Hello! Ask me any question specifically about this note. If the answer isn't in your text, I will explicitly let you know.
        </div>
      </div>
    `;
  }

  if (quizBox) {
    quizBox.innerHTML = `
      <div class="ai-placeholder">
        Click <strong>"Generate Quiz"</strong> to create a 5-question test based on this note.
      </div>
    `;
  }
  state.currentQuizData = null;
  state.userQuizAnswers = {};
}

// AI Tab Switcher
function switchAITab(tabName) {
  const tabs = {
    summary: { btn: document.getElementById("tabBtnSummary"), content: document.getElementById("tabContentSummary") },
    ask: { btn: document.getElementById("tabBtnAsk"), content: document.getElementById("tabContentAsk") },
    quiz: { btn: document.getElementById("tabBtnQuiz"), content: document.getElementById("tabContentQuiz") },
  };

  Object.keys(tabs).forEach((key) => {
    tabs[key].btn?.classList.toggle("active", key === tabName);
    tabs[key].content?.classList.toggle("active", key === tabName);
  });
}

// Feature 2: Summarize with AI
async function triggerSummarize() {
  const contentInput = document.getElementById("noteContentInput");
  const content = (contentInput?.value || "").trim();

  if (!content) {
    showToast("Please enter some note content first before summarizing.", "warning");
    return;
  }

  // Ensure note is saved first
  if (!state.activeNoteId) {
    await saveCurrentNote(true);
  }

  const spinner = document.getElementById("summaryLoadingSpinner");
  const container = document.getElementById("summaryResultsContainer");
  const actionsBar = document.getElementById("summaryActionsBar");

  spinner?.classList.remove("hidden");
  if (container) container.innerHTML = "";

  try {
    const res = await fetch(`/api/notes/${state.activeNoteId}/summarize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    renderFormattedSummary(data);
    actionsBar?.classList.remove("hidden");
    showToast("Summary generated with Gemma 3!", "success");
    fetchNotes(); // Refresh note card with summarized badge
  } catch (err) {
    if (container) {
      container.innerHTML = `
        <div class="alert-banner warning">
          <strong>⚠️ AI Summarization Notice:</strong><br>
          ${escapeHtml(err.message)}
          <br><br>
          <small>Make sure Ollama is running (<code>ollama serve</code>) and Gemma 3 is pulled (<code>ollama pull gemma3:1b</code>).</small>
        </div>
      `;
    }
  } finally {
    spinner?.classList.add("hidden");
  }
}

function renderFormattedSummary(data) {
  const container = document.getElementById("summaryResultsContainer");
  if (!container) return;

  let html = "";

  if (data.summary) {
    html += `
      <div class="summary-card">
        <h5>📌 Summary</h5>
        <p>${escapeHtml(data.summary)}</p>
      </div>
    `;
  }

  if (data.key_points && data.key_points.length > 0) {
    html += `
      <div class="summary-card">
        <h5>💡 Key Points</h5>
        <ul>
          ${data.key_points.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}
        </ul>
      </div>
    `;
  }

  if (data.important_concepts && data.important_concepts.length > 0) {
    html += `
      <div class="summary-card">
        <h5>🔑 Important Concepts</h5>
        <div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:6px;">
          ${data.important_concepts.map((c) => `<span class="note-card-tag" style="background:#eef2ff; color:#4f46e5;">${escapeHtml(c)}</span>`).join("")}
        </div>
      </div>
    `;
  }

  if (data.action_items && data.action_items.length > 0) {
    html += `
      <div class="summary-card">
        <h5>✅ Action Items</h5>
        <ul>
          ${data.action_items.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}
        </ul>
      </div>
    `;
  }

  // If output was raw markdown
  if (!html && data.raw_markdown) {
    html = `<div class="summary-card"><pre style="white-space:pre-wrap; font-family:inherit;">${escapeHtml(data.raw_markdown)}</pre></div>`;
  }

  container.innerHTML = html;
}

// Feature 5: Ask AI About Your Notes
async function sendQAQuestion(questionText) {
  const input = document.getElementById("qaQuestionInput");
  const q = (questionText || input?.value || "").trim();
  if (!q) return;

  const contentInput = document.getElementById("noteContentInput");
  const content = (contentInput?.value || "").trim();

  if (!content) {
    showToast("Please enter some note content first before asking questions.", "warning");
    return;
  }

  // Append user bubble
  const chat = document.getElementById("qaHistory");
  if (chat) {
    const userMsg = document.createElement("div");
    userMsg.className = "qa-message user";
    userMsg.innerHTML = `<div class="qa-bubble">${escapeHtml(q)}</div>`;
    chat.appendChild(userMsg);
    chat.scrollTop = chat.scrollHeight;
  }

  if (input) input.value = "";

  // Append temporary loading bot bubble
  const botMsg = document.createElement("div");
  botMsg.className = "qa-message bot";
  botMsg.innerHTML = `<div class="qa-bubble"><span style="color:#64748b;">Gemma 3 is thinking...</span></div>`;
  chat?.appendChild(botMsg);
  chat.scrollTop = chat?.scrollHeight;

  try {
    let url = state.activeNoteId ? `/api/notes/${state.activeNoteId}/ask` : null;
    let res;

    if (url) {
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
    } else {
      // Temporary unsaved note
      res = await fetch("/api/notes/0/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, context: content }),
      });
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    const bubble = botMsg.querySelector(".qa-bubble");
    if (bubble) {
      bubble.innerHTML = escapeHtml(data.answer);
      if (!data.source_available) {
        bubble.innerHTML += `<br><small style="color:#f59e0b; display:block; margin-top:6px;">⚠️ Information was not found directly in the note.</small>`;
      }
    }
  } catch (err) {
    const bubble = botMsg.querySelector(".qa-bubble");
    if (bubble) {
      bubble.innerHTML = `<span style="color:#ef4444;">⚠️ Error: ${escapeHtml(err.message)}</span>`;
    }
  }
  chat.scrollTop = chat?.scrollHeight;
}

// Feature 6: Generate Quiz
async function triggerQuiz() {
  const contentInput = document.getElementById("noteContentInput");
  const content = (contentInput?.value || "").trim();

  if (!content) {
    showToast("Please enter some note content first before generating a quiz.", "warning");
    return;
  }

  if (!state.activeNoteId) {
    await saveCurrentNote(true);
  }

  const spinner = document.getElementById("quizLoadingSpinner");
  const container = document.getElementById("quizContainer");

  spinner?.classList.remove("hidden");
  if (container) container.innerHTML = "";

  try {
    const res = await fetch(`/api/notes/${state.activeNoteId}/quiz`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    state.currentQuizData = data.questions;
    state.userQuizAnswers = {};
    renderInteractiveQuiz();
    showToast("5 revision questions generated!", "success");
  } catch (err) {
    if (container) {
      container.innerHTML = `
        <div class="alert-banner warning">
          <strong>⚠️ Quiz Generation Notice:</strong><br>
          ${escapeHtml(err.message)}
          <br><br>
          <small>Make sure Ollama is running with Gemma 3 loaded.</small>
        </div>
      `;
    }
  } finally {
    spinner?.classList.add("hidden");
  }
}

function renderInteractiveQuiz() {
  const container = document.getElementById("quizContainer");
  if (!container || !state.currentQuizData) return;

  const questions = state.currentQuizData;
  let html = "";

  questions.forEach((q, qIdx) => {
    html += `
      <div class="quiz-card" id="quizCard-${qIdx}">
        <div class="quiz-q-num">Question ${qIdx + 1} of ${questions.length}</div>
        <div class="quiz-q-text">${escapeHtml(q.question)}</div>
        <div class="quiz-options">
          ${q.options
            .map(
              (opt, optIdx) => `
            <div class="quiz-option" id="opt-${qIdx}-${optIdx}" onclick="selectQuizOption(${qIdx}, ${optIdx})">
              <strong>${String.fromCharCode(65 + optIdx)}.</strong>
              <span>${escapeHtml(opt)}</span>
            </div>
          `
            )
            .join("")}
        </div>
        <div id="quizExplanation-${qIdx}" class="quiz-explanation hidden">
          💡 <strong>Explanation:</strong> ${escapeHtml(q.explanation)}
        </div>
      </div>
    `;
  });

  html += `
    <div style="text-align:center; margin-top:16px;">
      <button id="btnSubmitQuiz" class="btn btn-primary btn-block" onclick="evaluateQuizAnswers()">
        Check Quiz Answers
      </button>
    </div>
  `;

  container.innerHTML = html;
}

function selectQuizOption(qIdx, optIdx) {
  state.userQuizAnswers[qIdx] = optIdx;

  // Visual highlight
  const card = document.getElementById(`quizCard-${qIdx}`);
  if (card) {
    card.querySelectorAll(".quiz-option").forEach((el, idx) => {
      el.classList.toggle("selected", idx === optIdx);
    });
  }
}

function evaluateQuizAnswers() {
  if (!state.currentQuizData) return;
  const questions = state.currentQuizData;
  let score = 0;

  questions.forEach((q, qIdx) => {
    const userChoice = state.userQuizAnswers[qIdx];
    const correctChoice = q.correct_index;

    const card = document.getElementById(`quizCard-${qIdx}`);
    if (!card) return;

    card.querySelectorAll(".quiz-option").forEach((el, idx) => {
      el.classList.remove("selected", "correct", "incorrect");
      if (idx === correctChoice) {
        el.classList.add("correct");
      }
      if (userChoice === idx && userChoice !== correctChoice) {
        el.classList.add("incorrect");
      }
    });

    if (userChoice === correctChoice) {
      score++;
    }

    const explanation = document.getElementById(`quizExplanation-${qIdx}`);
    explanation?.classList.remove("hidden");
  });

  // Render score banner at top of quiz container
  const container = document.getElementById("quizContainer");
  const existingBanner = document.getElementById("quizScoreBanner");
  if (existingBanner) existingBanner.remove();

  const scoreBanner = document.createElement("div");
  scoreBanner.id = "quizScoreBanner";
  scoreBanner.className = "quiz-score-banner";
  const pct = Math.round((score / questions.length) * 100);
  scoreBanner.innerHTML = `
    <h3>Quiz Complete: ${score} / ${questions.length} (${pct}%)</h3>
    <p>${pct >= 80 ? "🎉 Outstanding work! You have mastered these notes." : "Keep studying and review the explanations above!"}</p>
  `;
  container?.prepend(scoreBanner);
  scoreBanner.scrollIntoView({ behavior: "smooth" });
}

// -------------------------------------------------------------
// VOICE-TO-NOTES (AUDIO UPLOAD & STT)
// -------------------------------------------------------------

function setupAudioDropzone() {
  const dropzone = document.getElementById("audioDropzone");
  const fileInput = document.getElementById("audioFileInput");
  const label = document.getElementById("selectedAudioFilename");
  const processBtn = document.getElementById("btnProcessAudio");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      handleSelectedAudioFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      handleSelectedAudioFile(fileInput.files[0]);
    }
  });

  function handleSelectedAudioFile(file) {
    state.audioFile = file;
    if (label) label.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    if (processBtn) processBtn.disabled = false;
  }
}

async function processAudioFile() {
  if (!state.audioFile) return;

  const spinner = document.getElementById("audioProcessingSpinner");
  const resultArea = document.getElementById("audioResultArea");
  const rawText = document.getElementById("audioRawTranscriptText");
  const structText = document.getElementById("audioStructuredNotesText");
  const titleInput = document.getElementById("audioNoteTitleInput");
  const autoStructure = document.getElementById("chkAutoStructureAudio")?.checked ?? true;

  spinner?.classList.remove("hidden");
  resultArea?.classList.add("hidden");

  const formData = new FormData();
  formData.append("file", state.audioFile);
  formData.append("auto_structure", autoStructure);

  try {
    const res = await fetch("/api/audio/transcribe", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    if (rawText) rawText.value = data.raw_transcript || "(No speech detected)";

    let structuredOutput = "";
    if (data.structured) {
      structuredOutput = data.structured.organized_content || "";
      if (data.structured.summary) {
        structuredOutput += `\n\n### Summary\n${data.structured.summary}`;
      }
      if (data.structured.key_points && data.structured.key_points.length) {
        structuredOutput += `\n\n### Key Points\n` + data.structured.key_points.map((p) => `- ${p}`).join("\n");
      }
      if (data.structured.action_items && data.structured.action_items.length) {
        structuredOutput += `\n\n### Action Items\n` + data.structured.action_items.map((a) => `- ${a}`).join("\n");
      }
    } else {
      structuredOutput = data.raw_transcript || "";
    }

    if (structText) structText.value = structuredOutput;
    if (titleInput) {
      const baseName = state.audioFile.name.replace(/\.[^/.]+$/, "");
      titleInput.value = `Voice Note: ${baseName}`;
    }

    resultArea?.classList.remove("hidden");
    showToast("Audio transcribed & structured successfully!", "success");
  } catch (err) {
    showToast(`Audio processing error: ${err.message}`, "error");
  } finally {
    spinner?.classList.add("hidden");
  }
}

async function saveAudioAsNote() {
  const titleInput = document.getElementById("audioNoteTitleInput");
  const structText = document.getElementById("audioStructuredNotesText");
  const rawText = document.getElementById("audioRawTranscriptText");

  const title = (titleInput?.value || "").trim() || "Voice Note";
  const content = (structText?.value || rawText?.value || "").trim();

  if (!content) {
    showToast("No content to save.", "warning");
    return;
  }

  try {
    const res = await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        content: content + "\n\n---\n*Transcribed with faster-whisper & structured by NoteMate AI*",
        tags: "audio, voice-note",
      }),
    });

    if (!res.ok) throw new Error("Failed to save note");
    const newNote = await res.json();
    showToast("Voice note saved to your collection!", "success");
    fetchNotes();
    openNoteInEditor(newNote.id);
  } catch (err) {
    showToast(`Error saving note: ${err.message}`, "error");
  }
}

// -------------------------------------------------------------
// PDF-TO-NOTES (DOCUMENT PROCESSING & PYMUPDF)
// -------------------------------------------------------------

function setupPdfDropzone() {
  const dropzone = document.getElementById("pdfDropzone");
  const fileInput = document.getElementById("pdfFileInput");
  const label = document.getElementById("selectedPdfFilename");
  const processBtn = document.getElementById("btnProcessPdf");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length) {
      handleSelectedPdfFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) {
      handleSelectedPdfFile(fileInput.files[0]);
    }
  });

  function handleSelectedPdfFile(file) {
    state.pdfFile = file;
    if (label) label.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    if (processBtn) processBtn.disabled = false;
  }
}

async function processPdfFile() {
  if (!state.pdfFile) return;

  const spinner = document.getElementById("pdfProcessingSpinner");
  const resultArea = document.getElementById("pdfResultArea");
  const alertBanner = document.getElementById("pdfAlertBanner");
  const extractedText = document.getElementById("pdfExtractedText");
  const structuredNotes = document.getElementById("pdfStructuredNotes");
  const metaStats = document.getElementById("pdfMetaStats");
  const titleInput = document.getElementById("pdfNoteTitleInput");
  const autoSummarize = document.getElementById("chkAutoSummarizePdf")?.checked ?? true;

  spinner?.classList.remove("hidden");
  resultArea?.classList.add("hidden");
  alertBanner?.classList.add("hidden");

  const formData = new FormData();
  formData.append("file", state.pdfFile);
  formData.append("auto_summarize", autoSummarize);

  try {
    const res = await fetch("/api/pdf/process", {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    const extract = data.extract_result || {};

    if (metaStats) {
      metaStats.textContent = `${extract.page_count || 0} pages • ${extract.char_count || 0} chars`;
    }

    if (extractedText) extractedText.value = extract.extracted_text || "";

    if (extract.is_scanned_or_empty) {
      alertBanner?.classList.remove("hidden");
      if (alertBanner) alertBanner.textContent = data.message || "⚠️ Notice: This PDF appears to be a scanned image or contains no extractable text.";
    }

    let summaryOut = "";
    if (data.summary_result) {
      const s = data.summary_result;
      if (s.summary) summaryOut += `### Summary\n${s.summary}\n\n`;
      if (s.key_points && s.key_points.length) {
        summaryOut += `### Key Points\n` + s.key_points.map((p) => `- ${p}`).join("\n") + "\n\n";
      }
      if (s.important_concepts && s.important_concepts.length) {
        summaryOut += `### Important Concepts\n` + s.important_concepts.join(", ") + "\n\n";
      }
      if (s.action_items && s.action_items.length) {
        summaryOut += `### Action Items\n` + s.action_items.map((a) => `- ${a}`).join("\n");
      }
    } else {
      summaryOut = extract.extracted_text || "";
    }

    if (structuredNotes) structuredNotes.value = summaryOut.trim();

    if (titleInput) {
      const baseName = state.pdfFile.name.replace(/\.[^/.]+$/, "");
      titleInput.value = `PDF: ${baseName}`;
    }

    resultArea?.classList.remove("hidden");
    showToast("PDF extracted and processed successfully!", "success");
  } catch (err) {
    showToast(`PDF processing error: ${err.message}`, "error");
  } finally {
    spinner?.classList.add("hidden");
  }
}

async function savePdfAsNote() {
  const titleInput = document.getElementById("pdfNoteTitleInput");
  const structuredNotes = document.getElementById("pdfStructuredNotes");
  const extractedText = document.getElementById("pdfExtractedText");

  const title = (titleInput?.value || "").trim() || "PDF Note";
  const content = (structuredNotes?.value || extractedText?.value || "").trim();

  if (!content) {
    showToast("No content to save.", "warning");
    return;
  }

  try {
    const res = await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        content: content + "\n\n---\n*Extracted with PyMuPDF & analyzed by NoteMate AI*",
        tags: "pdf, document",
      }),
    });

    if (!res.ok) throw new Error("Failed to save note");
    const newNote = await res.json();
    showToast("PDF note saved to your collection!", "success");
    fetchNotes();
    openNoteInEditor(newNote.id);
  } catch (err) {
    showToast(`Error saving note: ${err.message}`, "error");
  }
}

// -------------------------------------------------------------
// SETTINGS & OLLAMA CONFIGURATION
// -------------------------------------------------------------

async function testOllamaConnection() {
  const urlInput = document.getElementById("settingsOllamaUrl");
  const modelInput = document.getElementById("settingsOllamaModel");
  const resultBox = document.getElementById("settingsConnectionResult");

  const base_url = (urlInput?.value || "http://localhost:11434").trim();
  const model = (modelInput?.value || "gemma3:1b").trim();

  if (resultBox) {
    resultBox.className = "connection-status-box";
    resultBox.classList.remove("hidden");
    resultBox.textContent = "Testing connection to Ollama...";
  }

  try {
    // Save configuration first
    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ollama_base_url: base_url, ollama_model: model }),
    });

    const res = await fetch("/api/status");
    const status = await res.json();

    if (resultBox) {
      if (status.ollama_reachable) {
        resultBox.className = "connection-status-box success";
        const modelsList = status.available_models.length ? status.available_models.join(", ") : "none found";
        resultBox.innerHTML = `
          ✅ <strong>Connected to Ollama!</strong><br>
          • Base URL: <code>${escapeHtml(status.base_url)}</code><br>
          • Target Model: <code>${escapeHtml(status.active_model)}</code> (${status.model_available ? "Found" : "Not yet pulled"})<br>
          • Available Models: ${escapeHtml(modelsList)}
        `;
      } else {
        resultBox.className = "connection-status-box error";
        resultBox.innerHTML = `
          ❌ <strong>Cannot connect to Ollama at ${escapeHtml(base_url)}</strong><br>
          Please make sure Ollama is installed and running on your machine.<br>
          Terminal command: <code>ollama serve</code>
        `;
      }
    }
    checkSystemStatus();
  } catch (err) {
    if (resultBox) {
      resultBox.className = "connection-status-box error";
      resultBox.textContent = `Connection test error: ${err.message}`;
    }
  }
}

async function saveSettings() {
  const urlInput = document.getElementById("settingsOllamaUrl");
  const modelInput = document.getElementById("settingsOllamaModel");

  const base_url = (urlInput?.value || "http://localhost:11434").trim();
  const model = (modelInput?.value || "gemma3:1b").trim();

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ollama_base_url: base_url, ollama_model: model }),
    });
    if (!res.ok) throw new Error("Failed to update settings");
    showToast("Settings updated successfully", "success");
    checkSystemStatus();
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  }
}

// -------------------------------------------------------------
// EVENT LISTENERS INITIALIZATION
// -------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Navigation
  document.getElementById("btnNewNote")?.addEventListener("click", createNewNote);
  document.getElementById("btnEmptyNewNote")?.addEventListener("click", createNewNote);
  document.getElementById("navAllNotes")?.addEventListener("click", () => {
    switchView("dashboard");
    fetchNotes();
  });
  document.getElementById("btnBackToDashboard")?.addEventListener("click", () => {
    switchView("dashboard");
    fetchNotes();
  });
  document.getElementById("navAudioUpload")?.addEventListener("click", () => switchView("audio"));
  document.getElementById("btnCloseAudioView")?.addEventListener("click", () => switchView("dashboard"));
  document.getElementById("navPdfUpload")?.addEventListener("click", () => switchView("pdf"));
  document.getElementById("btnClosePdfView")?.addEventListener("click", () => switchView("dashboard"));
  document.getElementById("navSettings")?.addEventListener("click", () => switchView("settings"));
  document.getElementById("btnCloseSettingsView")?.addEventListener("click", () => switchView("dashboard"));
  document.getElementById("btnRefreshNotes")?.addEventListener("click", fetchNotes);

  // Search
  const searchInput = document.getElementById("searchInput");
  const clearSearchBtn = document.getElementById("clearSearchBtn");
  let searchDebounce;

  searchInput?.addEventListener("input", (e) => {
    const q = e.target.value.trim();
    state.activeFilter.query = q;
    clearSearchBtn?.classList.toggle("hidden", !q);

    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      fetchNotes();
    }, 250);
  });

  clearSearchBtn?.addEventListener("click", () => {
    if (searchInput) searchInput.value = "";
    clearSearchBtn.classList.add("hidden");
    state.activeFilter.query = "";
    fetchNotes();
  });

  document.getElementById("resetFilterBtn")?.addEventListener("click", clearFilters);

  // Editor Actions
  document.getElementById("btnSaveNote")?.addEventListener("click", () => saveCurrentNote(false));
  document.getElementById("btnDeleteNote")?.addEventListener("click", () => {
    if (state.activeNoteId) deleteNote(state.activeNoteId);
  });

  // Debounced auto-save on content or title change
  const triggerAutoSave = () => {
    clearTimeout(state.autoSaveTimer);
    const saveIndicator = document.getElementById("saveStatusIndicator");
    if (saveIndicator) saveIndicator.textContent = "Unsaved changes...";
    state.autoSaveTimer = setTimeout(() => {
      if (state.activeNoteId) {
        saveCurrentNote(true);
      }
    }, 1500);
  };

  document.getElementById("noteTitleInput")?.addEventListener("input", triggerAutoSave);
  document.getElementById("noteTagsInput")?.addEventListener("input", triggerAutoSave);
  document.getElementById("noteContentInput")?.addEventListener("input", triggerAutoSave);

  // AI Tab Buttons
  document.getElementById("tabBtnSummary")?.addEventListener("click", () => switchAITab("summary"));
  document.getElementById("tabBtnAsk")?.addEventListener("click", () => switchAITab("ask"));
  document.getElementById("tabBtnQuiz")?.addEventListener("click", () => switchAITab("quiz"));

  // AI Action Triggers
  document.getElementById("btnTriggerSummarize")?.addEventListener("click", triggerSummarize);
  document.getElementById("btnTriggerQuiz")?.addEventListener("click", triggerQuiz);

  // Copy Summary
  document.getElementById("btnCopySummary")?.addEventListener("click", () => {
    const container = document.getElementById("summaryResultsContainer");
    if (container) {
      navigator.clipboard.writeText(container.innerText);
      showToast("Summary copied to clipboard!", "info");
    }
  });

  // Append Summary into Note
  document.getElementById("btnInsertSummary")?.addEventListener("click", () => {
    const container = document.getElementById("summaryResultsContainer");
    const contentInput = document.getElementById("noteContentInput");
    if (container && contentInput) {
      contentInput.value += `\n\n---\n### AI Summary\n${container.innerText}`;
      saveCurrentNote(false);
      showToast("Summary appended to note content!", "success");
    }
  });

  // Ask AI Q&A
  document.getElementById("btnSendQuestion")?.addEventListener("click", () => sendQAQuestion());
  document.getElementById("qaQuestionInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendQAQuestion();
    }
  });

  // Suggestion Chips
  document.querySelectorAll(".suggested-chips .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-q");
      sendQAQuestion(q);
    });
  });

  // Audio Upload & Processing
  setupAudioDropzone();
  document.getElementById("btnProcessAudio")?.addEventListener("click", processAudioFile);
  document.getElementById("btnSaveAudioAsNote")?.addEventListener("click", saveAudioAsNote);

  // PDF Upload & Processing
  setupPdfDropzone();
  document.getElementById("btnProcessPdf")?.addEventListener("click", processPdfFile);
  document.getElementById("btnSavePdfAsNote")?.addEventListener("click", savePdfAsNote);

  // Settings
  document.getElementById("btnTestOllama")?.addEventListener("click", testOllamaConnection);
  document.getElementById("btnSaveSettings")?.addEventListener("click", saveSettings);

  // Initial Load
  checkSystemStatus();
  fetchNotes();
});
