const bootstrapNode = document.getElementById("bootstrap-data");
const bootstrap = bootstrapNode ? JSON.parse(bootstrapNode.textContent || "{}") : {};

const screens = {
  auth: document.getElementById("auth-shell"),
  onboarding: document.getElementById("onboarding-shell"),
  kite: document.getElementById("kite-shell"),
  transition: document.getElementById("transition-shell"),
  app: document.getElementById("app-shell"),
};

const form = document.getElementById("analysis-form");
const queryInput = document.getElementById("query");
const thoughtsInput = document.getElementById("thoughts");
const intervalInput = document.getElementById("chart-interval");
const agentPresetInput = document.getElementById("agent-preset");
const snapshotInput = document.getElementById("include-snapshot");
const progressLog = document.getElementById("progress-log");
const progressBar = document.getElementById("progress-bar");
const progressPill = document.getElementById("progress-pill");
const resultBoard = document.getElementById("result-board");
const loadingScreen = document.getElementById("loading-screen");
const loadingMessage = document.getElementById("loading-message");
const loadingOverlayMessage = document.getElementById("loading-overlay-message");
const progressEstimate = document.getElementById("progress-estimate");
const loadingEstimate = document.getElementById("loading-estimate");
const transitionHelper = document.getElementById("transition-helper");
const googleLoginButton = document.getElementById("google-login-button");
const heroLoginButton = document.getElementById("hero-login-button");
const authHelper = document.getElementById("auth-helper");
const kiteYesButton = document.getElementById("kite-yes-button");
const kiteNoButton = document.getElementById("kite-no-button");
const kiteConnectButton = document.getElementById("kite-connect-button");
const kiteRefreshButton = document.getElementById("kite-refresh-button");
const kiteSkipButton = document.getElementById("kite-skip-button");
const kiteStatusCard = document.getElementById("kite-status-card");
const profileMenuButton = document.getElementById("profile-menu-button");
const profileDropdown = document.getElementById("profile-dropdown");
const logoutButton = document.getElementById("logout-button");
const userName = document.getElementById("user-name");
const userEmail = document.getElementById("user-email");
const userAvatar = document.getElementById("user-avatar");
const heroKiteStatus = document.getElementById("hero-kite-status");
const providerVisibility = document.getElementById("provider-visibility");
const dashboardSourceNote = document.getElementById("dashboard-source-note");
const dashboardSessionPill = document.getElementById("dashboard-session-pill");
const marketDataPanel = document.getElementById("market-data-panel");
const portfolioPanel = document.getElementById("portfolio-panel");
const watchlistPanel = document.getElementById("watchlist-panel");
const knowledgePanel = document.getElementById("knowledge-panel");
const infrastructurePanel = document.getElementById("infrastructure-panel");
const agentHelper = document.getElementById("agent-helper");
const agentPanel = document.getElementById("agent-panel");
const addWatchlistButton = document.getElementById("add-watchlist-button");
const dashboardConnectKiteButton = document.getElementById("dashboard-connect-kite-button");
const sideConnectKiteButton = document.getElementById("side-connect-kite-button");
const feedbackFab = document.getElementById("feedback-fab");
const feedbackPanel = document.getElementById("feedback-panel");
const feedbackClose = document.getElementById("feedback-close");
const feedbackSubmit = document.getElementById("feedback-submit");
const feedbackMessage = document.getElementById("feedback-message");
const feedbackStatus = document.getElementById("feedback-status");
const resultToolbar = document.getElementById("result-toolbar");
const resultHomeButton = document.getElementById("result-home-button");
const resultSearchForm = document.getElementById("result-search-form");
const resultSearchInput = document.getElementById("result-search-input");

let appState = bootstrap;
let currentEventSource = null;
let highestProgress = 0;
let firebaseAuthContext = null;
let activeScreen = "auth";
let kiteStatusPoller = null;
let kitePollingAttempts = 0;
let kiteSyncInFlight = false;

function showScreen(key) {
  activeScreen = key;
  document.body.dataset.screen = key;
  Object.entries(screens).forEach(([name, element]) => {
    if (!element) return;
    element.classList.toggle("hidden", name !== key);
  });
}

function formatValue(value, fallback = "N/A", suffix = "") {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return fallback;
  }
  return `${value}${suffix}`;
}

function createTile(label, value, tone = "") {
  return `
    <div class="tile ${tone}">
      <div class="tile-label">${label}</div>
      <div class="tile-value">${value}</div>
    </div>
  `;
}

function createBadge(value, tone = "") {
  return `<span class="mini-badge ${tone}">${value}</span>`;
}

function initials(name) {
  if (!name) return "G";
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("");
}

function setTransitionMessage(text) {
  if (transitionHelper) transitionHelper.textContent = text;
}

function setLoadingOverlayMessage(text) {
  if (loadingOverlayMessage) loadingOverlayMessage.textContent = text;
}

function setLoadingEstimate(text) {
  if (loadingEstimate) loadingEstimate.textContent = text || "";
  if (progressEstimate) progressEstimate.textContent = text || "Signals update as the run advances.";
}

function formatClock(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch (_) {
    return "";
  }
}

function formatRelativeMoment(value) {
  if (!value) return "";
  try {
    const date = new Date(value);
    return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch (_) {
    return "";
  }
}

function renderProviderVisibility() {
  if (!providerVisibility) return;
  const providers = appState.market_data?.providers || [];
  providerVisibility.innerHTML = providers
    .map((provider) =>
      createBadge(
        `${provider.label}${provider.available ? "" : " • pending"}`,
        provider.available ? "tone-green" : "tone-yellow"
      )
    )
    .join("");
}

function renderMarketDataPanel() {
  if (!marketDataPanel) return;
  const marketData = appState.market_data || {};
  const providerLabels = (marketData.providers || [])
    .map((provider) => `${provider.label}${provider.available ? "" : " (pending)"}`)
    .join(" -> ");
  marketDataPanel.innerHTML = `
    <p class="muted">${providerLabels || "Provider stack unavailable."}</p>
    <div class="placeholder-pills">
      ${(marketData.order || []).map((item) => createBadge(item.replaceAll("_", " "), "tone-yellow")).join("")}
    </div>
  `;
}

function agentOptions() {
  return appState.agents?.selectable || appState.agents?.summary?.selectable || [];
}

function selectedAgentMeta() {
  const selectedId = agentPresetInput?.value || "auto";
  return agentOptions().find((item) => item.id === selectedId) || agentOptions()[0] || null;
}

function renderAgentHelper() {
  if (!agentHelper) return;
  const selected = selectedAgentMeta();
  if (!selected) {
    agentHelper.textContent = "Choose a local research agent to bias the workflow.";
    return;
  }
  const bestFor = (selected.best_for || []).slice(0, 2).join(", ");
  agentHelper.textContent = `${selected.description}${bestFor ? ` Best for ${bestFor}.` : ""}`;
}

function renderAgentPanel() {
  if (!agentPanel) return;
  const options = agentOptions();
  if (!options.length) {
    agentPanel.textContent = "Local research agents are not loaded yet.";
    return;
  }
  agentPanel.innerHTML = `
    <p class="muted">Local-only research agents route the same data through different decision lenses. They do not send extra personal data anywhere.</p>
    <div class="placeholder-pills">
      ${options
        .slice(1)
        .map((item) => createBadge(item.label, `tone-${item.tone || "yellow"}`))
        .join("")}
    </div>
  `;
}

function renderKiteStatus() {
  if (!kiteStatusCard) return;
  const kite = appState.kite || {};
  kiteStatusCard.innerHTML = `
    <div class="status-board-grid">
      ${createTile("Bridge", kite.bridge_ready ? "Ready" : "Pending", kite.bridge_ready ? "tile-positive" : "")}
      ${createTile("Connection", kite.kite_connected ? "Connected" : "Not connected")}
      ${createTile("Mode", kite.mode || "N/A")}
    </div>
    <p class="muted">${kite.message || "No Kite status available."}</p>
    <div class="placeholder-pills">
      ${createBadge(`Hosted endpoint: ${kite.hosted_endpoint || "N/A"}`, "tone-yellow")}
      ${createBadge(`Bridge URL: ${kite.bridge_base_url || "Not configured"}`)}
    </div>
  `;
}

function renderUserCard() {
  const user = appState.session;
  const displayName = user?.name || "Guest";
  const displayEmail = user?.email || "No active session";
  if (userName) userName.textContent = displayName;
  if (userEmail) userEmail.textContent = displayEmail;
  if (userAvatar) userAvatar.textContent = initials(displayName);
  if (dashboardSessionPill) {
    dashboardSessionPill.textContent = user ? "Session live" : "Guest";
    dashboardSessionPill.className = `status-chip ${user ? "chip-green" : "chip-yellow"}`;
  }
}

function renderHeroMeta() {
  const user = appState.session;
  const marketData = appState.market_data || {};
  const sourceCopy = user
    ? `Welcome back, ${user.name || "there"}. Live data flows through ${(marketData.order || []).join(" -> ")}.`
    : "Provider visibility, stock intelligence, and portfolio context stay in one cleaner workflow.";
  if (dashboardSourceNote) dashboardSourceNote.textContent = sourceCopy;
  if (heroKiteStatus) {
    const kite = appState.kite || {};
    heroKiteStatus.textContent = kite.kite_connected ? "Connected" : kite.bridge_ready ? "Bridge ready" : "Pending setup";
  }
}

function renderWatchlist() {
  const items = appState.watchlist || [];
  if (!watchlistPanel) return;
  if (!items.length) {
    watchlistPanel.innerHTML = `<p class="muted">No watchlist items yet. Save the first symbol from any run to keep your radar active.</p>`;
    return;
  }
  watchlistPanel.innerHTML = items
    .map(
      (item) => `
        <div class="watchlist-item">
          <strong>${item.symbol}</strong>
          <p>${item.note || "No note added yet."}</p>
        </div>
      `
    )
    .join("");
}

function renderKnowledgePanel() {
  const knowledge = appState.knowledge || {};
  if (!knowledgePanel) return;
  knowledgePanel.innerHTML = `
    <p class="muted">${knowledge.count || 0} registered sources across ${(knowledge.categories || []).join(", ") || "general"}.</p>
    <div class="placeholder-pills">
      ${(knowledge.categories || []).slice(0, 4).map((item) => createBadge(item)).join("")}
    </div>
  `;
}

function renderInfrastructurePanel() {
  if (!infrastructurePanel) return;
  const infrastructure = appState.infrastructure || {};
  const postgres = infrastructure.postgres || {};
  const firestore = infrastructure.firestore || {};
  infrastructurePanel.innerHTML = `
    <div class="status-board-grid">
      ${createTile("Postgres", postgres.ready ? "Ready" : postgres.dsn_configured ? "Configured" : "Pending")}
      ${createTile("Firestore", firestore.credentials_ready ? "Configured" : "Pending")}
    </div>
    <p class="muted">Storage mode: ${postgres.mode || "local-json-fallback"}</p>
    ${postgres.message ? `<p class="muted">${postgres.message}</p>` : ""}
    <p class="muted">Feedback collection: ${firestore.collection || "feedback"}</p>
  `;
}

function renderPortfolio() {
  const payload = appState.portfolio || {};
  const insights = payload.insights || {};
  const kite = appState.kite || {};
  const snapshot = payload.latest_snapshot || null;
  const statusMessage =
    payload.sync_message ||
    insights.message ||
    payload.holdings_status?.message ||
    payload.positions_status?.message ||
    kite.message ||
    "Kite portfolio is not connected yet.";
  if (!portfolioPanel) return;

  if (!insights.available) {
    const snapshotSummary = snapshot?.summary || {};
    portfolioPanel.innerHTML = `
      <div class="module-stack">
        <p class="muted">${statusMessage}</p>
        ${
          snapshot
            ? `
            <div class="status-board-grid compact-grid">
              ${createTile("Last Sync Value", formatValue(snapshotSummary.total_value))}
              ${createTile("Diversification", snapshotSummary.diversification_view || "N/A")}
              ${createTile("Concentration", snapshotSummary.concentration_risk || "N/A")}
            </div>
            <p class="muted compact-note">Last successful sync: ${formatRelativeMoment(snapshot.createdAt)}</p>
          `
            : `
            <div class="placeholder-pills">
              ${createBadge("Personalized holdings")}
              ${createBadge("P&L overview")}
              ${createBadge("Concentration risk")}
            </div>
          `
        }
      </div>
    `;
    return;
  }

  const summary = insights.summary || {};
  const riskItems = (insights.risk_summary || []).map((item) => `<li>${item}</li>`).join("");
  const convictionItems = (insights.conviction_insights || [])
    .slice(0, 4)
    .map(
      (item) => `
        <div class="mini-list-item">
          <strong>${item.symbol}</strong>
          <span>${item.label} • Conviction ${formatValue(item.conviction)}</span>
        </div>
      `
    )
    .join("");

  portfolioPanel.innerHTML = `
    <div class="module-stack">
      <div class="status-board-grid">
      ${createTile("Total Value", formatValue(summary.total_value))}
      ${createTile("Total P&L", formatValue(summary.total_pnl))}
      ${createTile("Diversification", summary.diversification_view || "N/A")}
      ${createTile("Concentration", summary.concentration_risk || "N/A")}
      </div>
      ${payload.sync_message ? `<p class="muted compact-note">${payload.sync_message}</p>` : ""}
      <div class="mini-list">${convictionItems}</div>
      <ul class="list">${riskItems}</ul>
    </div>
  `;
}

function renderRequestContext(context) {
  if (!context) return "";
  const focusBadges = (context.focus_labels || []).map((label) => createBadge(label, "tone-green")).join("");
  const noteItems = (context.notes_highlights || []).map((item) => `<li>${item}</li>`).join("");
  const frameworkItems = (context.framework_steps || []).map((item) => `<li>${item}</li>`).join("");
  const checklistItems = (context.thinking_checklist || []).map((item) => `<li>${item}</li>`).join("");

  return `
    <section class="brief-section glass-card">
      <div class="section-title">
        <div>
          <p class="eyebrow">Prompt Intelligence</p>
          <h2>The engine's read of your request</h2>
        </div>
      </div>
      <div class="metric-grid">
        ${createTile("Run Type", context.mode_label)}
        ${createTile("Time Horizon", context.time_horizon_label)}
        ${createTile("Detected Stocks", (context.symbols || []).join(", "))}
      </div>
      <div class="thought-grid">
        <div class="tile">
          <div class="tile-label">Intent summary</div>
          <div class="muted">${context.intent_summary}</div>
        </div>
        <div class="tile">
          <div class="tile-label">Organized prompt</div>
          <div class="muted">${context.organized_prompt}</div>
        </div>
      </div>
      <div class="badge-row">${focusBadges}</div>
      ${noteItems ? `<div class="tile"><div class="tile-label">Your notes, cleaned up</div><ul class="list">${noteItems}</ul></div>` : ""}
      <div class="thought-grid">
        <div class="tile">
          <div class="tile-label">How to think about it</div>
          <ul class="list">${frameworkItems}</ul>
        </div>
        <div class="tile">
          <div class="tile-label">Questions to answer</div>
          <ul class="list">${checklistItems}</ul>
        </div>
      </div>
    </section>
  `;
}

function renderComparison(comparison) {
  if (!comparison || !comparison.table || !comparison.table.length) return "";
  const tiles = comparison.table
    .map(
      (row) => `
        <div class="tile compare-tile">
          <div class="tile-label">${row.symbol}</div>
          <div class="tile-value">${row.decision}</div>
          <p class="muted">Conviction ${formatValue(row.conviction)} | LT ${formatValue(row.long_term_score)} | Swing ${formatValue(row.swing_score)}</p>
          <p class="muted">PE ${formatValue(row.trailing_pe)} | Div ${formatValue(row.dividend_yield, "N/A", "%")}</p>
        </div>
      `
    )
    .join("");
  return `
    <section class="compare-section glass-card">
      <div class="section-title">
        <div>
          <p class="eyebrow">Compare View</p>
          <h2>Quick ranking</h2>
        </div>
      </div>
      <div class="compare-grid">${tiles}</div>
      <div class="metric-grid">
        ${createTile("Best Long-Term", comparison.summary.best_long_term)}
        ${createTile("Best Swing", comparison.summary.best_swing)}
        ${createTile("Lowest Risk", comparison.summary.lowest_risk)}
        ${comparison.summary.best_fit_for_prompt ? createTile("Best Fit For Prompt", comparison.summary.best_fit_for_prompt) : ""}
        ${comparison.summary.agent_lens ? createTile("Agent Lens", comparison.summary.agent_lens) : ""}
      </div>
    </section>
  `;
}

function renderAgentLens(context) {
  const agent = context?.agent;
  if (!agent?.label) return "";
  const workflowItems = (agent.workflow || []).map((item) => `<li>${item}</li>`).join("");
  return `
    <section class="agent-section glass-card">
      <div class="section-title">
        <div>
          <p class="eyebrow">Research Agent</p>
          <h2>${agent.label}</h2>
        </div>
        <span class="status-chip chip-${agent.tone || "yellow"}">${agent.selection_mode === "manual" ? "Manual" : "Auto"}</span>
      </div>
      <p class="muted">${agent.description || "This run used a local research lens."}</p>
      <div class="badge-row">
        ${createBadge(agent.selection_reason || "Local preset applied.", `tone-${agent.tone || "yellow"}`)}
        ${(agent.best_for || []).slice(0, 3).map((item) => createBadge(item)).join("")}
      </div>
      ${workflowItems ? `<ul class="list">${workflowItems}</ul>` : ""}
    </section>
  `;
}

function renderNews(news) {
  if (!news || !news.length) {
    return `<div class="tile"><div class="tile-label">Latest headlines</div><div class="muted">No recent headlines were returned by the data feed.</div></div>`;
  }
  return news
    .map(
      (item) => `
        <article class="tile news-card">
          <div class="tile-label">${item.publisher || "Market feed"}${item.published_at ? ` • ${item.published_at}` : ""}</div>
          <div class="tile-value"><a href="${item.url || "#"}" target="_blank" rel="noreferrer">${item.title || "Headline unavailable"}</a></div>
          <p class="muted">${item.summary || "Open the headline for more context."}</p>
        </article>
      `
    )
    .join("");
}

function renderSnapshot(snapshot) {
  if (!snapshot || snapshot.status !== "ready") return "";
  return `
    <div class="tile snapshot-card">
      <div class="tile-label">TradingView Snapshot • ${snapshot.symbol} • ${snapshot.interval}</div>
      <img src="${snapshot.image_url}" alt="TradingView snapshot for ${snapshot.symbol}" />
    </div>
  `;
}

function renderReport(report) {
  const summary = report.summary;
  const technicals = report.technicals;
  const fundamentals = report.fundamentals;
  const swing = report.swing_plan;
  const risks = report.risks;
  const reasoning = report.reasoning_context || {};
  const selectedAgent = reasoning.agent || {};

  const summaryTiles = [
    createTile("Current Price", formatValue(summary.current_price)),
    createTile("Market Cap", report.display.market_cap_compact),
    createTile("52W High", formatValue(summary.fifty_two_week_high)),
    createTile("52W Low", formatValue(summary.fifty_two_week_low)),
    createTile("Conviction", formatValue(summary.conviction_score, "N/A", "/10")),
    createTile("Confidence", summary.confidence_level),
    createTile("Agent Lens", selectedAgent.label || "Balanced"),
  ].join("");

  const technicalTiles = [
    createTile("Daily Trend", technicals.trend_daily),
    createTile("Weekly Trend", technicals.trend_weekly),
    createTile("Monthly Trend", technicals.trend_monthly),
    createTile("RSI 14", formatValue(technicals.rsi14)),
    createTile("MACD", formatValue(technicals.macd)),
    createTile("Stochastic K", formatValue(technicals.stochastic_k)),
    createTile("Support", formatValue(technicals.support_1)),
    createTile("Resistance", formatValue(technicals.resistance_1)),
  ].join("");

  const fundamentalTiles = [
    createTile("Trailing PE", formatValue(fundamentals.trailing_pe)),
    createTile("Price / Book", formatValue(fundamentals.price_to_book)),
    createTile("Dividend Yield", formatValue(fundamentals.dividend_yield, "N/A", "%")),
    createTile("Revenue Growth", formatValue(fundamentals.revenue_growth, "N/A", "%")),
    createTile("Earnings Growth", formatValue(fundamentals.earnings_growth, "N/A", "%")),
    createTile("ROE", formatValue(fundamentals.roe, "N/A", "%")),
    createTile("ROCE", formatValue(fundamentals.roce, "N/A", "%")),
    createTile("Debt / Equity", formatValue(fundamentals.debt_to_equity)),
  ].join("");

  const swingMarkup = swing.qualifies
    ? `
      <div class="metric-grid">
        ${createTile("Entry Zone", swing.entry_zone)}
        ${createTile("Stop Loss", formatValue(swing.stop_loss))}
        ${createTile("Target 1", formatValue(swing.target_1))}
        ${createTile("Target 2", formatValue(swing.target_2))}
        ${createTile("Expected Swing", formatValue(swing.expected_return_pct, "N/A", "%"))}
        ${createTile("Risk / Reward", formatValue(swing.risk_reward_ratio))}
      </div>
      <ul class="list">
        <li>${swing.technical_reason}</li>
        <li>${swing.invalidation}</li>
      </ul>
    `
    : `<div class="tile"><div class="tile-label">Swing setup</div><div class="muted">${swing.why_not}</div></div>`;
  const snapshotMarkup = renderSnapshot(report.snapshot);
  const hasNews = Array.isArray(report.news) && report.news.length > 0;
  const chartAndNewsMarkup =
    snapshotMarkup || hasNews
      ? `
      <section>
        <div class="section-title"><div><p class="eyebrow">Latest Context</p><h3>Chart and news</h3></div></div>
        <div class="chart-grid">
          ${snapshotMarkup}
          ${hasNews ? `<div class="news-grid">${renderNews(report.news)}</div>` : ""}
        </div>
      </section>
    `
      : "";

  return `
    <article class="stock-card glass-card">
      <div class="card-head">
        <div>
          <p class="eyebrow">Stock Dashboard</p>
          <h2>${report.identity.company_name}</h2>
          <div class="symbol-line">${report.identity.resolved_symbol} • ${summary.sector || "Sector N/A"}${summary.industry ? ` • ${summary.industry}` : ""}</div>
        </div>
        <div class="pill-row">
          <span class="status-chip chip-${summary.decision_pill.tone}">${summary.decision_pill.label}</span>
          <span class="status-chip chip-${summary.trend_pill.tone}">${summary.trend_pill.label}</span>
        </div>
      </div>
      <section>
        <div class="section-title"><div><p class="eyebrow">Summary</p><h3>Decision dashboard</h3></div></div>
        <div class="summary-grid">${summaryTiles}</div>
      </section>
      <section>
        <div class="section-title"><div><p class="eyebrow">Why This Call</p><h3>Swing vs Long-Term</h3></div></div>
        <div class="metric-grid">
          ${createTile("Decision", report.decision.label)}
          ${createTile("Swing Score", formatValue(report.decision.swing_score, "N/A", "/100"))}
          ${createTile("Long-Term Score", formatValue(report.decision.long_term_score, "N/A", "/100"))}
        </div>
        <ul class="list">${report.decision.reasons.map((item) => `<li>${item}</li>`).join("")}</ul>
      </section>
      <section>
        <div class="section-title"><div><p class="eyebrow">Technicals</p><h3>Momentum and structure</h3></div></div>
        <div class="metric-grid">${technicalTiles}</div>
      </section>
      <section>
        <div class="section-title"><div><p class="eyebrow">Fundamentals</p><h3>Financial quality</h3></div></div>
        <div class="metric-grid">${fundamentalTiles}</div>
        <p class="muted">Financial trend label: ${fundamentals.financial_status || "N/A"}</p>
      </section>
      <section>
        <div class="section-title"><div><p class="eyebrow">Reasoning Layer</p><h3>Knowledge influence</h3></div></div>
        <div class="tile">
          <div class="tile-label">Source tags</div>
          <div class="badge-row">${(reasoning.sources || []).map((item) => createBadge(item.title, "tone-green")).join("")}</div>
          <ul class="list">${(reasoning.principles || []).map((item) => `<li>${item}</li>`).join("")}</ul>
        </div>
      </section>
      <section>
        <div class="section-title"><div><p class="eyebrow">Swing Plan</p><h3>Entry, stop, targets</h3></div></div>
        ${swingMarkup}
      </section>
      <section>
        <div class="section-title"><div><p class="eyebrow">Risk and Return</p><h3>Scenario framework</h3></div></div>
        <div class="metric-grid">
          ${createTile("Risk Rating", formatValue(risks.rating, "N/A", "/10"))}
          ${createTile("Base Case", formatValue(report.return_framework.base_case_pct, "N/A", "%"))}
          ${createTile("Bull Case", formatValue(report.return_framework.bull_case_pct, "N/A", "%"))}
          ${createTile("Bear Case", formatValue(report.return_framework.bear_case_pct, "N/A", "%"))}
        </div>
        <ul class="list">${risks.items.map((item) => `<li>${item}</li>`).join("")}</ul>
        <p class="muted">${risks.downside_scenario}</p>
      </section>
      ${chartAndNewsMarkup}
    </article>
  `;
}

function addProgressEvent(event) {
  highestProgress = Math.max(highestProgress, event.progress || 0);
  const stateTone = event.kind === "error" ? "chip-red" : highestProgress >= 100 ? "chip-green" : "chip-yellow";
  progressBar.style.width = `${highestProgress}%`;
  progressPill.textContent = event.kind === "error" ? "Error" : highestProgress >= 100 ? "Complete" : "Running";
  progressPill.className = `status-chip ${stateTone}`;
  if (loadingMessage) loadingMessage.textContent = event.message || "Working...";
  setLoadingOverlayMessage(event.message || "Working...");
  const item = document.createElement("li");
  item.className = `progress-event ${event.kind === "error" ? "event-error" : ""}`;
  item.innerHTML = `
    <div class="progress-event-head">
      <strong>${event.symbol ? `${event.symbol} • ` : ""}${event.step}</strong>
      <span>${formatClock(event.timestamp)}</span>
    </div>
    <span>${event.message}</span>
  `;
  progressLog.prepend(item);
}

function renderResult(payload) {
  const comparisonMarkup = renderComparison(payload.comparison);
  const agentMarkup = renderAgentLens(payload.request_context);
  const reportMarkup = payload.reports.map(renderReport).join("");
  resultBoard.classList.remove("empty-state");
  resultBoard.innerHTML = `${agentMarkup}${comparisonMarkup}${reportMarkup}`;
  document.body.dataset.resultView = "focused";
  if (resultToolbar) resultToolbar.classList.remove("hidden");
  if (resultSearchInput) {
    resultSearchInput.value = "";
    resultSearchInput.placeholder = payload.request?.query || "Search another stock or compare set";
  }
}

function resetRunState() {
  highestProgress = 0;
  progressLog.innerHTML = "";
  progressBar.style.width = "0%";
  progressPill.textContent = "Queued";
  progressPill.className = "status-chip chip-yellow";
  if (loadingMessage) loadingMessage.textContent = "Waiting to start...";
  setLoadingOverlayMessage("Waiting to start...");
  setLoadingEstimate("");
  document.body.dataset.resultView = "default";
  if (resultToolbar) resultToolbar.classList.add("hidden");
}

function showResearchHome() {
  document.body.dataset.resultView = "default";
  if (resultToolbar) resultToolbar.classList.add("hidden");
  resultBoard.classList.add("empty-state");
  resultBoard.innerHTML = `
    <div class="empty-card glass-card">
      <p class="eyebrow">Ready</p>
      <h2>No research package yet</h2>
      <p>Run a ticker or compare set and the dashboard will fill with scores, charts, technicals, fundamentals, risk notes, and decision tags.</p>
    </div>
  `;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || "Request failed");
  }
  return payload;
}

async function loadPortfolioData({ allowFailure = true } = {}) {
  if (!appState.session) {
    appState.portfolio = null;
    renderPortfolio();
    return null;
  }
  try {
    const portfolio = await fetchJSON("/api/portfolio");
    appState.portfolio = portfolio;
    renderPortfolio();
    return portfolio;
  } catch (error) {
    appState.portfolio = {
      insights: { available: false, message: error.message || "Portfolio insights are not available yet." },
      sync_message: error.message || "Portfolio insights are not available yet.",
    };
    renderPortfolio();
    if (!allowFailure) throw error;
    return appState.portfolio;
  }
}

function stopKiteStatusPolling() {
  if (kiteStatusPoller) {
    window.clearInterval(kiteStatusPoller);
    kiteStatusPoller = null;
  }
  kitePollingAttempts = 0;
}

async function finalizeKiteConnection() {
  if (kiteSyncInFlight) return;
  kiteSyncInFlight = true;
  stopKiteStatusPolling();
  showScreen("transition");
  setTransitionMessage("Kite connected. Syncing holdings, positions, and portfolio signals...");
  try {
    await fetchJSON("/api/onboarding/complete", { method: "POST" });
    await refreshBootstrap({ allowAutoKiteSync: false, loadPortfolio: false });
    setTransitionMessage("Portfolio connected. Bringing your dashboard back with live context...");
    await loadPortfolioData();
    await new Promise((resolve) => setTimeout(resolve, 1200));
    showScreen("app");
  } catch (error) {
    setTransitionMessage(error.message || "Kite connected, but portfolio sync still needs another pass.");
    await refreshBootstrap({ allowAutoKiteSync: false });
    showScreen("app");
  } finally {
    kiteSyncInFlight = false;
  }
}

async function checkKiteStatusAndFinalize() {
  const status = await fetchJSON("/api/kite/status");
  appState.kite = status;
  renderKiteStatus();
  renderHeroMeta();
  if (status.kite_connected || status.should_complete_onboarding) {
    await finalizeKiteConnection();
    return true;
  }
  return false;
}

function startKiteStatusPolling() {
  stopKiteStatusPolling();
  showScreen("transition");
  setTransitionMessage("Waiting for Zerodha to confirm Kite. Once it does, we’ll sync the portfolio and open your dashboard.");
  kiteStatusPoller = window.setInterval(async () => {
    kitePollingAttempts += 1;
    try {
      const done = await checkKiteStatusAndFinalize();
      if (done) return;
      if (kitePollingAttempts >= 40) {
        stopKiteStatusPolling();
        await refreshBootstrap({ allowAutoKiteSync: false });
        if (appState.session?.onboardingStep === "kite-connect") {
          showScreen("kite");
        }
      }
    } catch (_) {
      if (kitePollingAttempts >= 40) {
        stopKiteStatusPolling();
        showScreen("kite");
      }
    }
  }, 3000);
}

async function refreshBootstrap({ allowAutoKiteSync = true, loadPortfolio = true } = {}) {
  appState = await fetchJSON("/api/bootstrap");
  renderProviderVisibility();
  renderUserCard();
  renderHeroMeta();
  renderAgentPanel();
  renderAgentHelper();
  renderWatchlist();
  renderKnowledgePanel();
  renderInfrastructurePanel();
  renderMarketDataPanel();
  renderKiteStatus();
  if (allowAutoKiteSync && appState.session && appState.kite?.kite_connected && appState.session?.onboardingStep === "kite-connect") {
    await finalizeKiteConnection();
    return;
  }
  if (appState.session && loadPortfolio && (appState.kite?.kite_connected || appState.session?.isKiteUser)) {
    await loadPortfolioData();
  } else {
    appState.portfolio = null;
    renderPortfolio();
  }
  routeAppState();
}

function routeAppState() {
  const user = appState.session;
  if (!user) {
    showScreen("auth");
    return;
  }
  if (appState.kite?.kite_connected && user.onboardingStep === "kite-connect") {
    showScreen("transition");
    setTransitionMessage("Kite connected. Syncing your dashboard...");
    return;
  }
  if (user.onboardingStep === "choose-kite") {
    showScreen("onboarding");
    return;
  }
  if (user.onboardingStep === "kite-connect") {
    showScreen("kite");
    return;
  }
  showScreen("app");
}

async function ensureFirebaseContext() {
  const auth = appState.auth || {};
  if (!auth.firebase_enabled || !auth.firebase_client_config?.apiKey) {
    return null;
  }
  if (firebaseAuthContext) return firebaseAuthContext;
  const [{ initializeApp }, { getAuth, GoogleAuthProvider, signInWithPopup }] = await Promise.all([
    import("https://www.gstatic.com/firebasejs/10.12.5/firebase-app.js"),
    import("https://www.gstatic.com/firebasejs/10.12.5/firebase-auth.js"),
  ]);
  const app = initializeApp(auth.firebase_client_config);
  const authClient = getAuth(app);
  firebaseAuthContext = { authClient, GoogleAuthProvider, signInWithPopup };
  return firebaseAuthContext;
}

async function loginWithGoogle() {
  if (googleLoginButton) googleLoginButton.disabled = true;
  if (heroLoginButton) heroLoginButton.disabled = true;
  if (authHelper) authHelper.textContent = "Starting sign-in...";
  try {
    let profile;
    const firebaseContext = await ensureFirebaseContext();
    if (firebaseContext) {
      const provider = new firebaseContext.GoogleAuthProvider();
      const result = await firebaseContext.signInWithPopup(firebaseContext.authClient, provider);
      const user = result.user;
      profile = {
        uid: user.uid,
        name: user.displayName || "Gains user",
        email: user.email || "",
        image: user.photoURL || "",
        id_token: await user.getIdToken(),
        provider: "google",
      };
    } else {
      profile = {
        uid: `local-${Date.now()}`,
        name: "Local Gains User",
        email: "local@gains.dev",
        image: "",
        id_token: "",
        provider: "google",
      };
    }
    await fetchJSON("/api/auth/session", {
      method: "POST",
      body: JSON.stringify(profile),
    });
    if (authHelper) authHelper.textContent = "Signed in successfully.";
    await refreshBootstrap();
  } catch (error) {
    if (authHelper) authHelper.textContent = error.message || "Google sign-in failed.";
  } finally {
    if (googleLoginButton) googleLoginButton.disabled = false;
    if (heroLoginButton) heroLoginButton.disabled = false;
  }
}

async function setKiteChoice(isKiteUser, { refresh = true } = {}) {
  await fetchJSON("/api/onboarding/kite-choice", {
    method: "POST",
    body: JSON.stringify({ is_kite_user: isKiteUser }),
  });
  if (refresh) {
    await refreshBootstrap();
  }
}

async function completeOnboardingWithDelay(message = "We’re updating market data for your dashboard...") {
  showScreen("transition");
  setTransitionMessage(message);
  await new Promise((resolve) => setTimeout(resolve, 2000));
  await fetchJSON("/api/onboarding/complete", { method: "POST" });
  await refreshBootstrap();
}

async function handleLogout() {
  await fetchJSON("/api/auth/logout", { method: "POST" });
  appState = { ...(appState || {}), session: null, watchlist: [], search_history: [], portfolio: null };
  toggleProfileMenu(false);
  showScreen("auth");
}

async function handleAddWatchlist() {
  const firstSymbol = (queryInput.value || "").split(/[\s,]+/).find(Boolean);
  if (!firstSymbol) return;
  await fetchJSON("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ symbol: firstSymbol, note: thoughtsInput.value.trim() }),
  });
  await refreshBootstrap();
}

async function openKiteFlow() {
  if (!appState.session) {
    showScreen("auth");
    return;
  }
  await setKiteChoice(true);
}

async function handleKiteConnectAttempt() {
  if (kiteConnectButton) kiteConnectButton.disabled = true;
  if (dashboardConnectKiteButton) dashboardConnectKiteButton.disabled = true;
  if (sideConnectKiteButton) sideConnectKiteButton.disabled = true;
  try {
    const payload = await fetchJSON("/api/kite/connect", { method: "POST" });
    appState.kite = payload.kite || appState.kite;
    renderKiteStatus();
    renderHeroMeta();
    if (payload.connect?.login_url) {
      const warningText = payload.connect.warning_text || appState.kite?.warning_text || "";
      const proceed = warningText ? window.confirm(`${warningText}\n\nPress OK to continue to Zerodha login.`) : true;
      if (proceed) {
        window.open(payload.connect.login_url, "_blank", "noopener,noreferrer");
        startKiteStatusPolling();
      }
    }
    await refreshBootstrap({ allowAutoKiteSync: false });
    if (appState.kite?.kite_connected) {
      await finalizeKiteConnection();
    }
  } catch (error) {
    if (kiteStatusCard) {
      kiteStatusCard.insertAdjacentHTML(
        "beforeend",
        `<p class="muted inline-note">${error.message || "Kite connection could not be started."}</p>`
      );
    }
  } finally {
    if (kiteConnectButton) kiteConnectButton.disabled = false;
    if (dashboardConnectKiteButton) dashboardConnectKiteButton.disabled = false;
    if (sideConnectKiteButton) sideConnectKiteButton.disabled = false;
  }
}

function toggleProfileMenu(force) {
  if (!profileDropdown || !profileMenuButton) return;
  const willOpen = typeof force === "boolean" ? force : profileDropdown.classList.contains("hidden");
  profileDropdown.classList.toggle("hidden", !willOpen);
  profileMenuButton.setAttribute("aria-expanded", willOpen ? "true" : "false");
}

function toggleFeedbackPanel(force) {
  if (!feedbackPanel) return;
  const willOpen = typeof force === "boolean" ? force : feedbackPanel.classList.contains("hidden");
  feedbackPanel.classList.toggle("hidden", !willOpen);
}

async function submitFeedback() {
  const message = feedbackMessage?.value.trim();
  if (!message) {
    if (feedbackStatus) feedbackStatus.textContent = "Add a short note first.";
    return;
  }
  if (feedbackSubmit) feedbackSubmit.disabled = true;
  if (feedbackStatus) feedbackStatus.textContent = "Sending...";
  try {
    const payload = await fetchJSON("/api/feedback", {
      method: "POST",
      body: JSON.stringify({
        message,
        route: `${window.location.pathname}#${activeScreen}`,
        metadata: {
          screen: activeScreen,
          has_kite: Boolean(appState.session?.isKiteUser),
        },
      }),
    });
    if (feedbackStatus) feedbackStatus.textContent = payload.message || "Feedback stored.";
    if (feedbackMessage) feedbackMessage.value = "";
    window.setTimeout(() => toggleFeedbackPanel(false), 900);
  } catch (error) {
    if (feedbackStatus) feedbackStatus.textContent = error.message || "Could not store feedback.";
  } finally {
    if (feedbackSubmit) feedbackSubmit.disabled = false;
  }
}

async function startAnalysis(event) {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) {
    queryInput.focus();
    return;
  }
  if (currentEventSource) currentEventSource.close();
  resetRunState();
  loadingScreen.classList.remove("hidden");
  setLoadingOverlayMessage("Starting your research engine...");
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({
      query,
      thoughts: thoughtsInput.value.trim(),
      chart_interval: intervalInput.value,
      agent_preset: agentPresetInput?.value || "auto",
      include_tradingview_snapshot: snapshotInput.checked,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    loadingScreen.classList.add("hidden");
    addProgressEvent({ kind: "error", step: "validation", message: payload.detail || "Request failed.", progress: 0 });
    return;
  }
  if (payload.estimate?.label) {
    setLoadingEstimate(`Estimated time: ${payload.estimate.label}`);
    if (loadingMessage) loadingMessage.textContent = `Estimated time: ${payload.estimate.label}`;
    setLoadingOverlayMessage(`This usually takes ${payload.estimate.label}, depending on symbols, charts, and live data speed.`);
  }
  currentEventSource = new EventSource(`/api/jobs/${payload.job_id}/events`);
  currentEventSource.onmessage = (messageEvent) => {
    const eventPayload = JSON.parse(messageEvent.data);
    if (eventPayload.kind === "terminal") {
      loadingScreen.classList.add("hidden");
      if (eventPayload.status === "completed" && eventPayload.result) {
        renderResult(eventPayload.result);
      } else {
        addProgressEvent({ kind: "error", step: "terminal", message: eventPayload.error || "Analysis failed.", progress: 100 });
      }
      currentEventSource.close();
      currentEventSource = null;
      return;
    }
    addProgressEvent(eventPayload);
  };
  currentEventSource.onerror = () => {
    loadingScreen.classList.add("hidden");
    if (currentEventSource) {
      currentEventSource.close();
      currentEventSource = null;
    }
    addProgressEvent({ kind: "error", step: "stream", message: "Lost the live event stream. Refresh and try again.", progress: 100 });
  };
}

document.querySelectorAll(".preset").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.query || "";
    thoughtsInput.value = button.dataset.thoughts || "";
  });
});

document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", (event) => {
    const href = anchor.getAttribute("href");
    if (!href || href === "#") return;
    const target = document.querySelector(href);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

document.addEventListener("click", (event) => {
  if (profileDropdown && profileMenuButton) {
    const insideProfile = profileDropdown.contains(event.target) || profileMenuButton.contains(event.target);
    if (!insideProfile) toggleProfileMenu(false);
  }
  if (feedbackPanel && feedbackFab) {
    const insideFeedback = feedbackPanel.contains(event.target) || feedbackFab.contains(event.target);
    if (!insideFeedback && !feedbackPanel.classList.contains("hidden")) toggleFeedbackPanel(false);
  }
});

googleLoginButton?.addEventListener("click", loginWithGoogle);
heroLoginButton?.addEventListener("click", loginWithGoogle);
kiteYesButton?.addEventListener("click", () => setKiteChoice(true));
kiteNoButton?.addEventListener("click", async () => {
  await setKiteChoice(false, { refresh: false });
  await completeOnboardingWithDelay("We’re updating market data for your dashboard...");
});
kiteConnectButton?.addEventListener("click", handleKiteConnectAttempt);
kiteRefreshButton?.addEventListener("click", async () => {
  await refreshBootstrap({ allowAutoKiteSync: false });
  if (appState.kite?.kite_connected) {
    await finalizeKiteConnection();
  }
});
kiteSkipButton?.addEventListener("click", async () => {
  await completeOnboardingWithDelay("Opening the dashboard without portfolio sync...");
});
profileMenuButton?.addEventListener("click", () => toggleProfileMenu());
logoutButton?.addEventListener("click", handleLogout);
addWatchlistButton?.addEventListener("click", handleAddWatchlist);
dashboardConnectKiteButton?.addEventListener("click", openKiteFlow);
sideConnectKiteButton?.addEventListener("click", openKiteFlow);
feedbackFab?.addEventListener("click", () => toggleFeedbackPanel());
feedbackClose?.addEventListener("click", () => toggleFeedbackPanel(false));
feedbackSubmit?.addEventListener("click", submitFeedback);
form?.addEventListener("submit", startAnalysis);
resultHomeButton?.addEventListener("click", showResearchHome);
resultSearchForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = resultSearchInput?.value.trim();
  if (!query) return;
  queryInput.value = query;
  thoughtsInput.value = "";
  await startAnalysis(event);
});
agentPresetInput?.addEventListener("change", renderAgentHelper);

refreshBootstrap().catch((error) => {
  if (authHelper) authHelper.textContent = error.message || "Unable to bootstrap the app.";
  showScreen("auth");
});
