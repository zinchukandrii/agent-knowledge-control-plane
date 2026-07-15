const runButton = document.querySelector("#run-button");
const runStatus = document.querySelector("#run-status");
const runCopy = document.querySelector("#run-copy");
const trace = document.querySelector("#trace");
const evidenceList = document.querySelector("#evidence-list");
const evidenceCount = document.querySelector("#evidence-count");

function setStatus(label, variant) {
  runStatus.textContent = label;
  runStatus.className = `status ${variant}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatRole(role) {
  return escapeHtml(role.replaceAll("_", " "));
}

function evidenceSummary(excerpt) {
  return escapeHtml(excerpt.replace(/^#.*?\n\s*/u, "").trim());
}

function renderTrace(events) {
  trace.innerHTML = events
    .map(
      (event, index) =>
        `<div class="trace-row"><span>${String(index + 1).padStart(2, "0")}</span><strong>${formatRole(event.role)}</strong><p>${escapeHtml(event.detail)}</p></div>`,
    )
    .join("");
}

function renderEvidence(cards) {
  evidenceCount.textContent = `${cards.length} cards`;
  evidenceList.innerHTML = cards
    .map(
      (card) =>
        `<article class="evidence-card"><span>${escapeHtml(card.id)}</span><strong>${evidenceSummary(card.excerpt)}</strong><p>Source: ${escapeHtml(card.source_node_id)}</p></article>`,
    )
    .join("");
}

async function runFixture() {
  runButton.disabled = true;
  runButton.textContent = "Running local fixture…";
  setStatus("RUNNING", "running");
  runCopy.textContent = "Creating a task and executing the bounded workflow through the local API.";

  try {
    const taskResponse = await fetch("/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: "demo-research",
        objective: "Create an evidence brief from public fixtures.",
      }),
    });
    if (!taskResponse.ok) throw new Error("Task creation failed.");

    const task = await taskResponse.json();
    const runResponse = await fetch(`/tasks/${task.id}/run`, { method: "POST" });
    if (!runResponse.ok) throw new Error("Fixture run failed.");

    const run = await runResponse.json();
    const statusClass = run.status === "VERIFIED" ? "verified" : "blocked";
    setStatus(run.status, statusClass);
    runCopy.textContent = `${run.evidence_cards.length} evidence cards and ${run.brief.claims.length} cited claims persisted locally.`;
    renderTrace(run.trace);
    renderEvidence(run.evidence_cards);
  } catch (error) {
    setStatus("ERROR", "blocked");
    runCopy.textContent = error.message;
    trace.innerHTML = '<div class="trace-empty">The local run did not complete. Inspect the API response.</div>';
  } finally {
    runButton.disabled = false;
    runButton.innerHTML = 'Run verified fixture <span>→</span>';
  }
}

runButton.addEventListener("click", runFixture);
