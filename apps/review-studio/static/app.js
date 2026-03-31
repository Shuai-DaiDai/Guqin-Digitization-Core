const state = {
  data: null,
  config: null,
  currentPageId: null,
  currentReviewId: null,
  statusFilter: "all",
  decisions: {},
  progressByPage: {},
  authToken: "",
  remoteEnabled: false,
  selectedReviewIds: [],
  marquee: null,
  pageNotes: {},
};

const dom = {
  siteTitle: document.getElementById("site-title"),
  siteSubtitle: document.getElementById("site-subtitle"),
  pageSelect: document.getElementById("page-select"),
  statusFilter: document.getElementById("status-filter"),
  pageLabel: document.getElementById("page-label"),
  pageMeta: document.getElementById("page-meta"),
  pageImage: document.getElementById("page-image"),
  viewerCanvas: document.getElementById("viewer-canvas"),
  overlay: document.getElementById("overlay"),
  pageCompleteBanner: document.getElementById("page-complete-banner"),
  floatingToolbar: document.getElementById("floating-toolbar"),
  floatingSelectionLabel: document.getElementById("floating-selection-label"),
  floatingClearSelection: document.getElementById("floating-clear-selection"),
  floatingPrevPage: document.getElementById("floating-prev-page"),
  floatingNextPage: document.getElementById("floating-next-page"),
  floatingNextUndecided: document.getElementById("floating-next-undecided"),
  floatingMarkCorrect: document.getElementById("floating-mark-correct"),
  floatingMarkWrong: document.getElementById("floating-mark-wrong"),
  floatingMarkSkipped: document.getElementById("floating-mark-skipped"),
  pageAuditTitle: document.getElementById("page-audit-title"),
  pageAuditStatus: document.getElementById("page-audit-status"),
  pageAuditNote: document.getElementById("page-audit-note"),
  pageMissingYes: document.getElementById("page-missing-yes"),
  pageMissingNo: document.getElementById("page-missing-no"),
  pageMissingClear: document.getElementById("page-missing-clear"),
  selectedTitle: document.getElementById("selected-title"),
  selectedStatus: document.getElementById("selected-status"),
  selectedDetails: document.getElementById("selected-details"),
  decisionNote: document.getElementById("decision-note"),
  itemsList: document.getElementById("items-list"),
  itemsCount: document.getElementById("items-count"),
  summaryTotal: document.getElementById("summary-total"),
  summaryReviewed: document.getElementById("summary-reviewed"),
  summaryCorrect: document.getElementById("summary-correct"),
  summaryWrong: document.getElementById("summary-wrong"),
  summaryPagesComplete: document.getElementById("summary-pages-complete"),
  markCorrect: document.getElementById("mark-correct"),
  markWrong: document.getElementById("mark-wrong"),
  markSkipped: document.getElementById("mark-skipped"),
  exportJson: document.getElementById("export-json"),
  exportCsv: document.getElementById("export-csv"),
  importJson: document.getElementById("import-json"),
  itemRowTemplate: document.getElementById("item-row-template"),
  authOverlay: document.getElementById("auth-overlay"),
  tokenInput: document.getElementById("token-input"),
  tokenSubmit: document.getElementById("token-submit"),
  tokenLocalOnly: document.getElementById("token-local-only"),
  tokenError: document.getElementById("token-error"),
};

function apiBaseUrl() {
  if (!state.config) return "";
  return state.config.apiBaseUrl || window.location.origin;
}

function authHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (state.authToken) {
    headers.Authorization = `Bearer ${state.authToken}`;
  }
  return headers;
}

function uniqueIds(reviewIds) {
  return [...new Set((reviewIds || []).filter(Boolean))];
}

function pageById(pageId) {
  return state.data?.pages.find((item) => item.pageId === pageId) || null;
}

function pageItems(pageId) {
  if (!state.data) return [];
  return state.data.items.filter((item) => item.pageId === pageId);
}

function pageIndex(pageId) {
  return state.data?.pages.findIndex((page) => page.pageId === pageId) ?? -1;
}

function getDecision(reviewId) {
  return state.decisions[reviewId] || { verdict: "undecided", note: "", updatedAt: null };
}

function getPageNote(pageId) {
  return state.pageNotes[pageId] || { hasMissingBoxes: null, note: "", updatedAt: null };
}

function getSelectionIds() {
  const ids = uniqueIds(state.selectedReviewIds).filter((reviewId) =>
    pageItems(state.currentPageId).some((item) => item.reviewId === reviewId),
  );
  if (ids.length) return ids;
  if (state.currentReviewId && pageItems(state.currentPageId).some((item) => item.reviewId === state.currentReviewId)) {
    return [state.currentReviewId];
  }
  return [];
}

function recomputeProgressByPage() {
  const progress = {};
  for (const page of state.data.pages) {
    const items = pageItems(page.pageId);
    const reviewed = items.filter((item) => getDecision(item.reviewId).verdict !== "undecided").length;
    progress[page.pageId] = {
      reviewed,
      total: items.length,
      completed: items.length > 0 && reviewed >= items.length,
    };
  }
  state.progressByPage = progress;
}

function persistDecisions() {
  if (!state.data) return;
  localStorage.setItem(state.data.site.localStorageKey, JSON.stringify(state.decisions));
}

function loadPersistedDecisions() {
  if (!state.data) return;
  try {
    const raw = localStorage.getItem(state.data.site.localStorageKey);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      state.decisions = parsed;
    }
  } catch (error) {
    console.warn("Failed to load saved decisions", error);
  }
}

function persistPageNotes() {
  if (!state.data) return;
  localStorage.setItem(`${state.data.site.localStorageKey}::page-notes`, JSON.stringify(state.pageNotes));
}

function loadPersistedPageNotes() {
  if (!state.data) return;
  try {
    const raw = localStorage.getItem(`${state.data.site.localStorageKey}::page-notes`);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object") {
      state.pageNotes = parsed;
    }
  } catch (error) {
    console.warn("Failed to load saved page notes", error);
  }
}

function persistToken(token) {
  if (!state.data) return;
  localStorage.setItem(`${state.data.site.localStorageKey}::token`, token);
}

function loadPersistedToken() {
  if (!state.data) return "";
  return localStorage.getItem(`${state.data.site.localStorageKey}::token`) || "";
}

function filteredItemsForPage(pageId) {
  return pageItems(pageId).filter((item) => {
    const verdict = getDecision(item.reviewId).verdict;
    if (state.statusFilter === "all") return true;
    if (state.statusFilter === "undecided") return verdict === "undecided";
    return verdict === state.statusFilter;
  });
}

function verdictLabel(verdict) {
  if (verdict === "correct") return "正确";
  if (verdict === "wrong") return "错误";
  if (verdict === "skipped") return "跳过";
  if (verdict === "multi") return "多选";
  return "未处理";
}

function setSelection(reviewIds, anchorReviewId = null) {
  const normalized = uniqueIds(reviewIds).filter((reviewId) =>
    pageItems(state.currentPageId).some((item) => item.reviewId === reviewId),
  );
  state.selectedReviewIds = normalized;
  state.currentReviewId = anchorReviewId || normalized[normalized.length - 1] || null;
}

function selectSingleReview(reviewId) {
  setSelection([reviewId], reviewId);
}

function toggleReviewSelection(reviewId) {
  const current = new Set(getSelectionIds());
  if (current.has(reviewId)) {
    current.delete(reviewId);
  } else {
    current.add(reviewId);
  }
  const next = [...current];
  setSelection(next, next.includes(reviewId) ? reviewId : next[next.length - 1] || null);
}

function selectionStatusCounts(reviewIds) {
  const counts = { undecided: 0, correct: 0, wrong: 0, skipped: 0 };
  for (const reviewId of reviewIds) {
    counts[getDecision(reviewId).verdict] += 1;
  }
  return counts;
}

function refreshSummary() {
  const all = state.data.items;
  const reviewed = all.filter((item) => getDecision(item.reviewId).verdict !== "undecided").length;
  const correct = all.filter((item) => getDecision(item.reviewId).verdict === "correct").length;
  const wrong = all.filter((item) => getDecision(item.reviewId).verdict === "wrong").length;
  const completePages = Object.values(state.progressByPage || {}).filter((item) => item?.completed).length;
  dom.summaryTotal.textContent = String(all.length);
  dom.summaryReviewed.textContent = String(reviewed);
  dom.summaryCorrect.textContent = String(correct);
  dom.summaryWrong.textContent = String(wrong);
  dom.summaryPagesComplete.textContent = String(completePages);
}

function pageAuditLabel(flag) {
  if (flag === true) return "有漏框";
  if (flag === false) return "无漏框";
  return "未处理";
}

function renderPageAudit() {
  const page = pageById(state.currentPageId);
  if (!page) return;
  const audit = getPageNote(page.pageId);
  dom.pageAuditTitle.textContent = `第 ${page.pageIndex || "?"} 页漏框判断`;
  dom.pageAuditStatus.textContent = pageAuditLabel(audit.hasMissingBoxes);
  dom.pageAuditStatus.className = `status-badge ${
    audit.hasMissingBoxes === true ? "wrong" : audit.hasMissingBoxes === false ? "correct" : "undecided"
  }`;
  dom.pageAuditNote.value = audit.note || "";
}

function renderPageSelector() {
  dom.pageSelect.innerHTML = "";
  for (const page of state.data.pages) {
    const option = document.createElement("option");
    option.value = page.pageId;
    const progress = state.progressByPage?.[page.pageId];
    const suffix = progress?.completed ? " · 已完成" : progress ? ` · ${progress.reviewed}/${progress.total}` : "";
    option.textContent = `第 ${page.pageIndex || "?"} 页 · ${page.pageId}${suffix}`;
    dom.pageSelect.appendChild(option);
  }
  dom.pageSelect.value = state.currentPageId;
}

function renderPageView() {
  const page = pageById(state.currentPageId);
  if (!page) return;
  if (dom.pageImage.getAttribute("src") !== page.imagePath) {
    dom.pageImage.src = page.imagePath;
  }
  const progress = state.progressByPage?.[page.pageId];
  const progressText = progress ? ` · 已完成 ${progress.reviewed}/${progress.total}` : "";
  dom.pageLabel.textContent = `第 ${page.pageIndex || "?"} 页`;
  dom.pageMeta.textContent = `${page.pageId} · ${filteredItemsForPage(page.pageId).length} 条当前筛选结果${progressText}`;
  dom.viewerCanvas.classList.toggle("page-complete", Boolean(progress?.completed));
  dom.pageCompleteBanner.classList.toggle("hidden", !progress?.completed);
}

function itemMetaText(item) {
  const guess = item.systemGuess?.label || item.visualCharText || "unknown";
  const confidence = item.detectionConfidence ? `置信度 ${Number(item.detectionConfidence).toFixed(3)}` : "无置信度";
  return `${guess} · ${confidence}`;
}

function rectIntersects(a, b) {
  return !(a.x2 < b.x1 || a.x1 > b.x2 || a.y2 < b.y1 || a.y1 > b.y2);
}

function currentMarqueeRect() {
  if (!state.marquee) return null;
  return {
    x1: Math.min(state.marquee.startX, state.marquee.currentX),
    y1: Math.min(state.marquee.startY, state.marquee.currentY),
    x2: Math.max(state.marquee.startX, state.marquee.currentX),
    y2: Math.max(state.marquee.startY, state.marquee.currentY),
  };
}

function renderOverlay() {
  const page = pageById(state.currentPageId);
  if (!page) return;
  const selectedIds = new Set(getSelectionIds());
  dom.overlay.innerHTML = "";
  dom.overlay.setAttribute("viewBox", `0 0 ${page.width || 1} ${page.height || 1}`);

  for (const item of pageItems(state.currentPageId)) {
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    const { x1, y1, x2, y2 } = item.bbox;
    rect.setAttribute("x", x1);
    rect.setAttribute("y", y1);
    rect.setAttribute("width", Math.max(1, x2 - x1));
    rect.setAttribute("height", Math.max(1, y2 - y1));
    rect.dataset.reviewId = item.reviewId;
    rect.classList.add("overlay-box");
    rect.classList.add(getDecision(item.reviewId).verdict);
    if (selectedIds.has(item.reviewId)) rect.classList.add("selected");
    if (item.reviewId === state.currentReviewId) rect.classList.add("active");
    rect.addEventListener("click", (event) => {
      event.stopPropagation();
      if (event.shiftKey || event.metaKey || event.ctrlKey) {
        toggleReviewSelection(item.reviewId);
      } else {
        selectSingleReview(item.reviewId);
      }
      renderPageItems();
      renderOverlay();
      renderSelection();
      renderFloatingToolbar();
    });
    dom.overlay.appendChild(rect);
  }

  const marquee = currentMarqueeRect();
  if (marquee) {
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", marquee.x1);
    rect.setAttribute("y", marquee.y1);
    rect.setAttribute("width", Math.max(1, marquee.x2 - marquee.x1));
    rect.setAttribute("height", Math.max(1, marquee.y2 - marquee.y1));
    rect.classList.add("selection-marquee");
    dom.overlay.appendChild(rect);
  }
}

function renderPageItems() {
  const selectedIds = new Set(getSelectionIds());
  const items = filteredItemsForPage(state.currentPageId);
  dom.itemsCount.textContent = `${items.length} 条`;
  dom.itemsList.innerHTML = "";

  for (const item of items) {
    const node = dom.itemRowTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".item-row-title").textContent = item.reviewId;
    node.querySelector(".item-row-meta").textContent = itemMetaText(item);
    const statusNode = node.querySelector(".item-row-status");
    const verdict = getDecision(item.reviewId).verdict;
    statusNode.textContent = verdictLabel(verdict);
    statusNode.className = `item-row-status ${verdict}`;
    node.classList.toggle("selected", selectedIds.has(item.reviewId));
    node.classList.toggle("active", item.reviewId === state.currentReviewId);
    node.addEventListener("click", (event) => {
      if (event.shiftKey || event.metaKey || event.ctrlKey) {
        toggleReviewSelection(item.reviewId);
      } else {
        selectSingleReview(item.reviewId);
      }
      renderPageItems();
      renderOverlay();
      renderSelection();
      renderFloatingToolbar();
    });
    dom.itemsList.appendChild(node);
  }
}

function detailRow(term, valueNode) {
  const fragment = document.createDocumentFragment();
  const dt = document.createElement("dt");
  dt.textContent = term;
  const dd = document.createElement("dd");
  if (valueNode instanceof Node) {
    dd.appendChild(valueNode);
  } else {
    dd.textContent = valueNode || "-";
  }
  fragment.append(dt, dd);
  return fragment;
}

function createPillRow(values) {
  const wrapper = document.createElement("div");
  wrapper.className = "pill-row";
  for (const value of values) {
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = value;
    wrapper.appendChild(pill);
  }
  return wrapper;
}

function renderSelection() {
  const selectedIds = getSelectionIds();
  if (!selectedIds.length) {
    dom.selectedTitle.textContent = "请选择一个框";
    dom.selectedStatus.textContent = "未处理";
    dom.selectedStatus.className = "status-badge undecided";
    dom.selectedDetails.innerHTML = "";
    dom.decisionNote.value = "";
    dom.decisionNote.disabled = true;
    dom.decisionNote.placeholder = "先选择一个框，再填写备注。";
    return;
  }

  if (selectedIds.length > 1) {
    const counts = selectionStatusCounts(selectedIds);
    dom.selectedTitle.textContent = `已选 ${selectedIds.length} 个框`;
    dom.selectedStatus.textContent = "多选";
    dom.selectedStatus.className = "status-badge multi";
    dom.selectedDetails.innerHTML = "";
    dom.selectedDetails.appendChild(detailRow("页号", `第 ${pageById(state.currentPageId)?.pageIndex || "?"} 页`));
    dom.selectedDetails.appendChild(detailRow("已选数量", String(selectedIds.length)));
    dom.selectedDetails.appendChild(
      detailRow(
        "状态分布",
        createPillRow([
          `未处理 ${counts.undecided}`,
          `正确 ${counts.correct}`,
          `错误 ${counts.wrong}`,
          `跳过 ${counts.skipped}`,
        ]),
      ),
    );
    dom.selectedDetails.appendChild(detailRow("批量规则", "点击悬浮工具条或右侧按钮，可一次给这批框统一判定。"));
    dom.decisionNote.value = "";
    dom.decisionNote.disabled = true;
    dom.decisionNote.placeholder = "批量选择时不支持统一备注，请单独点选某个框再写备注。";
    return;
  }

  const item = state.data.items.find((entry) => entry.reviewId === selectedIds[0]);
  if (!item) return;
  const decision = getDecision(item.reviewId);
  dom.selectedTitle.textContent = item.reviewId;
  dom.selectedStatus.textContent = verdictLabel(decision.verdict);
  dom.selectedStatus.className = `status-badge ${decision.verdict}`;
  dom.decisionNote.disabled = false;
  dom.decisionNote.placeholder = "可记录为什么判错，或需要后续怎么处理。";
  dom.decisionNote.value = decision.note || "";

  dom.selectedDetails.innerHTML = "";
  dom.selectedDetails.appendChild(detailRow("页号", `第 ${item.pageIndex || "?"} 页`));
  dom.selectedDetails.appendChild(detailRow("系统判断", item.systemGuess?.label || item.visualCharText || "-"));
  dom.selectedDetails.appendChild(
    detailRow("框置信度", item.detectionConfidence ? Number(item.detectionConfidence).toFixed(4) : "-"),
  );
  dom.selectedDetails.appendChild(detailRow("建议动作", item.suggestedAction || "-"));
  dom.selectedDetails.appendChild(detailRow("当前问题", createPillRow(item.currentIssues || ["无"])));
  dom.selectedDetails.appendChild(
    detailRow(
      "部件提示",
      createPillRow((item.componentHints || []).map((part) => `${part.slot}:${part.label}`) || ["无"]),
    ),
  );
}

function getSelectionBounds(reviewIds) {
  const items = reviewIds
    .map((reviewId) => state.data.items.find((item) => item.reviewId === reviewId))
    .filter(Boolean);
  if (!items.length) return null;
  return items.reduce(
    (bounds, item) => ({
      x1: Math.min(bounds.x1, item.bbox.x1),
      y1: Math.min(bounds.y1, item.bbox.y1),
      x2: Math.max(bounds.x2, item.bbox.x2),
      y2: Math.max(bounds.y2, item.bbox.y2),
    }),
    { x1: Number.POSITIVE_INFINITY, y1: Number.POSITIVE_INFINITY, x2: 0, y2: 0 },
  );
}

function hasUndecidedInPage(pageId) {
  return pageItems(pageId).some((item) => getDecision(item.reviewId).verdict === "undecided");
}

function getNextUndecidedReviewId(pageId, afterReviewIds = []) {
  const items = pageItems(pageId);
  if (!items.length) return null;
  const selected = new Set(afterReviewIds);
  let anchorIndex = -1;
  items.forEach((item, index) => {
    if (selected.has(item.reviewId)) {
      anchorIndex = Math.max(anchorIndex, index);
    }
  });
  for (let index = anchorIndex + 1; index < items.length; index += 1) {
    if (getDecision(items[index].reviewId).verdict === "undecided") return items[index].reviewId;
  }
  for (let index = 0; index <= anchorIndex; index += 1) {
    if (getDecision(items[index].reviewId).verdict === "undecided") return items[index].reviewId;
  }
  return null;
}

function updateActionButtons() {
  const pageDone = state.progressByPage?.[state.currentPageId]?.completed;
  const hasSelection = getSelectionIds().length > 0;
  const currentIndex = pageIndex(state.currentPageId);
  const hasPrevPage = currentIndex > 0;
  const hasNextPage = currentIndex >= 0 && currentIndex < state.data.pages.length - 1;
  const hasNextUndecided = Boolean(getNextUndecidedReviewId(state.currentPageId, getSelectionIds()));

  [dom.markCorrect, dom.markWrong, dom.markSkipped, dom.floatingMarkCorrect, dom.floatingMarkWrong, dom.floatingMarkSkipped].forEach(
    (button) => {
      button.disabled = !hasSelection;
    },
  );
  dom.floatingPrevPage.disabled = !hasPrevPage;
  dom.floatingNextPage.disabled = !hasNextPage;
  dom.floatingNextUndecided.disabled = pageDone || !hasNextUndecided;
  dom.floatingClearSelection.disabled = !hasSelection;
}

function renderFloatingToolbar() {
  if (!state.data || !state.currentPageId) {
    dom.floatingToolbar.classList.add("hidden");
    return;
  }
  const selectedIds = getSelectionIds();
  const pageDone = state.progressByPage?.[state.currentPageId]?.completed;
  if (selectedIds.length > 1) {
    dom.floatingSelectionLabel.textContent = `已选 ${selectedIds.length} 个框`;
  } else if (selectedIds.length === 1) {
    dom.floatingSelectionLabel.textContent = selectedIds[0];
  } else if (pageDone) {
    dom.floatingSelectionLabel.textContent = "本页已完成";
  } else {
    dom.floatingSelectionLabel.textContent = "请选择一个框";
  }

  updateActionButtons();
  dom.floatingToolbar.classList.remove("hidden");
  const viewerRect = dom.viewerCanvas.getBoundingClientRect();
  if (!viewerRect.width) return;
  dom.floatingToolbar.style.left = `${viewerRect.left + viewerRect.width / 2}px`;
  dom.floatingToolbar.style.bottom = "16px";
  dom.floatingToolbar.style.transform = "translateX(-50%)";
}

function selectDefaultForCurrentPage() {
  const currentSelection = getSelectionIds();
  if (currentSelection.length) {
    setSelection(currentSelection, state.currentReviewId || currentSelection[0]);
    return;
  }
  if (state.progressByPage?.[state.currentPageId]?.completed) {
    setSelection([], null);
    return;
  }
  const nextUndecided = getNextUndecidedReviewId(state.currentPageId);
  if (nextUndecided) {
    selectSingleReview(nextUndecided);
    return;
  }
  const items = filteredItemsForPage(state.currentPageId);
  if (items.length) {
    selectSingleReview(items[0].reviewId);
    return;
  }
  setSelection([], null);
}

function render() {
  recomputeProgressByPage();
  renderPageSelector();
  renderPageView();
  renderPageAudit();
  selectDefaultForCurrentPage();
  renderOverlay();
  renderPageItems();
  renderSelection();
  refreshSummary();
  renderFloatingToolbar();
}

function downloadText(filename, content, contentType) {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function exportDecisionsJson() {
  const payload = {
    site: state.data.site,
    exportedAt: new Date().toISOString(),
    decisions: state.decisions,
    pageNotes: state.pageNotes,
  };
  downloadText("review-decisions.json", JSON.stringify(payload, null, 2), "application/json");
}

function exportDecisionsCsv() {
  const rows = [["review_id", "verdict", "note", "updated_at"]];
  for (const item of state.data.items) {
    const decision = getDecision(item.reviewId);
    if (decision.verdict === "undecided" && !decision.note) continue;
    rows.push([
      item.reviewId,
      decision.verdict,
      (decision.note || "").replaceAll("\n", " "),
      decision.updatedAt || "",
    ]);
  }
  const content = rows
    .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(","))
    .join("\n");
  downloadText("review-decisions.csv", `${content}\n`, "text/csv;charset=utf-8");
}

function importDecisionsJson(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(String(reader.result || "{}"));
      if (!payload.decisions || typeof payload.decisions !== "object") {
        throw new Error("invalid payload");
      }
      state.decisions = payload.decisions;
      state.pageNotes = payload.pageNotes && typeof payload.pageNotes === "object" ? payload.pageNotes : state.pageNotes;
      persistDecisions();
      persistPageNotes();
      render();
    } catch (error) {
      alert("导入失败，请确认文件是这个页面导出的 JSON。");
    }
  };
  reader.readAsText(file, "utf-8");
}

async function submitDecision(reviewId, decision) {
  const response = await fetch(`${apiBaseUrl()}/api/decision`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      siteId: state.data.site.siteId,
      reviewId,
      verdict: decision.verdict,
      note: decision.note || "",
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to submit decision: ${response.status}`);
  }
  const payload = await response.json();
  state.progressByPage = { ...state.progressByPage, ...(payload.progressByPage || {}) };
  state.pageNotes = payload.pageNotes || state.pageNotes;
}

async function loadRemoteState() {
  const response = await fetch(`${apiBaseUrl()}/api/bootstrap?siteId=${encodeURIComponent(state.data.site.siteId)}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(`bootstrap failed: ${response.status}`);
  }
  const payload = await response.json();
  state.decisions = payload.decisions || {};
  state.progressByPage = payload.progressByPage || {};
  state.pageNotes = payload.pageNotes || {};
  persistDecisions();
  persistPageNotes();
}

async function connectWithToken(token) {
  dom.tokenError.textContent = "";
  if (!token) {
    dom.tokenError.textContent = "请输入 token。";
    return;
  }
  try {
    state.authToken = token;
    const response = await fetch(`${apiBaseUrl()}/api/auth`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ siteId: state.data.site.siteId }),
    });
    if (!response.ok) {
      throw new Error(`auth failed: ${response.status}`);
    }
    state.remoteEnabled = true;
    persistToken(token);
    await loadRemoteState();
    dom.authOverlay.classList.add("hidden");
    render();
  } catch (error) {
    console.error(error);
    state.remoteEnabled = false;
    dom.tokenError.textContent = "token 无效，或当前结果服务不可用。";
  }
}

async function setDecisionBatch(reviewIds, patch) {
  const ids = uniqueIds(reviewIds);
  if (!ids.length) return;
  const nextById = {};
  for (const reviewId of ids) {
    nextById[reviewId] = {
      ...getDecision(reviewId),
      ...patch,
      updatedAt: new Date().toISOString(),
    };
    state.decisions[reviewId] = nextById[reviewId];
  }
  persistDecisions();
  recomputeProgressByPage();
  render();

  if (state.remoteEnabled) {
    try {
      await Promise.all(ids.map((reviewId) => submitDecision(reviewId, nextById[reviewId])));
    } catch (error) {
      console.error(error);
      dom.tokenError.textContent = "远端保存失败，结果仍保存在当前浏览器。";
    }
  }
}

async function submitPageNote(pageId, payload) {
  const response = await fetch(`${apiBaseUrl()}/api/page-note`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      siteId: state.data.site.siteId,
      pageId,
      hasMissingBoxes: payload.hasMissingBoxes,
      note: payload.note || "",
    }),
  });
  if (!response.ok) {
    throw new Error(`Failed to submit page note: ${response.status}`);
  }
  const body = await response.json();
  state.progressByPage = { ...state.progressByPage, ...(body.progressByPage || {}) };
  state.pageNotes = body.pageNotes || state.pageNotes;
}

async function setPageMissingFlag(hasMissingBoxes) {
  const pageId = state.currentPageId;
  if (!pageId) return;
  const next = {
    ...getPageNote(pageId),
    hasMissingBoxes,
    updatedAt: new Date().toISOString(),
  };
  state.pageNotes[pageId] = next;
  persistPageNotes();
  renderPageAudit();
  if (state.remoteEnabled) {
    try {
      await submitPageNote(pageId, next);
    } catch (error) {
      console.error(error);
      dom.tokenError.textContent = "远端保存页级漏框结果失败，结果仍保存在当前浏览器。";
    }
  }
}

async function updatePageAuditNote(note) {
  const pageId = state.currentPageId;
  if (!pageId) return;
  const next = {
    ...getPageNote(pageId),
    note,
    updatedAt: new Date().toISOString(),
  };
  state.pageNotes[pageId] = next;
  persistPageNotes();
  if (state.remoteEnabled) {
    try {
      await submitPageNote(pageId, next);
    } catch (error) {
      console.error(error);
      dom.tokenError.textContent = "远端保存页级备注失败，结果仍保存在当前浏览器。";
    }
  }
}

function advanceToNextUndecided(afterIds) {
  const nextReviewId = getNextUndecidedReviewId(state.currentPageId, afterIds);
  if (nextReviewId) {
    selectSingleReview(nextReviewId);
  } else {
    setSelection([], null);
  }
}

async function applyVerdict(verdict) {
  const selectedIds = getSelectionIds();
  if (!selectedIds.length) return;
  await setDecisionBatch(selectedIds, { verdict });
  if (state.progressByPage?.[state.currentPageId]?.completed) {
    setSelection([], null);
  } else {
    advanceToNextUndecided(selectedIds);
  }
  render();
}

async function updateSingleNote(note) {
  const selectedIds = getSelectionIds();
  if (selectedIds.length !== 1) return;
  await setDecisionBatch(selectedIds, { note });
  render();
}

function goToPage(nextPageId) {
  if (!nextPageId || nextPageId === state.currentPageId) return;
  state.currentPageId = nextPageId;
  setSelection([], null);
  render();
}

function goToPageByOffset(offset) {
  const index = pageIndex(state.currentPageId);
  if (index < 0) return;
  const next = state.data.pages[index + offset];
  if (!next) return;
  goToPage(next.pageId);
}

function goToNextUndecided() {
  const nextReviewId = getNextUndecidedReviewId(state.currentPageId, getSelectionIds());
  if (!nextReviewId) return;
  selectSingleReview(nextReviewId);
  render();
}

function pagePointFromPointer(event) {
  const page = pageById(state.currentPageId);
  const rect = dom.overlay.getBoundingClientRect();
  if (!page || !rect.width || !rect.height) return null;
  const x = ((event.clientX - rect.left) / rect.width) * page.width;
  const y = ((event.clientY - rect.top) / rect.height) * page.height;
  return {
    x: Math.min(Math.max(x, 0), page.width),
    y: Math.min(Math.max(y, 0), page.height),
  };
}

function finalizeMarqueeSelection(cancelled = false) {
  const marquee = currentMarqueeRect();
  const append = state.marquee?.append;
  state.marquee = null;
  if (cancelled || !marquee) {
    renderOverlay();
    renderFloatingToolbar();
    return;
  }

  const width = marquee.x2 - marquee.x1;
  const height = marquee.y2 - marquee.y1;
  if (width < 12 || height < 12) {
    renderOverlay();
    renderFloatingToolbar();
    return;
  }

  const matched = pageItems(state.currentPageId)
    .filter((item) => rectIntersects(marquee, item.bbox))
    .map((item) => item.reviewId);
  if (matched.length) {
    if (append) {
      setSelection([...getSelectionIds(), ...matched], matched[matched.length - 1]);
    } else {
      setSelection(matched, matched[matched.length - 1]);
    }
  } else if (!append) {
    setSelection([], null);
  }
  renderPageItems();
  renderOverlay();
  renderSelection();
  renderFloatingToolbar();
}

function bindCanvasSelection() {
  dom.viewerCanvas.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    if (event.target.closest(".overlay-box") || event.target.closest(".floating-toolbar")) return;
    const point = pagePointFromPointer(event);
    if (!point) return;
    state.marquee = {
      pointerId: event.pointerId,
      startX: point.x,
      startY: point.y,
      currentX: point.x,
      currentY: point.y,
      append: event.shiftKey || event.metaKey || event.ctrlKey,
    };
    dom.viewerCanvas.setPointerCapture?.(event.pointerId);
    renderOverlay();
    renderFloatingToolbar();
  });

  dom.viewerCanvas.addEventListener("pointermove", (event) => {
    if (!state.marquee || state.marquee.pointerId !== event.pointerId) return;
    const point = pagePointFromPointer(event);
    if (!point) return;
    state.marquee.currentX = point.x;
    state.marquee.currentY = point.y;
    renderOverlay();
  });

  dom.viewerCanvas.addEventListener("pointerup", (event) => {
    if (!state.marquee || state.marquee.pointerId !== event.pointerId) return;
    dom.viewerCanvas.releasePointerCapture?.(event.pointerId);
    finalizeMarqueeSelection(false);
  });

  dom.viewerCanvas.addEventListener("pointercancel", (event) => {
    if (!state.marquee || state.marquee.pointerId !== event.pointerId) return;
    dom.viewerCanvas.releasePointerCapture?.(event.pointerId);
    finalizeMarqueeSelection(true);
  });
}

function bindEvents() {
  dom.pageSelect.addEventListener("change", (event) => {
    goToPage(event.target.value);
  });
  dom.statusFilter.addEventListener("change", (event) => {
    state.statusFilter = event.target.value;
    render();
  });
  dom.markCorrect.addEventListener("click", async () => applyVerdict("correct"));
  dom.markWrong.addEventListener("click", async () => applyVerdict("wrong"));
  dom.markSkipped.addEventListener("click", async () => applyVerdict("skipped"));
  dom.floatingMarkCorrect.addEventListener("click", async () => applyVerdict("correct"));
  dom.floatingMarkWrong.addEventListener("click", async () => applyVerdict("wrong"));
  dom.floatingMarkSkipped.addEventListener("click", async () => applyVerdict("skipped"));
  dom.floatingPrevPage.addEventListener("click", () => goToPageByOffset(-1));
  dom.floatingNextPage.addEventListener("click", () => goToPageByOffset(1));
  dom.floatingNextUndecided.addEventListener("click", () => goToNextUndecided());
  dom.floatingClearSelection.addEventListener("click", () => {
    setSelection([], null);
    render();
  });
  dom.pageMissingYes.addEventListener("click", async () => setPageMissingFlag(true));
  dom.pageMissingNo.addEventListener("click", async () => setPageMissingFlag(false));
  dom.pageMissingClear.addEventListener("click", async () => setPageMissingFlag(null));
  dom.pageAuditNote.addEventListener("change", async (event) => {
    await updatePageAuditNote(event.target.value);
  });
  dom.decisionNote.addEventListener("change", async (event) => {
    await updateSingleNote(event.target.value);
  });
  dom.exportJson.addEventListener("click", exportDecisionsJson);
  dom.exportCsv.addEventListener("click", exportDecisionsCsv);
  dom.importJson.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    importDecisionsJson(file);
    event.target.value = "";
  });
  dom.tokenSubmit.addEventListener("click", async () => {
    await connectWithToken(dom.tokenInput.value.trim());
  });
  dom.tokenLocalOnly.addEventListener("click", () => {
    state.remoteEnabled = false;
    dom.authOverlay.classList.add("hidden");
    dom.tokenError.textContent = "";
  });
  window.addEventListener("resize", renderFloatingToolbar);
  window.addEventListener("scroll", renderFloatingToolbar, { passive: true });
  dom.pageImage.addEventListener("load", () => {
    renderOverlay();
    renderFloatingToolbar();
  });
  bindCanvasSelection();
}

async function loadConfig() {
  const response = await fetch("./data/review-config.json", { cache: "no-store" });
  if (!response.ok) {
    return {
      apiBaseUrl: "",
      requireToken: false,
      siteId: "",
      siteTitle: "",
    };
  }
  return response.json();
}

async function loadData() {
  const response = await fetch("./data/review-data.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load review data: ${response.status}`);
  }
  state.data = await response.json();
  state.config = await loadConfig();
  state.currentPageId = state.data.pages[0]?.pageId || null;
  loadPersistedDecisions();
  loadPersistedPageNotes();
  state.authToken = loadPersistedToken();
  dom.siteTitle.textContent = state.data.site.title;
  dom.siteSubtitle.textContent = `${state.data.site.sourceId} · ${state.data.site.batchId} · ${state.data.summary.itemCount} 条`;

  if (state.config.requireToken) {
    dom.authOverlay.classList.remove("hidden");
    if (state.authToken) {
      dom.tokenInput.value = state.authToken;
      await connectWithToken(state.authToken);
    }
  } else if (state.config.apiBaseUrl) {
    try {
      await loadRemoteState();
      state.remoteEnabled = true;
    } catch (error) {
      console.warn("Remote state unavailable, fallback to local-only mode", error);
      state.remoteEnabled = false;
    }
  }

  render();
}

async function main() {
  bindEvents();
  try {
    await loadData();
  } catch (error) {
    console.error(error);
    dom.siteSubtitle.textContent = "加载失败，请确认 data/review-data.json 已存在。";
  }
}

if (typeof window !== "undefined") {
  window.__reviewStudio = {
    state,
    render,
    applyVerdict,
    goToPage,
    goToPageByOffset,
    goToNextUndecided,
    selectSingleReview,
    setSelection,
    getSelectionIds,
    getNextUndecidedReviewId,
    finalizeMarqueeSelection,
  };
}

main();
