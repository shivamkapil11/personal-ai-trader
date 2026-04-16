# Roadmap and Backlog

This backlog is organized for product planning and hiring handoff.

Complexity scale:

- `Low`
- `Medium`
- `High`
- `Very High`

Priority scale:

- `P1` immediate
- `P2` near-term
- `P3` medium-term
- `P4` later-stage

## Near-Term Product Backlog

| Feature | Value | Complexity | Priority | Dependencies |
| --- | --- | --- | --- | --- |
| Watchlist management | Keeps ideas organized between research sessions | Medium | P1 | Persistent storage |
| Portfolio tracking expansion | Turns optional Kite connectivity into a real monitoring surface | Medium | P1 | Kite bridge, persistent snapshots |
| Alerts | Helps users monitor setups and portfolio changes without manual checks | High | P2 | Background jobs, persistence |
| AI insights layer | Adds synthesized insight summaries and anomaly detection | Medium | P2 | Prompt orchestration, source governance |
| Earnings analysis | Makes quarterly updates easier to digest and compare | High | P2 | Earnings source ingestion |
| Annual report parsing | Converts long documents into structured company takeaways | High | P2 | PDF/document ingestion pipeline |
| Insider tracking | Adds conviction/risk context around promoter and insider activity | Medium | P2 | Reliable disclosures source |
| Sector dashboards | Makes relative analysis across sectors more useful | High | P2 | Sector data model |
| Conviction engine v2 | Improves consistency and explainability of recommendations | High | P2 | Larger scoring framework |
| Risk engine v2 | Better downside, scenario, and exposure analysis | High | P2 | Portfolio + factor models |
| Backtesting | Validates rule-based setups over time | Very High | P3 | Historical dataset strategy |
| Journaling | Helps users track thesis, outcome, and discipline | Medium | P2 | User profiles, persistence |
| Saved reports | Makes research reusable and shareable | Medium | P2 | Persistent storage |
| Exports | PDF/CSV sharing for reports and portfolio views | Medium | P3 | Saved report format |
| Admin panel | Internal visibility into usage, feedback, and ops | High | P3 | Auth roles, persistent telemetry |
| Subscriptions | Needed only if monetization becomes a goal | High | P4 | Billing provider, auth maturity |
| Mobile version | Expands access and retention | Very High | P4 | Stable API layer |
| Background jobs | Required for scalable alerts, ingestion, and scheduled work | High | P1 | Durable queue / worker system |
| PDF reports | Better client-ready output format | Medium | P3 | Report templating |
| Knowledge ingestion expansion | Allows adding more books, notes, research, and filings cleanly | High | P1 | Ingestion registry + storage |

## Feature Detail

### Watchlist

- Value: turns ad hoc searches into a repeatable monitoring workflow
- Complexity: Medium
- Priority: P1
- Dependencies: Postgres-backed persistence, optional tagging

### Portfolio Tracking Expansion

- Value: converts Kite connection into real daily utility
- Complexity: Medium
- Priority: P1
- Dependencies: Kite bridge, persistent portfolio snapshots

### Alerts

- Value: proactive monitoring for price, technical, portfolio, and event triggers
- Complexity: High
- Priority: P2
- Dependencies: background jobs, notification design, persistence

### AI Insights

- Value: faster scanning and clearer takeaways
- Complexity: Medium
- Priority: P2
- Dependencies: prompt orchestration rules, source tagging guardrails

### Earnings Analysis

- Value: faster quarterly result interpretation and post-results monitoring
- Complexity: High
- Priority: P2
- Dependencies: filings/results ingestion

### Annual Report Parsing

- Value: stronger long-term research workflow
- Complexity: High
- Priority: P2
- Dependencies: PDF parsing pipeline, source storage

### Insider Tracking

- Value: improves governance and confidence signals
- Complexity: Medium
- Priority: P2
- Dependencies: exchange disclosures normalization

### Sector Dashboards

- Value: compare ideas within sector context instead of in isolation
- Complexity: High
- Priority: P2
- Dependencies: sector benchmarks, normalized peer data

### Conviction Engine

- Value: better explainability and more stable recommendation quality
- Complexity: High
- Priority: P2
- Dependencies: expanded scoring schema, feedback loop

### Risk Engine

- Value: clearer downside framing and portfolio-aware caution signals
- Complexity: High
- Priority: P2
- Dependencies: portfolio model, scenario logic

### Backtesting

- Value: validates technical rules and research heuristics
- Complexity: Very High
- Priority: P3
- Dependencies: durable historical data and test harness

### Journaling

- Value: helps users improve decision quality over time
- Complexity: Medium
- Priority: P2
- Dependencies: user persistence, saved records

### Saved Reports

- Value: turns research runs into reusable knowledge assets
- Complexity: Medium
- Priority: P2
- Dependencies: Postgres or document storage

### Exports

- Value: improves sharing and offline use
- Complexity: Medium
- Priority: P3
- Dependencies: saved reports, render templates

### Admin Panel

- Value: internal operational visibility
- Complexity: High
- Priority: P3
- Dependencies: role system, telemetry collection

### Subscriptions

- Value: monetization
- Complexity: High
- Priority: P4
- Dependencies: stable product surface, auth maturity, billing provider

### Mobile Version

- Value: reach and convenience
- Complexity: Very High
- Priority: P4
- Dependencies: stable API-first backend

### Background Jobs

- Value: prerequisite for scale
- Complexity: High
- Priority: P1
- Dependencies: queue, worker runtime, durable persistence

### PDF Reports

- Value: high-signal deliverables for users and teams
- Complexity: Medium
- Priority: P3
- Dependencies: report templates and export pipeline

### Knowledge Ingestion Expansion

- Value: compounds the long-term quality of the reasoning layer
- Complexity: High
- Priority: P1
- Dependencies: ingestion workflow, source metadata model, storage rules

## Suggested Priority Order

1. Live environment validation
2. Postgres runtime persistence
3. Background jobs
4. Watchlist + saved reports
5. Portfolio expansion
6. Knowledge ingestion expansion
7. Alerts
8. Conviction/risk engine v2
