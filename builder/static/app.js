const state = {
  bootstrap: null,
  structureId: "immersive-workspace",
  importedSession: null,
  importedSessionRaw: null,
  importMode: "none",
  draft: null,
  autoSearchGroups: [],
  selectedSideTab: "selected",
  selectedPreviewTab: "flat",
  inspectorItem: null,
  lastSearch: null,
  searchTargetId: null,
};

const exampleBrief = "Can Igloo display a PDF, website, and video in one reusable session?";

const nodes = {
  brandLogo: document.getElementById("brandLogo"),
  readinessScore: document.getElementById("readinessScore"),
  verdictChip: document.getElementById("verdictChip"),
  reviewChip: document.getElementById("reviewChip"),
  briefInput: document.getElementById("briefInput"),
  assessButton: document.getElementById("assessButton"),
  loadExampleButton: document.getElementById("loadExampleButton"),
  sessionFileInput: document.getElementById("sessionFileInput"),
  sessionImportSummary: document.getElementById("sessionImportSummary"),
  structureToggle: document.getElementById("structureToggle"),
  assessmentChips: document.getElementById("assessmentChips"),
  dependencyList: document.getElementById("dependencyList"),
  unknownList: document.getElementById("unknownList"),
  previewPanel: document.getElementById("previewPanel"),
  targetDuration: document.getElementById("targetDuration"),
  estimatedDuration: document.getElementById("estimatedDuration"),
  durationGap: document.getElementById("durationGap"),
  workflowSteps: document.getElementById("workflowSteps"),
  demoPlanNotes: document.getElementById("demoPlanNotes"),
  recommendationList: document.getElementById("recommendationList"),
  useCaseList: document.getElementById("useCaseList"),
  evidenceList: document.getElementById("evidenceList"),
  selectedContentList: document.getElementById("selectedContentList"),
  searchInput: document.getElementById("searchInput"),
  searchMode: document.getElementById("searchMode"),
  require4k: document.getElementById("require4k"),
  clearSearchTargetButton: document.getElementById("clearSearchTargetButton"),
  autoSearchButton: document.getElementById("autoSearchButton"),
  searchButton: document.getElementById("searchButton"),
  searchNotes: document.getElementById("searchNotes"),
  searchResults: document.getElementById("searchResults"),
  inspectorPanel: document.getElementById("inspectorPanel"),
  routeSummary: document.getElementById("routeSummary"),
  saveDraftButton: document.getElementById("saveDraftButton"),
  exportSessionButton: document.getElementById("exportSessionButton"),
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function chipClass(value) {
  const normalized = String(value).toLowerCase();
  if (normalized.includes("documented") || normalized.includes("known") || normalized.includes("good fit") || normalized.includes("straightforward")) {
    return "good";
  }
  if (normalized.includes("custom") || normalized.includes("unsupported") || normalized.includes("high risk") || normalized.includes("poor")) {
    return "risk";
  }
  if (normalized.includes("review") || normalized.includes("configuration") || normalized.includes("checking") || normalized.includes("caveat") || normalized.includes("unverified")) {
    return "caution";
  }
  return "neutral";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function humanizeValue(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function setupLabel(value) {
  return humanizeValue(value || "").replaceAll("360", "360");
}

function displaySourceName(value) {
  const normalized = String(value || "").trim();
  if (!normalized) return "Planned source";
  if (normalized === "Planned asset") return "Placeholder";
  if (normalized === "Live route") return "Live route";
  return normalized;
}

function importedLayerToCandidate(layer, index = 0) {
  const title = layer.name || `Imported layer ${index + 1}`;
  const contentType = layer.inferred_content_type || layer.layer_type || "Imported content";
  return {
    candidate_id: layer.layer_id || `imported-layer-${Date.now()}-${index}`,
    title,
    content_type: contentType,
    source: "Imported session",
    location: layer.file_path || "",
    readiness_status: layer.readiness_status || "needs checking",
    readiness_score: Number(layer.readiness_score || 52),
    exact_item_status: layer.readiness_status === "ready" ? "likely fine" : "needs checking",
    notes: [...(layer.notes || []), layer.source_field ? `Imported from ${layer.source_field}` : ""].filter(Boolean),
    recommended_layer_type: layer.layer_type || "WebView",
    query_hint: title,
    resolution_label: (layer.render_passes || []).join(", ") || "Imported route",
    recommended_minutes: minutesForContentType(contentType),
    selected: true,
    thumbnail_url: "",
    preview_caption: "Imported session layer",
    provider: "Imported session",
    match_score: 64,
    setup_archetype: "",
    layout_role: "",
    setup_notes: layer.notes || [],
    setup_summary: "",
  };
}

function updateSearchModeUi() {
  if (!nodes.clearSearchTargetButton) return;
  const target = state.searchTargetId && (state.draft?.selected_content || []).find((item) => item.candidate_id === state.searchTargetId);
  nodes.clearSearchTargetButton.style.display = target ? "block" : "none";
  nodes.clearSearchTargetButton.textContent = target ? `Stop replacing: ${target.title}` : "Clear replace target";
}

function replaceDraftItemWithSearchResult(targetId, result) {
  const items = state.draft?.selected_content || [];
  const target = items.find((item) => item.candidate_id === targetId);
  if (!target || !result) return;
  target.title = result.title || target.title;
  target.content_type = result.content_type || target.content_type;
  target.source = result.source || target.source;
  target.location = result.asset_location || result.url || target.location;
  target.readiness_status = result.readiness_status || target.readiness_status;
  target.readiness_score = result.readiness_status === "usable with prep" ? 74 : Math.max(48, Number(target.readiness_score || 0));
  target.exact_item_status = result.readiness_status === "usable with prep" ? "likely fine" : "needs checking";
  target.notes = [...new Set([...(target.notes || []), ...(result.notes || [])])];
  target.recommended_layer_type = layerTypeForSearchResult(result);
  target.query_hint = nodes.searchInput.value.trim() || target.query_hint || result.title || target.title;
  target.resolution_label = result.resolution_label || target.resolution_label;
  target.thumbnail_url = result.thumbnail_url || target.thumbnail_url || "";
  target.preview_caption = result.preview_caption || target.preview_caption || "";
  target.provider = result.provider || target.provider || target.source;
  target.match_score = result.match_score || target.match_score || 0;
  target.setup_archetype = result.setup_archetype || target.setup_archetype || "";
  target.layout_role = target.layout_role || result.layout_role || "";
  target.setup_notes = [...new Set([...(target.setup_notes || []), ...(result.notes || [])])];
  target.setup_summary = target.setup_summary || result.setup_summary || "";
}

function appendImportedLayersToDraft() {
  if (!state.importedSession?.layers?.length) return;
  if (!state.draft) {
    alert("Plan a session first, then append the imported layers into the same editable content list.");
    return;
  }
  const existingKeys = new Set(
    (state.draft.selected_content || []).map((item) => `${String(item.title || "").toLowerCase()}|${String(item.location || "").toLowerCase()}`)
  );
  const importedCandidates = state.importedSession.layers
    .map((layer, index) => importedLayerToCandidate(layer, index))
    .filter((item) => !existingKeys.has(`${String(item.title || "").toLowerCase()}|${String(item.location || "").toLowerCase()}`));
  state.draft.selected_content = [...(state.draft.selected_content || []), ...importedCandidates];
  recomputeDraftReadiness();
  renderSelectedContent();
  renderPreview();
}

function previewUrlForItem(item) {
  return item?.thumbnail_url || "";
}

function previewLabelForItem(item) {
  return item?.preview_caption || item?.title || "Planned content";
}

function previewTile(item, className = "") {
  const imageUrl = previewUrlForItem(item);
  const label = previewLabelForItem(item);
  const minimal = className.includes("minimal");
  if (imageUrl) {
    return `
      <div class="preview-tile ${className}" style="background-image:url('${escapeHtml(imageUrl)}')">
        ${minimal ? "" : `<div class="preview-tile-overlay"><span>${escapeHtml(label)}</span></div>`}
      </div>
    `;
  }
  return `
    <div class="preview-tile ${className} placeholder">
      ${
        minimal
          ? `<div class="preview-tile-minimal-copy"><strong>${escapeHtml(item?.content_type || "Draft slot")}</strong></div>`
          : `<div class="preview-tile-overlay"><strong>${escapeHtml(item?.title || "Planned content")}</strong><span>${escapeHtml(item?.content_type || "Draft slot")}</span></div>`
      }
    </div>
  `;
}

function renderStructures(structures) {
  nodes.structureToggle.innerHTML = structures
    .map(
      (structure) => `
        <button class="pill ${state.structureId === structure.structure_id ? "active" : ""}" data-structure="${escapeHtml(structure.structure_id)}">
          <span>${escapeHtml(structure.label)}</span>
        </button>
      `
    )
    .join("");
  nodes.structureToggle.querySelectorAll("[data-structure]").forEach((button) => {
    button.addEventListener("click", () => {
      state.structureId = button.dataset.structure;
      renderStructures(structures);
      renderPreview();
    });
  });
}

function renderAssessment() {
  const assessment = state.draft?.assessment;
  if (!assessment) {
    nodes.readinessScore.textContent = "--";
    nodes.verdictChip.textContent = "Not assessed";
    nodes.verdictChip.className = "chip neutral";
    nodes.reviewChip.textContent = "No signal yet";
    nodes.reviewChip.className = "chip neutral";
    nodes.assessmentChips.innerHTML = "";
    nodes.dependencyList.innerHTML = "<li>Create a draft to populate dependencies.</li>";
    nodes.unknownList.innerHTML = "<li>Create a draft to populate unknowns.</li>";
    nodes.routeSummary.textContent = "Plan a session to see the recommended build route.";
    return;
  }
  nodes.readinessScore.textContent = `${state.draft.readiness_score}%`;
  nodes.verdictChip.textContent = assessment.verdict;
  nodes.verdictChip.className = `chip ${chipClass(assessment.verdict)}`;
  const reviewNeeded = assessment.operational_flags.includes("Needs human review");
  nodes.reviewChip.textContent = reviewNeeded ? "Needs human review" : "Review not currently required";
  nodes.reviewChip.className = `chip ${reviewNeeded ? "caution" : "good"}`;
  const chips = [
    ["Confidence", `${assessment.confidence_percent}%`],
    ["Posture", humanizeValue(assessment.validation_posture)],
    ["Platform", humanizeValue(assessment.platform_capability)],
    ["Exact item", humanizeValue(assessment.exact_item_check)],
    ["Workflow", humanizeValue(assessment.workflow_fit)],
    ["Controls", humanizeValue(assessment.control_interaction_fit)],
  ];
  nodes.assessmentChips.innerHTML = chips
    .map(([label, value]) => `<div class="chip ${chipClass(value)}"><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}</div>`)
    .join("");
  nodes.dependencyList.innerHTML = (assessment.top_dependencies || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No dependencies highlighted yet.</li>";
  nodes.unknownList.innerHTML = (assessment.top_unknowns || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No unknowns highlighted yet.</li>";
  nodes.routeSummary.textContent = `Build route: ${assessment.recommended_route}`;
}

function renderSessionImport() {
  if (!state.importedSession) {
    nodes.sessionImportSummary.textContent = "No session imported yet.";
    nodes.sessionImportSummary.className = "mini-stack empty-state";
    return;
  }
  const session = state.importedSession;
  nodes.sessionImportSummary.className = "mini-stack";
  nodes.sessionImportSummary.innerHTML = `
    <div class="chip-grid">
      <div class="chip good">${escapeHtml(session.session_name)}</div>
      <div class="chip neutral">${escapeHtml(session.product_version)}</div>
      <div class="chip ${chipClass(session.inferred_session_type)}">${escapeHtml(session.inferred_session_type)}</div>
    </div>
    <ul class="compact-list">
      <li>${session.layer_count} layer(s)</li>
      <li>Exported with assets: ${session.exported_with_assets ? "yes" : "no"}</li>
      <li>Triggers and Actions enabled: ${session.trigger_action_enabled ? "yes" : "no"}</li>
    </ul>
    <div class="button-row">
      <button class="mini-button" data-import-action="replace">Use as plan</button>
      <button class="mini-button" data-import-action="append">Append layers</button>
    </div>
    <div class="imported-layer-stack">
      ${(session.layers || [])
        .map(
          (layer, index) => `
            <article class="content-item compact-import-item" data-import-layer-id="${escapeHtml(layer.layer_id)}">
              <div class="content-copy">
                <p class="content-title clamp-2">${escapeHtml(layer.name)}</p>
                <div class="content-meta compact-meta">
                  <span class="meta-pill">${escapeHtml(layer.inferred_content_type || layer.layer_type)}</span>
                  <span class="meta-pill">${escapeHtml(layer.readiness_status)}</span>
                </div>
                <p class="query-line clamp-1">${escapeHtml(layer.file_path || layer.source_field || "Imported route")}</p>
              </div>
              <div class="content-actions">
                <button class="mini-button" data-import-layer-action="inspect" data-import-layer-index="${index}">Inspect</button>
                <button class="mini-button" data-import-layer-action="add" data-import-layer-index="${index}">Add to session</button>
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
  nodes.sessionImportSummary.querySelectorAll("[data-import-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.importMode = button.dataset.importAction;
      if (state.importMode === "append" && state.draft) {
        appendImportedLayersToDraft();
        return;
      }
      await buildDraft();
    });
  });
  nodes.sessionImportSummary.querySelectorAll("[data-import-layer-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.importLayerIndex);
      const layer = session.layers?.[index];
      if (!layer) return;
      if (button.dataset.importLayerAction === "inspect") {
        state.inspectorItem = importedLayerToCandidate(layer, index);
        switchSideTab("inspector");
        renderInspector();
        return;
      }
      if (button.dataset.importLayerAction === "add") {
        if (!state.draft) {
          alert("Plan a session first, then add imported layers into the editable content list.");
          return;
        }
        state.draft.selected_content = [...(state.draft.selected_content || []), importedLayerToCandidate(layer, index)];
        recomputeDraftReadiness();
        renderSelectedContent();
        renderPreview();
      }
    });
  });
}

function renderUseCases() {
  const items = state.draft?.use_case_alignment || [];
  nodes.useCaseList.innerHTML = items.length
    ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "<li>Comparable Igloo patterns will appear here after you create a draft.</li>";
}

function renderEvidence() {
  const evidence = state.draft?.assessment?.evidence || [];
  nodes.evidenceList.innerHTML = evidence.length
    ? evidence
        .map(
          (item) => `
            <article class="evidence-item">
              <p class="eyebrow">${escapeHtml(item.source_type)}</p>
              <h3 class="content-title">${escapeHtml(item.title)}</h3>
              <p class="muted">${escapeHtml(item.excerpt).slice(0, 150)}${item.excerpt.length > 150 ? "..." : ""}</p>
            </article>
          `
        )
        .join("")
    : `<div class="empty-state">Evidence highlights will appear here after the brief is assessed.</div>`;
}

function renderPlan() {
  const draft = state.draft;
  if (!draft) {
    nodes.targetDuration.textContent = "--";
    nodes.estimatedDuration.textContent = "--";
    nodes.durationGap.textContent = "--";
    nodes.workflowSteps.innerHTML = `<div class="empty-state">Plan a session to see the run of show.</div>`;
    nodes.demoPlanNotes.innerHTML = "<li>Plan a session to see the recommended demo structure.</li>";
    nodes.recommendationList.innerHTML = `<div class="empty-state">Open items will appear here.</div>`;
    return;
  }
  nodes.targetDuration.textContent = `${draft.target_duration_minutes} min`;
  nodes.estimatedDuration.textContent = `${draft.estimated_duration_minutes} min`;
  nodes.durationGap.textContent = draft.duration_gap_minutes > 0 ? `${draft.duration_gap_minutes} min` : "Closed";
  nodes.workflowSteps.innerHTML = (draft.workflow_steps || [])
    .map(
      (step) => `
        <article class="workflow-item">
          <div class="workflow-topline">
            <strong>${escapeHtml(step.label)}</strong>
            <span class="minute-pill">${step.minutes}m</span>
          </div>
          <p class="muted">${escapeHtml(step.summary)}</p>
        </article>
      `
    )
    .join("");
  nodes.demoPlanNotes.innerHTML = (draft.demo_plan_notes || [])
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("") || "<li>No extra demo planning notes yet.</li>";
  nodes.recommendationList.innerHTML = (draft.recommendations || [])
    .map(
      (item) => `
        <article class="recommendation-item">
          <div class="workflow-topline">
            <strong>${escapeHtml(item.title)}</strong>
            <span class="priority-pill ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span>
          </div>
          <p class="muted">${escapeHtml(item.detail)}</p>
        </article>
      `
    )
    .join("");
}

function renderSelectedContent() {
  const items = state.draft?.selected_content || [];
  if (!items.length) {
    nodes.selectedContentList.innerHTML = `<div class="empty-state">Selected content will appear here after you plan the session.</div>`;
    return;
  }
  nodes.selectedContentList.innerHTML = items
    .map(
      (item) => `
        <article class="content-item" data-item-id="${escapeHtml(item.candidate_id)}">
          <div class="content-item-head">
            ${previewTile(item, "content-thumb compact minimal")}
            <div class="content-copy">
              <div class="content-title-row">
                <div>
                  <p class="content-title clamp-2">${escapeHtml(item.title)}</p>
                  <p class="muted">${escapeHtml(displaySourceName(item.provider || item.source))}</p>
                </div>
                <span class="score-badge">${item.readiness_score}</span>
              </div>
              <div class="content-meta compact-meta">
                <span class="meta-pill">${escapeHtml(item.content_type)}</span>
                <span class="meta-pill">${escapeHtml(item.recommended_layer_type)}</span>
                <span class="meta-pill">${escapeHtml(item.recommended_minutes)} min</span>
                ${item.layout_role ? `<span class="meta-pill">${escapeHtml(item.layout_role)}</span>` : ""}
              </div>
              <p class="query-line">${escapeHtml(humanizeValue(item.readiness_status))}</p>
            </div>
          </div>
          <div class="content-meta">
            <span class="meta-pill">${escapeHtml(item.match_score || 0)} match</span>
            <span class="meta-pill">${escapeHtml(item.exact_item_status || "not assessed")}</span>
            ${item.setup_archetype ? `<span class="meta-pill">${escapeHtml(setupLabel(item.setup_archetype))}</span>` : ""}
          </div>
          ${
            item.location
              ? `<p class="query-line clamp-1">Source: <a class="inline-link" href="${escapeHtml(item.location)}" target="_blank" rel="noreferrer">${escapeHtml(item.location)}</a></p>`
              : ""
          }
          <p class="query-line clamp-1">Search focus: ${escapeHtml(item.query_hint || item.title)}</p>
          <div class="content-actions">
            <button class="mini-button" data-action="inspect" data-item-id="${escapeHtml(item.candidate_id)}">Inspect</button>
            <button class="mini-button" data-action="find" data-item-id="${escapeHtml(item.candidate_id)}">Search</button>
            <button class="mini-button" data-action="remove" data-item-id="${escapeHtml(item.candidate_id)}">Remove</button>
          </div>
        </article>
      `
    )
    .join("");
  nodes.selectedContentList.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => handleContentAction(button.dataset.action, button.dataset.itemId));
  });
}

function renderSearchResults(results = [], notes = []) {
  const target = state.searchTargetId && (state.draft?.selected_content || []).find((item) => item.candidate_id === state.searchTargetId);
  nodes.searchNotes.innerHTML = notes.length ? notes.map((item) => `<p>${escapeHtml(item)}</p>`).join("") : "";
  nodes.searchResults.innerHTML = results.length
    ? results
        .map(
          (item, index) => `
            <article class="search-result">
              <div class="content-item-head">
                ${previewTile(item, "search-thumb compact minimal")}
                <div class="content-copy">
                  <div class="content-title-row">
                    <div>
                      <p class="content-title clamp-2">${escapeHtml(item.title)}</p>
                      <p class="muted">${escapeHtml(displaySourceName(item.provider || item.source))}</p>
                    </div>
                    <span class="chip ${chipClass(item.readiness_status)}">${escapeHtml(item.readiness_status)}</span>
                  </div>
                  <div class="content-meta compact-meta">
                    <span class="meta-pill">${escapeHtml(item.content_type)}</span>
                    <span class="meta-pill">${escapeHtml(item.resolution_label)}</span>
                    <span class="meta-pill">${escapeHtml(item.match_score || 0)} match</span>
                    ${item.setup_archetype ? `<span class="meta-pill">${escapeHtml(setupLabel(item.setup_archetype))}</span>` : ""}
                  </div>
                </div>
              </div>
              <div class="content-meta">
                <span class="meta-pill">${escapeHtml(item.source)}</span>
              </div>
              <p class="muted clamp-3">${escapeHtml(item.snippet || "No snippet available.")}</p>
              <div class="content-actions">
                <button class="mini-button" data-search-action="add" data-search-index="${index}">${target ? "Replace slot" : "Add to session"}</button>
                <a class="mini-button" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">Open link</a>
              </div>
            </article>
          `
        )
        .join("")
    : `<div class="empty-state">Search results will appear here.</div>`;
  nodes.searchResults.querySelectorAll("[data-search-action='add']").forEach((button) => {
    button.addEventListener("click", () => addSearchResult(Number(button.dataset.searchIndex)));
  });
}

function renderAutoSearchGroups(groups = []) {
  nodes.searchResults.innerHTML = groups.length
    ? groups
        .map((group) => {
          const best = group.best_result;
          const alternatives = group.alternatives || [];
          return `
            <section class="auto-search-group">
              <div class="workflow-topline">
                <strong>${escapeHtml(group.title || "Planned slot")}</strong>
                <span class="meta-pill">${escapeHtml(group.query || "")}</span>
              </div>
              ${
                best
                  ? `
                    <div class="auto-search-best">
                      ${previewTile(best, "search-thumb")}
                      <div class="auto-search-copy">
                        <p class="content-title">${escapeHtml(best.title)}</p>
                        <p class="muted">${escapeHtml(best.provider || best.source)}</p>
                        <div class="content-meta">
                          <span class="meta-pill">${escapeHtml(best.content_type)}</span>
                          <span class="meta-pill">${escapeHtml(best.resolution_label)}</span>
                          <span class="meta-pill">${escapeHtml(best.match_score || 0)} match</span>
                        </div>
                      <div class="content-actions">
                        <button class="mini-button" data-auto-apply="${escapeHtml(group.candidate_id)}">Use this result</button>
                        <a class="mini-button" href="${escapeHtml(best.url)}" target="_blank" rel="noreferrer">Open result</a>
                      </div>
                      </div>
                    </div>
                  `
                  : `<div class="empty-state">No strong result found yet for this slot.</div>`
              }
              ${
                alternatives.length > 1
                  ? `<div class="auto-search-alt-list">${alternatives
                      .slice(1, 3)
                      .map(
                        (item) => `
                          <article class="search-result compact-result">
                            ${previewTile(item, "search-thumb minimal")}
                            <div>
                              <p class="content-title">${escapeHtml(item.title)}</p>
                              <p class="muted">${escapeHtml(displaySourceName(item.provider || item.source))}</p>
                            </div>
                          </article>
                        `
                      )
                      .join("")}</div>`
                  : ""
              }
            </section>
          `;
        })
        .join("")
    : `<div class="empty-state">Auto-found content suggestions will appear here.</div>`;
  nodes.searchResults.querySelectorAll("[data-auto-apply]").forEach((button) => {
    button.addEventListener("click", () => applyAutoSearchResult(button.dataset.autoApply));
  });
}

function renderInspector() {
  const item = state.inspectorItem;
  if (!item) {
    nodes.inspectorPanel.className = "inspector-panel empty-state";
    nodes.inspectorPanel.textContent = "Select a content item or imported layer to inspect it here.";
    return;
  }
  nodes.inspectorPanel.className = "inspector-panel";
  const notes = item.notes || [];
  nodes.inspectorPanel.innerHTML = `
    ${previewTile(item, "inspector-thumb")}
    <div class="inspector-grid">
      <div class="inspector-block">
        <span class="label">Title</span>
        <strong>${escapeHtml(item.title || item.name)}</strong>
      </div>
      <div class="inspector-block">
        <span class="label">Type</span>
        <strong>${escapeHtml(item.content_type || item.inferred_content_type || item.layer_type)}</strong>
      </div>
      <div class="inspector-block">
        <span class="label">Status</span>
        <strong>${escapeHtml(item.readiness_status || item.exact_item_status || "Not assessed")}</strong>
      </div>
      <div class="inspector-block">
        <span class="label">Slot length</span>
        <strong>${escapeHtml(item.recommended_minutes || 0)} min</strong>
      </div>
      ${
        item.layout_role
          ? `<div class="inspector-block"><span class="label">Layout role</span><strong>${escapeHtml(item.layout_role)}</strong></div>`
          : ""
      }
      ${
        item.setup_archetype
          ? `<div class="inspector-block"><span class="label">Setup archetype</span><strong>${escapeHtml(setupLabel(item.setup_archetype))}</strong></div>`
          : ""
      }
    </div>
    ${
      item.candidate_id
        ? `
          <div class="inspector-edit-grid">
            <label class="field-label">Title<input id="inspectorTitleInput" type="text" value="${escapeHtml(item.title || item.name || "")}" /></label>
            <label class="field-label">Location<input id="inspectorLocationInput" type="text" value="${escapeHtml(item.location || item.file_path || "")}" /></label>
            <label class="field-label">Search focus<input id="inspectorQueryInput" type="text" value="${escapeHtml(item.query_hint || item.title || "")}" /></label>
            <label class="field-label">Minutes<input id="inspectorMinutesInput" type="number" min="1" max="30" value="${escapeHtml(item.recommended_minutes || 1)}" /></label>
          </div>
          <div class="button-row">
            <button class="mini-button" data-inspector-action="save" data-item-id="${escapeHtml(item.candidate_id)}">Save edits</button>
            <button class="mini-button" data-inspector-action="search" data-item-id="${escapeHtml(item.candidate_id)}">Search for replacement</button>
            <button class="mini-button" data-inspector-action="remove" data-item-id="${escapeHtml(item.candidate_id)}">Remove from session</button>
          </div>
        `
        : ""
    }
    <div class="inspector-block">
      <span class="label">Location / search focus</span>
      <strong>${escapeHtml(item.location || item.file_path || item.query_hint || "No location yet")}</strong>
    </div>
    <div class="inspector-block">
      <span class="label">Notes</span>
      <ul class="compact-list">${notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("") || "<li>No notes yet.</li>"}</ul>
    </div>
    ${
      item.setup_summary
        ? `<div class="inspector-block"><span class="label">Setup summary</span><strong>${escapeHtml(item.setup_summary)}</strong></div>`
        : ""
    }
  `;
  nodes.inspectorPanel.querySelectorAll("[data-inspector-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const itemId = button.dataset.itemId;
      const action = button.dataset.inspectorAction;
      if (!itemId || !action || !state.draft) return;
      const target = (state.draft.selected_content || []).find((entry) => entry.candidate_id === itemId);
      if (!target) return;
      if (action === "save") {
        target.title = document.getElementById("inspectorTitleInput")?.value?.trim() || target.title;
        target.location = document.getElementById("inspectorLocationInput")?.value?.trim() || "";
        target.query_hint = document.getElementById("inspectorQueryInput")?.value?.trim() || target.query_hint;
        target.recommended_minutes = Number(document.getElementById("inspectorMinutesInput")?.value || target.recommended_minutes || 1);
        target.exact_item_status = target.location ? "likely fine" : "needs checking";
        renderSelectedContent();
        renderPreview();
        renderInspector();
        return;
      }
      if (action === "search") {
        state.searchTargetId = itemId;
        nodes.searchInput.value = target.query_hint || target.title;
        nodes.searchMode.value = searchModeForItem(target);
        updateSearchModeUi();
        switchSideTab("search");
        renderSearchResults(state.lastSearch?.results || [], state.lastSearch?.notes || []);
        autoFillSearchQuery();
        return;
      }
      if (action === "remove") {
        handleContentAction("remove", itemId);
      }
    });
  });
}

function structureSvg(structureId) {
  const fills = {
    stage: "rgba(40, 90, 235, 0.18)",
    accent: "rgba(56, 222, 223, 0.26)",
    line: "rgba(255,255,255,0.48)",
  };
  if (structureId === "cylinder") {
    return `<svg viewBox="0 0 520 220" aria-hidden="true"><ellipse cx="260" cy="38" rx="130" ry="26" fill="${fills.stage}" stroke="${fills.line}" /><path d="M130 38v118c0 18 58 32 130 32s130-14 130-32V38" fill="rgba(0,99,220,0.08)" stroke="${fills.line}" /><ellipse cx="260" cy="156" rx="130" ry="32" fill="${fills.accent}" opacity="0.75" /></svg>`;
  }
  if (structureId === "dome") {
    return `<svg viewBox="0 0 520 220" aria-hidden="true"><path d="M120 170c0-86 63-134 140-134s140 48 140 134" fill="rgba(40,90,235,0.14)" stroke="${fills.line}" stroke-width="2"/><path d="M140 170h240" stroke="${fills.line}" stroke-width="2"/><path d="M180 148c25-18 58-28 80-28s55 10 80 28" fill="rgba(56,222,223,0.22)" /></svg>`;
  }
  if (structureId === "cave") {
    return `<svg viewBox="0 0 520 220" aria-hidden="true"><path d="M110 160V56l120-20 90 18 90 22v84" fill="rgba(40,90,235,0.12)" stroke="${fills.line}" /><path d="M110 160h300" stroke="${fills.line}" /><path d="M230 36v124" stroke="${fills.line}" opacity="0.5"/><path d="M320 54v106" stroke="${fills.line}" opacity="0.5"/></svg>`;
  }
  if (structureId === "cube") {
    return `<svg viewBox="0 0 520 220" aria-hidden="true"><path d="M150 150V70l110-24 110 24v80l-110 24z" fill="rgba(40,90,235,0.14)" stroke="${fills.line}"/><path d="M260 46v128" stroke="${fills.line}" opacity="0.5"/><path d="M150 70l110 24 110-24" stroke="${fills.line}" opacity="0.5"/></svg>`;
  }
  if (structureId === "retrofit") {
    return `<svg viewBox="0 0 520 220" aria-hidden="true"><rect x="120" y="58" width="280" height="110" rx="12" fill="rgba(40,90,235,0.14)" stroke="${fills.line}"/><rect x="152" y="78" width="216" height="70" rx="8" fill="rgba(56,222,223,0.16)" /></svg>`;
  }
  return `<svg viewBox="0 0 520 220" aria-hidden="true"><rect x="90" y="54" width="340" height="112" rx="18" fill="rgba(40,90,235,0.12)" stroke="rgba(255,255,255,0.5)" /><rect x="118" y="78" width="284" height="66" rx="12" fill="rgba(56,222,223,0.16)" /></svg>`;
}

function structureRoomHtml(structureId, draft) {
  const assets = draft?.selected_content || [];
  const setup = String(draft?.setup_archetype || "");
  const byRole = (role) => assets.find((item) => String(item.layout_role || "").toLowerCase() === role);
  const byType = (type) => assets.filter((item) => String(item.content_type || "").toLowerCase() === type);
  const main = byRole("immersive background") || byRole("hero wall") || byRole("three-wall span") || assets[0] || null;
  const left = byRole("left wall") || byType("dashboard app")[0] || byType("interactive web")[0] || assets[1] || null;
  const center = byRole("center wall") || main || assets[0] || null;
  const right = byRole("right wall") || byType("3d model")[0] || byType("website")[0] || assets[2] || null;
  const overlay = byRole("pinned support") || byRole("support panel") || byRole("launcher / support") || assets[3] || null;
  const suggestion = draft?.suggested_structure_reason || "";
  const roomMode = setupLabel(setup || "immersive_room_layout");
  if (structureId === "cylinder") {
    return `
      <div class="room-preview cylinder">
        <div class="room-copy">
          <p class="eyebrow">Suggested structure</p>
          <h3>${escapeHtml(humanizeValue(draft?.suggested_structure_id || structureId))}</h3>
          <p class="room-mode">${escapeHtml(roomMode)}</p>
          <p class="muted">${escapeHtml(draft?.setup_summary || suggestion)}</p>
        </div>
        <div class="room-visual cylinder-visual">
          <div class="room-surface wrap">${main ? previewTile(main, "projection hero minimal") : previewTile({ title: "Main 360 beat", content_type: "360 video" }, "projection hero minimal")}</div>
          <div class="room-overlay-card">${overlay ? previewTile(overlay, "projection small minimal") : ""}</div>
        </div>
      </div>
    `;
  }
  if (structureId === "cave" || structureId === "cube") {
    return `
      <div class="room-preview cave">
        <div class="room-copy">
          <p class="eyebrow">Suggested structure</p>
          <h3>${escapeHtml(humanizeValue(draft?.suggested_structure_id || structureId))}</h3>
          <p class="room-mode">${escapeHtml(roomMode)}</p>
          <p class="muted">${escapeHtml(draft?.setup_summary || suggestion)}</p>
        </div>
        <div class="room-visual cave-visual">
          <div class="room-floor"></div>
          <div class="room-walls ${setup === "three_wall_dashboard" ? "strategic" : ""}">
            <div class="wall left">
              <span class="wall-label">Left wall</span>
              ${
                setup === "three_wall_canvas"
                  ? previewTile(main, "projection hero minimal")
                  : left
                    ? previewTile(left, "projection minimal")
                    : previewTile({ title: "Support panel", content_type: "website" }, "projection minimal")
              }
            </div>
            <div class="wall center">
              <span class="wall-label">Center wall</span>
              ${center ? previewTile(center, "projection hero minimal") : previewTile({ title: "Main scene", content_type: "video" }, "projection hero minimal")}
            </div>
            <div class="wall right">
              <span class="wall-label">Right wall</span>
              ${
                setup === "three_wall_canvas"
                  ? previewTile(main, "projection hero minimal")
                  : right
                    ? previewTile(right, "projection minimal")
                    : previewTile({ title: "Reference panel", content_type: "pdf" }, "projection minimal")
              }
            </div>
          </div>
        </div>
      </div>
    `;
  }
  if (structureId === "dome") {
    return `
      <div class="room-preview dome">
        <div class="room-copy">
          <p class="eyebrow">Suggested structure</p>
          <h3>${escapeHtml(humanizeValue(draft?.suggested_structure_id || structureId))}</h3>
          <p class="room-mode">${escapeHtml(roomMode)}</p>
          <p class="muted">${escapeHtml(draft?.setup_summary || suggestion)}</p>
        </div>
        <div class="room-visual dome-visual">
          <div class="dome-shell">${main ? previewTile(main, "projection hero minimal") : previewTile({ title: "Cinematic dome scene", content_type: "360 video" }, "projection hero minimal")}</div>
        </div>
      </div>
    `;
  }
  return `
    <div class="room-preview workspace">
      <div class="room-copy">
        <p class="eyebrow">Suggested structure</p>
        <h3>${escapeHtml(humanizeValue(draft?.suggested_structure_id || structureId))}</h3>
        <p class="room-mode">${escapeHtml(roomMode)}</p>
        <p class="muted">${escapeHtml(draft?.setup_summary || suggestion)}</p>
      </div>
      <div class="room-visual workspace-visual">
        <div class="room-floor"></div>
        <div class="room-walls ${setup === "three_wall_dashboard" ? "strategic" : ""}">
          <div class="wall left">
            <span class="wall-label">Left wall</span>
            ${
              setup === "three_wall_canvas"
                ? previewTile(main, "projection hero minimal")
                : left
                  ? previewTile(left, "projection minimal")
                  : previewTile({ title: "Support layer", content_type: "website" }, "projection minimal")
            }
          </div>
          <div class="wall center">
            <span class="wall-label">Center wall</span>
            ${center ? previewTile(center, "projection hero minimal") : previewTile({ title: "Main visual", content_type: "video" }, "projection hero minimal")}
          </div>
          <div class="wall right">
            <span class="wall-label">Right wall</span>
            ${
              setup === "three_wall_canvas"
                ? previewTile(main, "projection hero minimal")
                : right
                  ? previewTile(right, "projection minimal")
                  : overlay
                    ? previewTile(overlay, "projection minimal")
                    : previewTile({ title: "Launcher or reference", content_type: "image" }, "projection minimal")
            }
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderPreview() {
  const draft = state.draft;
  const structure = state.bootstrap?.structures?.find((item) => item.structure_id === state.structureId);
  if (!draft) {
    nodes.previewPanel.innerHTML = `<div class="empty-state">Plan a session to generate the first preview.</div>`;
    return;
  }
  const assets = draft.selected_content || [];
  const layers = draft.layer_drafts || [];
  const heroAsset = assets[0] || null;
  if (state.selectedPreviewTab === "flat") {
    const unresolved = assets.filter((item) => !item.location).slice(0, 3);
    nodes.previewPanel.innerHTML = `
      <section class="preview-stage">
        <div class="preview-stage-grid">
          <div class="preview-hero" ${heroAsset && heroAsset.thumbnail_url ? `style="background-image:linear-gradient(180deg, rgba(6,19,31,0.15), rgba(6,19,31,0.82)), url('${escapeHtml(heroAsset.thumbnail_url)}')"` : ""}>
            <div class="preview-overlay top">
              <p class="eyebrow">${escapeHtml(structure?.label || draft.structure.label)}</p>
              <h3>${escapeHtml(heroAsset?.title || "Main session moment")}</h3>
              <p class="muted clamp-3">${escapeHtml(draft.assessment.practical_summary)}</p>
            </div>
          </div>
          <div class="preview-summary-stack">
            <div class="summary-block">
              <span class="label">Setup archetype</span>
              <strong>${escapeHtml(setupLabel(draft.setup_archetype || "single_surface_reference"))}</strong>
              <p class="muted clamp-3">${escapeHtml(draft.setup_summary || draft.suggested_structure_reason)}</p>
            </div>
            <div class="summary-block">
              <span class="label">Suggested room</span>
              <strong>${escapeHtml(humanizeValue(draft.suggested_structure_id))}</strong>
              <p class="muted clamp-3">${escapeHtml(draft.suggested_structure_reason)}</p>
            </div>
            <div class="summary-block">
              <span class="label">Build route</span>
              <p class="muted clamp-4">${escapeHtml(draft.assessment.recommended_route)}</p>
            </div>
            <div class="summary-block">
              <span class="label">Content to source</span>
              <ul class="compact-list compact-source-list">
                ${
                  unresolved.length
                    ? unresolved.map((item) => `<li><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.query_hint)}</span></li>`).join("")
                    : "<li>Nothing critical is missing in this plan.</li>"
                }
              </ul>
            </div>
          </div>
        </div>
        <div class="preview-strip">
          ${assets
            .slice(0, 4)
            .map(
              (item) => `
                <article class="asset-rail-item">
                  ${previewTile(item, "rail-thumb minimal")}
                  <div>
                    <p class="content-title clamp-1">${escapeHtml(item.title)}</p>
                    <p class="muted">${escapeHtml(item.content_type)} | ${escapeHtml(item.recommended_layer_type)}</p>
                  </div>
                </article>
              `
            )
            .join("")}
        </div>
        <div class="plan-grid preview-bottom-grid">
          <div class="plan-block">
            <span class="label">Layers in play</span>
            <ul class="compact-list">
              ${(layers || []).slice(0, 4).map((layer) => `<li><strong>${escapeHtml(layer.label)}</strong><span>${escapeHtml(layer.purpose)}</span></li>`).join("")}
            </ul>
          </div>
          <div class="plan-block">
            <span class="label">Operator notes</span>
            <ul class="compact-list">
              ${(draft.demo_plan_notes || []).slice(0, 3).map((note) => `<li>${escapeHtml(note)}</li>`).join("") || "<li>No special operator notes yet.</li>"}
            </ul>
          </div>
        </div>
      </section>
    `;
    return;
  }
  if (state.selectedPreviewTab === "structure") {
    nodes.previewPanel.innerHTML = `
      <section class="structure-stage">
        <div class="plan-block">
          <span class="label">Structure profile</span>
          <strong>${escapeHtml(structure?.label || draft.structure.label)}</strong>
          <p class="muted">${escapeHtml(structure?.description || draft.structure.description)}</p>
          <p class="muted">Recommended: ${escapeHtml(humanizeValue(draft.suggested_structure_id))}</p>
          <p class="muted clamp-3">${escapeHtml(draft.suggested_structure_reason)}</p>
        </div>
        ${structureRoomHtml(state.structureId, draft)}
        <div class="content-list">
          ${assets.slice(0, 4).map(
            (item) => `
              <div class="content-item">
                ${previewTile(item, "content-thumb small minimal")}
                <p class="content-title">${escapeHtml(item.title)}</p>
                <div class="content-meta">
                  <span class="meta-pill">${escapeHtml(item.content_type)}</span>
                  <span class="meta-pill">${escapeHtml(item.readiness_status)}</span>
                </div>
              </div>
            `
          ).join("")}
        </div>
      </section>
    `;
    return;
  }
  nodes.previewPanel.innerHTML = `
    <section class="layer-stage">
      <div class="layer-list">
        ${layers.map(
          (layer, index) => `
            <article class="layer-card">
              <p class="eyebrow">Layer ${index + 1}</p>
              <h3 class="content-title">${escapeHtml(layer.label)}</h3>
              <div class="content-meta">
                <span class="meta-pill">${escapeHtml(layer.layer_type)}</span>
                <span class="meta-pill">${escapeHtml(layer.purpose)}</span>
              </div>
              <ul class="compact-list">${layer.key_settings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
            </article>
          `
        ).join("")}
      </div>
    </section>
  `;
}

function switchSideTab(tabId) {
  state.selectedSideTab = tabId;
  document.querySelectorAll("[data-side-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.sideTab === tabId);
  });
  document.querySelectorAll(".side-tab").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${tabId}Tab`);
  });
}

function switchPreviewTab(tabId) {
  state.selectedPreviewTab = tabId;
  document.querySelectorAll("[data-preview-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.previewTab === tabId);
  });
  renderPreview();
}

function searchModeForItem(item) {
  if (item.content_type === "360 video") return "youtube_360";
  if (item.content_type === "interactive web") return "immersive_web";
  if (item.content_type === "dashboard app") return "review_app";
  if (item.content_type === "3d model") return "interactive_model";
  if ((item.query_hint || "").toLowerCase().includes("webxr")) return "webxr";
  return "website";
}

function layerTypeForSearchResult(item) {
  if (item.recommended_layer_type) return item.recommended_layer_type;
  const type = (item.content_type || "").toLowerCase();
  if (type.includes("youtube")) return "WebView";
  if (type.includes("website") || type.includes("webxr") || type.includes("interactive web") || type.includes("review app")) return "WebView";
  if (type.includes("model")) return "ModelViewer";
  if (type.includes("app stream")) return "Spout";
  if (type.includes("image")) return "Image";
  return "Video";
}

function minutesForContentType(type) {
  const normalized = String(type || "").toLowerCase();
  if (normalized.includes("360")) return 4;
  if (normalized.includes("pdf")) return 2;
  if (normalized.includes("dashboard")) return 3;
  if (normalized.includes("website") || normalized.includes("webxr")) return 2;
  if (normalized.includes("interactive web")) return 3;
  if (normalized.includes("image")) return 1;
  if (normalized.includes("model")) return 4;
  return 3;
}

function rebuildDerivedPlan() {
  if (!state.draft?.assessment) return;
  const items = state.draft.selected_content || [];
  const hasNavigation = items.some((item) => /menu|navigation/i.test(item.title || ""));
  const steps = [];
  if (hasNavigation || items.length > 2) {
    steps.push({
      step_id: "derived-open",
      label: "Open the session and orient the room",
      minutes: 1,
      summary: "Use the launch surface to start in a clean, repeatable state.",
    });
  }
  items.forEach((item, index) => {
    steps.push({
      step_id: `derived-${index + 1}`,
      label: item.title,
      minutes: Number(item.recommended_minutes || minutesForContentType(item.content_type)),
      summary: "Use this as one of the prepared beats in the operator flow.",
      source_candidate_id: item.candidate_id,
    });
  });
  if (items.length > 1) {
    steps.push({
      step_id: "derived-reset",
      label: "Reset or return to launcher",
      minutes: 1,
      summary: "End on a stable state so the next run starts cleanly.",
    });
  }
  state.draft.workflow_steps = steps;
  state.draft.estimated_duration_minutes = steps.reduce((sum, item) => sum + Number(item.minutes || 0), 0);
  state.draft.duration_gap_minutes = Math.max(0, Number(state.draft.target_duration_minutes || 10) - Number(state.draft.estimated_duration_minutes || 0));
}

function recomputeDraftReadiness() {
  if (!state.draft?.assessment) return;
  const items = state.draft.selected_content || [];
  const contentScore = items.length
    ? Math.round(items.reduce((sum, item) => sum + Number(item.readiness_score || 0), 0) / items.length)
    : 25;
  const assessmentScore = Number(state.draft.assessment.confidence_percent || 0);
  rebuildDerivedPlan();
  let score = Math.round(assessmentScore * 0.52 + contentScore * 0.48);
  if ((state.draft.assessment.operational_flags || []).includes("Needs human review")) score -= 5;
  if (Number(state.draft.duration_gap_minutes || 0) > 0) score -= Math.min(12, Number(state.draft.duration_gap_minutes || 0) * 2);
  state.draft.readiness_score = Math.max(0, Math.min(100, score));
  state.draft.readiness_label =
    score >= 80 ? "Ready to configure" : score >= 60 ? "Promising with checks" : score >= 40 ? "Needs content and review" : "Not ready yet";
  renderAssessment();
  renderPlan();
}

function handleContentAction(action, itemId) {
  const items = state.draft?.selected_content || [];
  const index = items.findIndex((item) => item.candidate_id === itemId);
  if (index === -1) return;
  const item = items[index];
  if (action === "inspect") {
    state.inspectorItem = item;
    switchSideTab("inspector");
    renderInspector();
    return;
  }
  if (action === "find") {
    state.searchTargetId = itemId;
    nodes.searchInput.value = item.query_hint || item.title;
    nodes.searchMode.value = searchModeForItem(item);
    updateSearchModeUi();
    switchSideTab("search");
    renderSearchResults(state.lastSearch?.results || [], state.lastSearch?.notes || []);
    autoFillSearchQuery();
    return;
  }
  if (action === "remove") {
    items.splice(index, 1);
    state.draft.selected_content = items;
    if (state.searchTargetId === itemId) {
      state.searchTargetId = null;
      updateSearchModeUi();
    }
    recomputeDraftReadiness();
    renderSelectedContent();
    renderPreview();
    renderInspector();
  }
}

function addSearchResult(index) {
  const results = state.lastSearch?.results || [];
  const item = results[index];
  if (!item || !state.draft) return;
  if (state.searchTargetId) {
    replaceDraftItemWithSearchResult(state.searchTargetId, item);
    state.searchTargetId = null;
    updateSearchModeUi();
    recomputeDraftReadiness();
    renderSelectedContent();
    renderPreview();
    renderInspector();
    return;
  }
  state.draft.selected_content.unshift({
    candidate_id: `search-${Date.now()}-${index}`,
    title: item.title,
    content_type: item.content_type,
    source: item.source,
    location: item.asset_location || item.url,
    readiness_status: item.readiness_status,
    readiness_score: item.readiness_status === "usable with prep" ? 70 : 44,
    exact_item_status: "needs checking",
    notes: item.notes,
    recommended_layer_type: layerTypeForSearchResult(item),
    query_hint: nodes.searchInput.value.trim() || item.title,
    resolution_label: item.resolution_label,
    recommended_minutes: minutesForContentType(item.content_type),
    selected: true,
    thumbnail_url: item.thumbnail_url || "",
    preview_caption: item.preview_caption || "",
    provider: item.provider || item.source || "",
    match_score: item.match_score || 0,
    setup_archetype: item.setup_archetype || "",
    layout_role: item.layout_role || "",
    setup_notes: item.notes || [],
    setup_summary: item.setup_summary || "",
  });
  recomputeDraftReadiness();
  renderSelectedContent();
  renderPreview();
}

function applyAutoSearchResult(candidateId) {
  if (!state.draft) return;
  const group = (state.autoSearchGroups || []).find((item) => item.candidate_id === candidateId);
  const best = group?.best_result;
  if (!group || !best) return;
  const target = (state.draft.selected_content || []).find((item) => item.candidate_id === candidateId);
  if (!target) return;
  target.title = best.title || target.title;
  target.location = best.url || target.location;
  target.source = best.source || target.source;
  target.provider = best.provider || target.provider || target.source;
  target.thumbnail_url = best.thumbnail_url || target.thumbnail_url || "";
  target.preview_caption = best.preview_caption || target.preview_caption || "";
  target.match_score = best.match_score || target.match_score || 0;
  target.readiness_status = best.readiness_status || target.readiness_status;
  target.resolution_label = best.resolution_label || target.resolution_label;
  target.recommended_layer_type = layerTypeForSearchResult(best);
  target.setup_archetype = target.setup_archetype || best.setup_archetype || "";
  target.layout_role = target.layout_role || best.layout_role || "";
  target.setup_summary = target.setup_summary || best.setup_summary || "";
  target.notes = [...new Set([...(target.notes || []), ...(best.notes || [])])];
  target.exact_item_status = best.readiness_status === "usable with prep" ? "likely fine" : "needs checking";
  target.readiness_score = Math.max(Number(target.readiness_score || 0), best.readiness_status === "usable with prep" ? 72 : 54);
  recomputeDraftReadiness();
  renderSelectedContent();
  renderPreview();
  state.inspectorItem = target;
  switchSideTab("inspector");
  renderInspector();
}

async function buildDraft() {
  const brief =
    nodes.briefInput.value.trim() ||
    (state.importMode !== "none" && state.importedSession?.session_name
      ? `Imported session review: ${state.importedSession.session_name}`
      : "");
  if (!brief) return;
  nodes.assessButton.disabled = true;
  nodes.assessButton.textContent = "Planning...";
  try {
    state.draft = await requestJson("/api/assess", {
      method: "POST",
      body: JSON.stringify({
        brief,
        structure_id: state.structureId,
        session_import: state.importMode === "none" ? null : state.importedSessionRaw,
        import_mode: state.importMode,
      }),
    });
    if (
      state.structureId === "immersive-workspace" &&
      state.draft?.suggested_structure_id &&
      state.draft.suggested_structure_id !== state.structureId
    ) {
      state.structureId = state.draft.suggested_structure_id;
      renderStructures(state.bootstrap.structures);
      state.draft = await requestJson("/api/assess", {
        method: "POST",
        body: JSON.stringify({
          brief,
          structure_id: state.structureId,
          session_import: state.importMode === "none" ? null : state.importedSessionRaw,
          import_mode: state.importMode,
        }),
      });
    }
    state.autoSearchGroups = [];
    state.inspectorItem = null;
    state.searchTargetId = null;
    renderAll();
    if (state.draft.search_suggestions?.length) {
      const suggestion = state.draft.search_suggestions[0];
      nodes.searchInput.value = suggestion.query;
      nodes.searchMode.value = suggestion.mode;
      updateSearchModeUi();
    }
  } catch (error) {
    alert(error.message);
  } finally {
    nodes.assessButton.disabled = false;
    nodes.assessButton.textContent = "Plan session";
  }
}

async function handleSessionImport(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const content = await file.text();
  state.importedSessionRaw = { filename: file.name, content };
  state.importMode = "none";
  try {
    state.importedSession = await requestJson("/api/parse-session", {
      method: "POST",
      body: JSON.stringify(state.importedSessionRaw),
    });
    renderSessionImport();
  } catch (error) {
    alert(error.message);
  }
}

async function runSearch() {
  const query = nodes.searchInput.value.trim();
  if (!query) return;
  nodes.searchButton.disabled = true;
  nodes.searchButton.textContent = "Searching...";
  try {
    state.lastSearch = await requestJson("/api/search-content", {
      method: "POST",
      body: JSON.stringify({
        query,
        mode: nodes.searchMode.value,
        require_4k: nodes.require4k.checked,
      }),
    });
    renderSearchResults(state.lastSearch.results, state.lastSearch.notes);
    updateSearchModeUi();
  } catch (error) {
    alert(error.message);
  } finally {
    nodes.searchButton.disabled = false;
    nodes.searchButton.textContent = "Find content";
  }
}

async function autoFillSearchQuery() {
  const brief = nodes.briefInput.value.trim();
  if (!brief) {
    alert("Write a brief first so the builder can plan a useful search query.");
    return;
  }
  const target = state.searchTargetId && (state.draft?.selected_content || []).find((item) => item.candidate_id === state.searchTargetId);
  nodes.autoSearchButton.disabled = true;
  nodes.autoSearchButton.textContent = "Planning query...";
  try {
    const payload = await requestJson("/api/plan-search-query", {
      method: "POST",
      body: JSON.stringify({
        brief,
        mode: nodes.searchMode.value,
        require_4k: nodes.require4k.checked,
        target_title: target?.title || "",
        target_content_type: target?.content_type || "",
        existing_query: nodes.searchInput.value.trim() || target?.query_hint || "",
      }),
    });
    nodes.searchInput.value = payload.query || nodes.searchInput.value;
    const notes = Array.isArray(payload.notes) ? payload.notes : [];
    const plannerNotes = [`Planner: ${payload.planner || "deterministic"}`, payload.destination ? `Anchor: ${payload.destination}` : "", ...notes].filter(Boolean);
    nodes.searchNotes.innerHTML = plannerNotes.map((item) => `<p>${escapeHtml(item)}</p>`).join("");
    updateSearchModeUi();
  } catch (error) {
    alert(error.message);
  } finally {
    nodes.autoSearchButton.disabled = false;
    nodes.autoSearchButton.textContent = "Auto-fill from brief";
  }
}

async function runAutoSearch() {
  if (!state.draft?.selected_content?.length) {
    alert("Plan a session first so the builder knows what content to search for.");
    return;
  }
  nodes.autoSearchButton.disabled = true;
  nodes.autoSearchButton.textContent = "Searching...";
  try {
    const payload = await requestJson("/api/auto-search-content", {
      method: "POST",
      body: JSON.stringify({
        brief: nodes.briefInput.value.trim(),
        candidates: state.draft.selected_content,
      }),
    });
    state.autoSearchGroups = payload.groups || [];
    state.autoSearchGroups.forEach((group) => {
      if (group.best_result && Number(group.best_result.match_score || 0) >= 24) {
        applyAutoSearchResult(group.candidate_id);
      }
    });
    switchSideTab("search");
    nodes.searchNotes.innerHTML = "<p>The builder searched each planned content slot, attached the strongest current match it found, and kept alternatives here for review.</p>";
    renderAutoSearchGroups(state.autoSearchGroups);
    updateSearchModeUi();
  } catch (error) {
    alert(error.message);
  } finally {
    nodes.autoSearchButton.disabled = false;
    nodes.autoSearchButton.textContent = "Auto-fill from brief";
  }
}

async function saveDraft() {
  if (!state.draft) {
    alert("Plan a session before saving it.");
    return;
  }
  try {
    const payload = { name: state.draft.brief.slice(0, 40) || "mixed-media-draft", ...state.draft };
    const result = await requestJson("/api/save-draft", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    alert(`Draft saved to ${result.path}`);
  } catch (error) {
    alert(error.message);
  }
}

async function exportSessionPackage() {
  if (!state.draft) {
    alert("Plan a session before exporting a session package.");
    return;
  }
  nodes.exportSessionButton.disabled = true;
  nodes.exportSessionButton.textContent = "Packaging...";
  try {
    const payload = { name: state.draft.brief.slice(0, 40) || "igloo-session", ...state.draft };
    const result = await requestJson("/api/export-session-package", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    alert(`Draft session package created in ${result.package_dir}`);
  } catch (error) {
    alert(error.message);
  } finally {
    nodes.exportSessionButton.disabled = false;
    nodes.exportSessionButton.textContent = "Export session";
  }
}

function renderAll() {
  renderAssessment();
  renderSessionImport();
  renderUseCases();
  renderEvidence();
  renderPlan();
  renderSelectedContent();
  renderInspector();
  renderPreview();
  updateSearchModeUi();
}

async function bootstrap() {
  state.bootstrap = await requestJson("/api/bootstrap");
  nodes.brandLogo.src = state.bootstrap.logo_url;
  renderStructures(state.bootstrap.structures);
  const params = new URLSearchParams(window.location.search);
  const presetBrief = params.get("brief");
  const presetPreviewTab = params.get("previewTab");
  const presetSideTab = params.get("sideTab");
  nodes.briefInput.value = presetBrief || exampleBrief;
  if (presetPreviewTab && ["flat", "structure", "layers"].includes(presetPreviewTab)) {
    state.selectedPreviewTab = presetPreviewTab;
  }
  if (presetSideTab && ["selected", "search", "inspector"].includes(presetSideTab)) {
    state.selectedSideTab = presetSideTab;
  }
  document.querySelectorAll("[data-side-tab]").forEach((button) => {
    button.addEventListener("click", () => switchSideTab(button.dataset.sideTab));
  });
  document.querySelectorAll("[data-preview-tab]").forEach((button) => {
    button.addEventListener("click", () => switchPreviewTab(button.dataset.previewTab));
  });
  nodes.assessButton.addEventListener("click", buildDraft);
  nodes.loadExampleButton.addEventListener("click", () => {
    nodes.briefInput.value = exampleBrief;
  });
  nodes.sessionFileInput.addEventListener("change", handleSessionImport);
  nodes.clearSearchTargetButton.addEventListener("click", () => {
    state.searchTargetId = null;
    updateSearchModeUi();
    renderSearchResults(state.lastSearch?.results || [], state.lastSearch?.notes || []);
  });
  nodes.autoSearchButton.addEventListener("click", () => {
    if (state.searchTargetId || state.selectedSideTab === "search") {
      autoFillSearchQuery();
      return;
    }
    runAutoSearch();
  });
  nodes.searchButton.addEventListener("click", runSearch);
  nodes.saveDraftButton.addEventListener("click", saveDraft);
  nodes.exportSessionButton.addEventListener("click", exportSessionPackage);
  renderAll();
  if (params.get("autoPlan") === "1" && nodes.briefInput.value.trim()) {
    await buildDraft();
    if (params.get("autoSearch") === "1") {
      await runAutoSearch();
    }
  }
}

bootstrap().catch((error) => {
  console.error(error);
  alert(error.message);
});
