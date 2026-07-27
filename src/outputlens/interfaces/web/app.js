/**
 * OutputLens Web Demo -- Rendering layer only.
 *
 * Per M7-001: This file renders AnalysisDocument JSON. It does NOT:
 * - Extract claims
 * - Classify concepts
 * - Calculate trust scores
 * - Perform E/R/N analysis
 * - Create analytical conclusions
 *
 * All analytical values come from the engine via the API.
 */

const API_URL = "/analyze";

const TRIGGER_LABELS = {
  no_evidence: "No Evidence",
  novel_claim: "Novel",
  overconfident: "Overconfident",
  foundational: "Foundational",
  contradicted: "Contradicted",
  orphaned: "Orphaned",
};

const SEVERITY_LABELS = {
  minor_flags: "Minor flags only.",
  several_concerns: "Several concerns identified.",
  systematic_verification_needed: "Systematic verification recommended.",
};

function showError(msg) {
  const el = document.getElementById("error-msg");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError() {
  document.getElementById("error-msg").classList.add("hidden");
}

function showResults() {
  document.getElementById("results").classList.remove("hidden");
}

/** Render the Trust Profile (from A9). Values come from the engine. */
function renderTrustProfile(tp) {
  if (!tp) return;
  document.getElementById("pct-established").textContent = Math.round(tp.established_pct) + "%";
  document.getElementById("pct-plausible").textContent = Math.round(tp.plausible_pct) + "%";
  document.getElementById("pct-verify").textContent = Math.round(tp.needs_verification_pct) + "%";
  document.getElementById("bar-established").style.width = tp.established_pct + "%";
  document.getElementById("bar-plausible").style.width = tp.plausible_pct + "%";
  document.getElementById("bar-verify").style.width = tp.needs_verification_pct + "%";
}

/** Render extracted claims (from A2) with classifications (from A4, A5, A6).
 *  All values come from the engine JSON -- no analysis in this function. */
function renderClaims(claims, eAnns, evAnns, nAnns) {
  document.getElementById("claims-count").textContent = claims.length + " claims extracted.";
  const container = document.getElementById("claims-list");
  container.innerHTML = "";

  const eMap = buildLevelMap(eAnns || []);
  const evMap = buildLevelMap(evAnns || []);
  const nMap = buildLevelMap(nAnns || []);

  const table = document.createElement("table");
  table.className = "claims-table";
  table.innerHTML = "<thead><tr><th>ID</th><th>E</th><th>R</th><th>N</th><th>Claim</th></tr></thead><tbody></tbody>";
  const tbody = table.querySelector("tbody");

  claims.slice(0, 20).forEach(function(c) {
    const e = eMap[c.id] || "--";
    const r = evMap[c.id] || "--";
    const n = nMap[c.id] || "--";
    const row = tbody.insertRow();
    row.innerHTML = "<td>" + c.id + "</td>" +
      "<td class='level " + levelClass(e) + "'>" + e + "</td>" +
      "<td class='level " + levelClass(r) + "'>" + r + "</td>" +
      "<td class='level " + levelClass(n) + "'>" + n + "</td>" +
      "<td>" + escapeHtml(c.text || "").substring(0, 150) + "</td>";
  });

  container.appendChild(table);
}

/** Render the Verification Punchlist (from A16). Values come from the engine. */
function renderPunchlist(punchlist) {
  document.getElementById("punchlist-severity").textContent =
    SEVERITY_LABELS[punchlist.overall_severity] || "";

  const container = document.getElementById("punchlist-list");
  container.innerHTML = "";

  if (!punchlist.entries || punchlist.entries.length === 0) {
    container.innerHTML = "<p>No claims flagged for investigation.</p>";
    return;
  }

  const list = document.createElement("ol");
  list.className = "punchlist";

  punchlist.entries.forEach(function(entry) {
    const item = document.createElement("li");
    const trigger = TRIGGER_LABELS[entry.attention_trigger] || entry.attention_trigger;
    item.innerHTML =
      "<div class='pl-header'>" +
        "<span class='pl-rank'>#" + entry.rank + "</span>" +
        "<span class='pl-trigger tag-" + entry.attention_trigger + "'>" + trigger + "</span>" +
        "<span class='pl-importance'>" + entry.structural_importance + "</span>" +
      "</div>" +
      "<p class='pl-claim'>" + escapeHtml(entry.claim_text || "").substring(0, 200) + "</p>" +
      "<p class='pl-verification'><strong>Verify:</strong> " + escapeHtml(entry.suggested_verification || "").substring(0, 200) + "</p>";
    list.appendChild(item);
  });

  container.appendChild(list);
}

/** Render the narrative (from A15). */
function renderNarrative(narrative) {
  if (narrative && narrative.narrative_text) {
    document.getElementById("narrative-text").textContent = narrative.narrative_text;
  }
}

/** Build a claim_id -> level lookup from annotations. */
function buildLevelMap(annotations) {
  var map = {};
  annotations.forEach(function(a) { map[a.claim_id] = a.level; });
  return map;
}

/** Assign a CSS-friendly class based on level prefix. */
function levelClass(level) {
  if (!level) return "";
  var prefix = level[0];
  if (prefix === "E") return "e-level";
  if (prefix === "R") return "r-level";
  if (prefix === "N") return "n-level";
  return "";
}

function escapeHtml(text) {
  var div = document.createElement("div");
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

/** Main: send text to API, render results. */
async function analyze() {
  hideError();
  var text = document.getElementById("text-input").value;
  if (!text || !text.trim()) {
    showError("Please enter text to analyze.");
    return;
  }

  var btn = document.getElementById("analyze-btn");
  btn.disabled = true;
  btn.textContent = "Analyzing...";

  try {
    var body = { text: text };
    var prompt = document.getElementById("prompt-input").value.trim();
    var model = document.getElementById("model-input").value.trim();
    if (prompt) body.prompt = prompt;
    if (model) body.model = model;

    var response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      var err = await response.json();
      showError(err.error || "Analysis failed (HTTP " + response.status + ").");
      return;
    }

    var doc = await response.json();
    var ao = doc.analysis_objects || {};

    renderTrustProfile(ao.trust_profile);
    renderClaims(ao.claims || [], ao.establishedness_annotations,
                 ao.evidence_annotations, ao.novelty_annotations);
    renderPunchlist(ao.verification_punchlist || {});
    renderNarrative(ao.response_narrative);
    showResults();

  } catch (e) {
    showError("Connection error: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyze";
  }
}

document.getElementById("analyze-btn").addEventListener("click", analyze);
