const modeSettings = {
  answer: { label: "Ask EduGenie", placeholder: 'Ask anything — “Which is the largest ocean?”', hint: "Thoughtful answers, one question at a time", route: "learn" },
  explain: { label: "Explain this", placeholder: 'What should feel simpler? Try “the Pythagorean theorem.”', hint: "Clear steps, followed by an example", route: "learn" },
  quiz: { label: "Build my quiz", placeholder: 'Choose a topic — try “the Pythagorean theorem.”', hint: "Three questions. Instant feedback. Your pace.", route: "quiz" },
  summarize: { label: "Summarize", placeholder: "Paste the passage you want to understand…", hint: "Your text is sent only to the configured AI provider", route: "learn" },
  path: { label: "Create my path", placeholder: 'Choose a subject — try “SQL for a complete beginner.”', hint: "A clear route from the first step onward", route: "path" },
  recommend: { label: "Find my next step", placeholder: 'What are you learning? Try “I know basic SQL SELECT.”', hint: "One manageable thing to work on next", route: "learn" },
};

const state = { mode: "answer", result: null, prompt: "", toastTimer: null };
const $ = (selector) => document.querySelector(selector);
const promptInput = $("#studyPrompt");
const answerPanel = $("#answerPanel");
const answerContent = $("#answerContent");
const submitButton = $("#submitButton");
const answerByMode = {
  answer: "A thoughtful answer",
  explain: "An idea, made clearer",
  quiz: "A quick check on your understanding",
  summarize: "The main ideas, in brief",
  path: "A path you can follow",
  recommend: "A good next step",
};

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function selectMode(mode, { keepRoute = false } = {}) {
  if (!(mode in modeSettings)) return;
  state.mode = mode;
  const settings = modeSettings[mode];
  document.querySelectorAll(".mode-button").forEach((button) => {
    const selected = button.dataset.mode === mode;
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  $("#submitLabel").textContent = settings.label;
  $("#composerHint").lastChild.textContent = ` ${settings.hint}`;
  promptInput.placeholder = settings.placeholder;
  if (!keepRoute) navigate(settings.route, { preserveMode: true });
}

function navigate(route, { preserveMode = false } = {}) {
  if (route === "saved") {
    $("#workspaceView").hidden = true;
    $("#savedView").hidden = false;
    $("#crumbCurrent").textContent = "Saved notes";
    document.querySelectorAll(".nav-link").forEach((button) => button.classList.toggle("is-active", button.dataset.route === "saved"));
    renderSaved();
    return;
  }

  $("#workspaceView").hidden = false;
  $("#savedView").hidden = true;
  const mode = route === "quiz" ? "quiz" : route === "path" ? "path" : state.mode;
  if (!preserveMode) {
    state.mode = mode;
    document.querySelectorAll(".mode-button").forEach((button) => {
      const selected = button.dataset.mode === mode;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    const settings = modeSettings[mode];
    $("#submitLabel").textContent = settings.label;
    $("#composerHint").lastChild.textContent = ` ${settings.hint}`;
    promptInput.placeholder = settings.placeholder;
  }
  const isQuiz = route === "quiz";
  const isPath = route === "path";
  $("#crumbCurrent").textContent = isQuiz ? "Quiz lab" : isPath ? "Learning paths" : "Study desk";
  $("#pageTitle").innerHTML = isQuiz ? "Find out what<br /><em>you know.</em>" : isPath ? "A new skill, one<br /><em>step at a time.</em>" : "Make the complicated<br /><em>feel close.</em>";
  $("#pageCopy").textContent = isQuiz
    ? "Pick a topic and give your understanding a friendly little check-in."
    : isPath
      ? "Tell us what you want to learn. We’ll map out a clear route, from first principles to practice."
      : "One good question can open up a whole new way of seeing things. What’s on your mind?";
  document.querySelectorAll(".nav-link").forEach((button) => button.classList.toggle("is-active", button.dataset.route === route));
  if (state.result && route !== "quiz" && route !== "path") displayResult(state.result, state.prompt);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function formatText(value) {
  const escaped = escapeHtml(value);
  return escaped
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*\n]+)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/(^|\s)(https?:\/\/[^\s]+)/g, '$1<a href="$2" target="_blank" rel="noreferrer">$2</a>');
}

function renderQuiz(quiz) {
  const form = document.createElement("div");
  form.className = "quiz-list";
  form.setAttribute("aria-label", "Interactive quiz");
  let correct = 0;
  let completed = 0;
  const score = document.createElement("div");
  score.className = "quiz-score";
  score.hidden = true;

  quiz.forEach((item, questionIndex) => {
    const fieldset = document.createElement("fieldset");
    fieldset.className = "quiz-question";
    const legend = document.createElement("legend");
    legend.textContent = `${questionIndex + 1}. ${item.question}`;
    fieldset.append(legend);
    const choices = document.createElement("div");
    choices.className = "quiz-choices";
    const feedback = document.createElement("p");
    feedback.className = "quiz-feedback";
    feedback.hidden = true;

    item.choices.forEach((choice, choiceIndex) => {
      const button = document.createElement("button");
      button.className = "quiz-choice";
      button.type = "button";
      const marker = document.createElement("span");
      marker.className = "choice-marker";
      marker.textContent = String.fromCharCode(65 + choiceIndex);
      const text = document.createElement("span");
      text.textContent = choice;
      button.append(marker, text);
      button.addEventListener("click", () => {
        if (button.disabled) return;
        completed += 1;
        const isCorrect = choiceIndex === item.answer_index;
        if (isCorrect) correct += 1;
        choices.querySelectorAll("button").forEach((option, index) => {
          option.disabled = true;
          if (index === item.answer_index) option.classList.add("is-correct");
          else if (index === choiceIndex && !isCorrect) option.classList.add("is-wrong");
        });
        feedback.textContent = `${isCorrect ? "Exactly right." : "Not quite."} ${item.explanation}`;
        feedback.hidden = false;
        score.textContent = completed === quiz.length
          ? `You got ${correct} of ${quiz.length} right. ${correct === quiz.length ? "Brilliantly done." : "Every question is another chance to learn."}`
          : `${completed} of ${quiz.length} answered`;
        score.hidden = false;
        refreshIcons();
      });
      choices.append(button);
    });
    fieldset.append(choices, feedback);
    form.append(fieldset);
  });
  form.append(score);
  return form;
}

function displayResult(result, prompt) {
  state.result = result;
  state.prompt = prompt;
  answerContent.replaceChildren();
  const description = document.createElement("p");
  description.className = "answer-source";
  description.textContent = `${answerByMode[result.mode] ?? "Your study notes"} · ${result.source === "offline" ? "local preview" : `${result.source} AI`}`;
  answerContent.append(description);
  if (result.quiz?.length) {
    const title = document.createElement("p");
    title.textContent = result.content;
    answerContent.append(title, renderQuiz(result.quiz));
  } else {
    const response = document.createElement("div");
    response.innerHTML = formatText(result.content);
    answerContent.append(response);
  }
  $("#answerMeta").textContent = `JUST NOW · “${prompt.slice(0, 64)}${prompt.length > 64 ? "…”" : ""}`;
  $("#saveButton").classList.remove("is-saved");
  answerPanel.hidden = false;
  $("#quickStarts").hidden = true;
  refreshIcons();
}

async function handleSubmit(event) {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (prompt.length < 2) {
    promptInput.focus();
    return;
  }
  submitButton.disabled = true;
  $("#submitLabel").textContent = "Thinking…";
  answerPanel.hidden = true;
  $("#quickStarts").hidden = true;

  try {
    const response = await fetch("/api/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: state.mode, prompt }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Something went wrong. Please try again.");
    displayResult(result, prompt);
    answerPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    const result = { mode: state.mode, content: error.message || "Could not reach EduGenie. Check your connection and try again.", source: "error" };
    displayResult(result, prompt);
    $("#answerContent > .answer-source").textContent = "Something went wrong";
  } finally {
    submitButton.disabled = false;
    $("#submitLabel").textContent = modeSettings[state.mode].label;
    refreshIcons();
  }
}

function getSaved() {
  try {
    const parsed = JSON.parse(localStorage.getItem("edugenie-saved") || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function renderSaved() {
  const saved = getSaved();
  const savedList = $("#savedList");
  savedList.replaceChildren();
  const count = $("#savedCount");
  count.hidden = saved.length === 0;
  count.textContent = String(saved.length);
  if (!saved.length) {
    const empty = document.createElement("div");
    empty.className = "empty-saved";
    empty.textContent = "Your saved responses will appear here. Head to your study desk and tap the bookmark on anything worth keeping.";
    savedList.append(empty);
    return;
  }
  saved.forEach((item) => {
    const article = document.createElement("article");
    article.className = "saved-item";
    const heading = document.createElement("div");
    heading.className = "saved-item-head";
    const label = document.createElement("span");
    label.textContent = `${answerByMode[item.mode] ?? "Study note"} · ${new Date(item.savedAt).toLocaleDateString()}`;
    heading.append(label);
    const remove = document.createElement("button");
    remove.className = "icon-button";
    remove.type = "button";
    remove.setAttribute("aria-label", "Remove saved note");
    remove.title = "Remove saved note";
    const icon = document.createElement("i");
    icon.dataset.lucide = "trash-2";
    icon.setAttribute("aria-hidden", "true");
    remove.append(icon);
    remove.addEventListener("click", () => {
      localStorage.setItem("edugenie-saved", JSON.stringify(getSaved().filter((entry) => entry.id !== item.id)));
      renderSaved();
      showToast("Saved note removed.");
    });
    heading.append(remove);
    const question = document.createElement("p");
    question.textContent = `Your question: ${item.prompt}`;
    const answer = document.createElement("p");
    answer.textContent = item.content;
    article.append(heading, question, answer);
    savedList.append(article);
  });
  refreshIcons();
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("is-visible");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2200);
}

function saveResponse() {
  if (!state.result || state.result.source === "error") return;
  const saved = getSaved();
  if (saved.some((item) => item.prompt === state.prompt && item.content === state.result.content)) {
    showToast("That response is already saved.");
    return;
  }
  saved.unshift({
    id: globalThis.crypto?.randomUUID?.() ?? String(Date.now()),
    mode: state.result.mode,
    prompt: state.prompt,
    content: state.result.content,
    savedAt: new Date().toISOString(),
  });
  localStorage.setItem("edugenie-saved", JSON.stringify(saved.slice(0, 50)));
  renderSaved();
  $("#saveButton").classList.add("is-saved");
  showToast("Saved to your study notes.");
}

function setProviderStatus(provider, ready) {
  const labels = {
    offline: ["Local study mode", "Answers stay on this device", "EDUGENIE · LOCAL STUDY MODE"],
    openai: ["OpenAI connected", "Cloud answers · configured model", "EDUGENIE · OPENAI"],
    ollama: ["Ollama connected", "Answers powered by your local model", "EDUGENIE · OLLAMA"],
  };
  const [label, caption, footer] = labels[provider] ?? labels.offline;
  $("#providerLabel").textContent = ready ? label : "Set up your AI provider";
  $("#providerCaption").textContent = ready ? caption : "Local answers; add credentials in .env";
  $("#footerProvider").textContent = ready ? footer : "EDUGENIE · SETUP NEEDED";
  $("#statusDot").classList.toggle("is-ready", ready && provider !== "offline");
}

function init() {
  const now = new Date();
  $("#todayLabel").textContent = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }).format(now);
  renderSaved();
  refreshIcons();
  fetch("/api/health")
    .then((response) => response.json())
    .then(({ provider, ready }) => setProviderStatus(provider, ready))
    .catch(() => setProviderStatus("offline", true));

  document.querySelectorAll(".mode-button").forEach((button) => button.addEventListener("click", () => selectMode(button.dataset.mode)));
  document.querySelectorAll(".nav-link, .brand[data-route]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      navigate(button.dataset.route);
      if (button.dataset.route === "quiz" || button.dataset.route === "path") selectMode(button.dataset.route, { keepRoute: true });
      if (button.dataset.route === "learn") selectMode("answer", { keepRoute: true });
    });
  });
  document.querySelectorAll(".prompt-chip").forEach((button) => button.addEventListener("click", () => {
    const value = button.dataset.fill;
    promptInput.value = value;
    const mode = value.toLowerCase().includes("quiz") ? "quiz" : value.toLowerCase().includes("learning path") ? "path" : "answer";
    selectMode(mode);
    promptInput.focus();
  }));
  $("#studyForm").addEventListener("submit", handleSubmit);
  $("#saveButton").addEventListener("click", saveResponse);
  $("#studyPrompt").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) $("#studyForm").requestSubmit();
  });
}

init();