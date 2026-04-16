const form = document.getElementById("analysis-form");
const queryInput = document.getElementById("query");
const thoughtsInput = document.getElementById("thoughts");
const intervalInput = document.getElementById("chart-interval");
const snapshotInput = document.getElementById("include-snapshot");
const progressLog = document.getElementById("progress-log");
const progressBar = document.getElementById("progress-bar");
const progressPill = document.getElementById("progress-pill");
const resultBoard = document.getElementById("result-board");
const loadingScreen = document.getElementById("loading-screen");
const loadingMessage = document.getElementById("loading-message");

let currentEventSource = null;
let highestProgress = 0;

document.querySelectorAll(".preset").forEach((button) => {
  button.addEventListener("click", () => {
    queryInput.value = button.dataset.query || "";
    thoughtsInput.value = button.dataset.thoughts || "";
  });
});

function formatValue(value, fallback = "N/A", suffix = "") {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return fallback;
  }
  return `${value}${suffix}`;
}

function createTile(label, value) {
  return `
    <div class="tile">
      <div class="tile-label">${label}</div>
      <div class="tile-value">${value}</div>
    </div>
  `;
}

function createBadge(value) {
  return `<span class="mini-badge">${value}</span>`;
}

function renderRequestContext(context) {
  if (!context) {
    return "";
  }

  const focusBadges = (context.focus_labels || []).map(createBadge).join("");
  const noteItems = (context.notes_highlights || [])
    .map((item) => `<li>${item}</li>`)
    .join("");
  const frameworkItems = (context.framework_steps || [])
    .map((item) => `<li>${item}</li>`)
    .join("");
  const checklistItems = (context.thinking_checklist || [])
    .map((item) => `<li>${item}</li>`)
    .join("");

  return `
    <section class="brief-section">
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
      ${
        noteItems
          ? `<div class="tile"><div class="tile-label">Your notes, cleaned up</div><ul class="list">${noteItems}</ul></div>`
          : ""
      }
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
  if (!comparison || !comparison.table || !comparison.table.length) {
    return "";
  }

  const tiles = comparison.table
    .map(
      (row) => `
        <div class="tile">
          <div class="tile-label">${row.symbol}</div>
          <div class="tile-value">${row.decision}</div>
          <p class="muted">Conviction ${formatValue(row.conviction)} | LT ${formatValue(row.long_term_score)} | Swing ${formatValue(row.swing_score)}</p>
          <p class="muted">PE ${formatValue(row.trailing_pe)} | Div ${formatValue(row.dividend_yield, "N/A", "%")}</p>
          ${row.prompt_fit_score !== undefined ? `<p class="muted">Prompt fit ${formatValue(row.prompt_fit_score)}</p>` : ""}
        </div>
      `
    )
    .join("");

  return `
    <section class="compare-section">
      <div class="section-title">
        <div>
          <p class="eyebrow">Compare View</p>
          <h2>Quick ranking</h2>
        </div>
      </div>
      <div class="compare-grid">
        ${tiles}
      </div>
      <div class="metric-grid">
        ${createTile("Best Long-Term", comparison.summary.best_long_term)}
        ${createTile("Best Swing", comparison.summary.best_swing)}
        ${createTile("Lowest Risk", comparison.summary.lowest_risk)}
        ${comparison.summary.best_fit_for_prompt ? createTile("Best Fit For Prompt", comparison.summary.best_fit_for_prompt) : ""}
      </div>
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
  if (!snapshot || snapshot.status !== "ready") {
    return `
      <div class="tile snapshot-card">
        <div class="tile-label">TradingView Snapshot</div>
        <div class="muted">${snapshot?.message || "Snapshot unavailable."}</div>
      </div>
    `;
  }

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

  const summaryTiles = [
    createTile("Current Price", formatValue(summary.current_price)),
    createTile("Quote Source", summary.quote_source || "N/A"),
    createTile("Market Cap", report.display.market_cap_compact),
    createTile("52W High", formatValue(summary.fifty_two_week_high)),
    createTile("52W Low", formatValue(summary.fifty_two_week_low)),
    createTile("Conviction", formatValue(summary.conviction_score, "N/A", "/10")),
    createTile("Confidence", summary.confidence_level),
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

  const riskMarkup = `
    <div class="metric-grid">
      ${createTile("Risk Rating", formatValue(risks.rating, "N/A", "/10"))}
      ${createTile("Base Case", formatValue(report.return_framework.base_case_pct, "N/A", "%"))}
      ${createTile("Bull Case", formatValue(report.return_framework.bull_case_pct, "N/A", "%"))}
      ${createTile("Bear Case", formatValue(report.return_framework.bear_case_pct, "N/A", "%"))}
    </div>
    <ul class="list">${risks.items.map((item) => `<li>${item}</li>`).join("")}</ul>
    <p class="muted">${risks.downside_scenario}</p>
  `;

  return `
    <article class="stock-card">
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
        <div class="section-title">
          <div>
            <p class="eyebrow">Summary</p>
            <h3>Decision dashboard</h3>
          </div>
        </div>
        <div class="summary-grid">${summaryTiles}</div>
      </section>

      <section>
        <div class="section-title">
          <div>
            <p class="eyebrow">Why This Call</p>
            <h3>Swing vs Long-Term</h3>
          </div>
        </div>
        <div class="metric-grid">
          ${createTile("Decision", report.decision.label)}
          ${createTile("Swing Score", formatValue(report.decision.swing_score, "N/A", "/100"))}
          ${createTile("Long-Term Score", formatValue(report.decision.long_term_score, "N/A", "/100"))}
        </div>
        <ul class="list">${report.decision.reasons.map((item) => `<li>${item}</li>`).join("")}</ul>
      </section>

      <section>
        <div class="section-title">
          <div>
            <p class="eyebrow">Technicals</p>
            <h3>Momentum and structure</h3>
          </div>
        </div>
        <div class="metric-grid">${technicalTiles}</div>
      </section>

      <section>
        <div class="section-title">
          <div>
            <p class="eyebrow">Fundamentals</p>
            <h3>Financial quality</h3>
          </div>
        </div>
        <div class="metric-grid">${fundamentalTiles}</div>
        <p class="muted">Financial trend label: ${fundamentals.financial_status || "N/A"}</p>
      </section>

      <section>
        <div class="section-title">
          <div>
            <p class="eyebrow">Data Source</p>
            <h3>Live quote tracking</h3>
          </div>
        </div>
        <div class="tile">
          <div class="tile-label">${report.market_context?.quote_provider_label || "Quote source"}</div>
          <div class="muted">${report.market_context?.quote_message || "No quote-source details available."}</div>
        </div>
      </section>

      <section>
        <div class="section-title">
          <div>
            <p class="eyebrow">Swing Plan</p>
            <h3>Entry, stop, targets</h3>
          </div>
        </div>
        ${swingMarkup}
      </section>

      <section>
        <div class="section-title">
          <div>
            <p class="eyebrow">Risk and Return</p>
            <h3>Scenario framework</h3>
          </div>
        </div>
        ${riskMarkup}
      </section>

      <section>
        <div class="section-title">
          <div>
            <p class="eyebrow">Chart and News</p>
            <h3>Visual and headline context</h3>
          </div>
        </div>
        <div class="chart-grid">
          ${renderSnapshot(report.snapshot)}
          <div class="news-grid">${renderNews(report.news)}</div>
        </div>
      </section>
    </article>
  `;
}

function addProgressEvent(event) {
  highestProgress = Math.max(highestProgress, event.progress || 0);
  progressBar.style.width = `${highestProgress}%`;
  progressPill.textContent = event.kind === "error" ? "Error" : event.kind === "complete" ? "Complete" : "Running";
  progressPill.className = `status-chip ${
    event.kind === "error" ? "chip-red" : highestProgress >= 100 ? "chip-green" : "chip-yellow"
  }`;
  loadingMessage.textContent = event.message || "Working...";

  const item = document.createElement("li");
  item.innerHTML = `
    <strong>${event.symbol ? `${event.symbol} • ` : ""}${event.step}</strong>
    <span>${event.message}</span>
  `;
  progressLog.prepend(item);
}

function renderResult(payload) {
  const contextMarkup = renderRequestContext(payload.request_context);
  const comparisonMarkup = renderComparison(payload.comparison);
  const reportMarkup = payload.reports.map(renderReport).join("");
  resultBoard.classList.remove("empty-state");
  resultBoard.innerHTML = `${contextMarkup}${comparisonMarkup}${reportMarkup}`;
}

function resetRunState() {
  highestProgress = 0;
  progressLog.innerHTML = "";
  progressBar.style.width = "0%";
  progressPill.textContent = "Queued";
  progressPill.className = "status-chip chip-yellow";
  loadingMessage.textContent = "Waiting to start...";
}

async function startAnalysis(event) {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) {
    queryInput.focus();
    return;
  }

  if (currentEventSource) {
    currentEventSource.close();
  }

  resetRunState();
  loadingScreen.classList.remove("hidden");

  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      thoughts: thoughtsInput.value.trim(),
      chart_interval: intervalInput.value,
      include_tradingview_snapshot: snapshotInput.checked,
    }),
  });

  if (!response.ok) {
    loadingScreen.classList.add("hidden");
    const payload = await response.json();
    addProgressEvent({
      kind: "error",
      step: "validation",
      message: payload.detail || "Request failed.",
      progress: 0,
    });
    return;
  }

  const { job_id } = await response.json();
  currentEventSource = new EventSource(`/api/jobs/${job_id}/events`);

  currentEventSource.onmessage = (messageEvent) => {
    const payload = JSON.parse(messageEvent.data);
    if (payload.kind === "terminal") {
      loadingScreen.classList.add("hidden");
      if (payload.status === "completed" && payload.result) {
        renderResult(payload.result);
      } else {
        addProgressEvent({
          kind: "error",
          step: "terminal",
          message: payload.error || "Analysis failed.",
          progress: 100,
        });
      }
      currentEventSource.close();
      currentEventSource = null;
      return;
    }

    addProgressEvent(payload);
  };

  currentEventSource.onerror = () => {
    loadingScreen.classList.add("hidden");
    if (currentEventSource) {
      currentEventSource.close();
      currentEventSource = null;
    }
    addProgressEvent({
      kind: "error",
      step: "stream",
      message: "Lost the live event stream. Refresh and try again.",
      progress: 100,
    });
  };
}

form.addEventListener("submit", startAnalysis);
