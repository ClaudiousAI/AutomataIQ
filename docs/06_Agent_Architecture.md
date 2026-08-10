# 06 — Agent Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [05_AI_Architecture](./05_AI_Architecture.md) · [10_Backend_Architecture](./10_Backend_Architecture.md) · [08_API_Design](./08_API_Design.md)

---

## 1. Operating Model

Agents communicate through **typed contracts and persistent artifacts**. Operating rules:

1. **No agent silently invents facts** — every claim traces to evidence.
2. **No agent directly deploys production changes.**
3. **No agent bypasses governance** (source policy, model policy, RBAC, audit).
4. **Each agent writes a durable artifact** before the next stage reads it (idempotent, replayable).

## 2. The Agent Roster

| Agent | Responsibility | Output artifact |
|---|---|---|
| **Discovery** | Find new/changed ecosystem content | Candidate items |
| **Evidence** | Validate authority/corroboration | Evidence package |
| **Change** | Determine material change | Change record |
| **Automation** | Extract business problem/pattern | Automation Card |
| **Architecture** | Reconstruct technical design | Architecture graph |
| **Opportunity** | Determine applicability/build path | Opportunity assessment |
| **Scoring** | Rank consistently | Score + rationale |
| **Knowledge** | Resolve entities/update graph | Relationships |
| **Report** | Create Saturday package | PDF / HTML / JSON |
| **Review** | Route uncertain/high-impact items | Review queue entry |
| **Governance** | Enforce source/model/policy controls | Audit / policy events |

## 3. Pipeline

```
Scheduler → Acquisition → Parse → Normalize → Hash/Diff → Relevance → Deduplicate
         → Automation Extraction → Architecture → Evidence → Opportunity → Scoring
         → Knowledge Graph → Report → Notification
```

Stage mapping:

| Stage | Agent(s) |
|---|---|
| Acquisition → Normalize | Discovery (via crawl workers) |
| Hash/Diff → Relevance | Change |
| Deduplicate | Knowledge (entity resolution) |
| Automation Extraction | Automation |
| Architecture | Architecture |
| Evidence | Evidence |
| Opportunity → Scoring | Opportunity + Scoring |
| Knowledge Graph | Knowledge |
| Report → Notification | Report (+ Review for high-impact) |

## 4. Agent Contract (typed I/O)

Every agent implements the same envelope:

```jsonc
{
  "agent": "architecture",
  "run_id": "run_...",            // idempotency key
  "tenant_id": "tenant_...",
  "input_refs": ["artifact://source_version/...", "artifact://finding/..."],
  "model": "model-x@1.4.2",
  "prompt_version": "p_arch_v3",
  "output_artifacts": ["artifact://architecture_graph/..."],
  "status": "succeeded",          // succeeded | failed | needs_review | skipped
  "confidence": 0.82,
  "audit": { "trace_id": "...", "token_cost_usd": 0.0042 }
}
```

- `input_refs`/`output_artifacts` reference the persistent artifact store (object storage + Postgres metadata).
- Validation: schema-checked on entry and exit ([05_AI_Architecture](./05_AI_Architecture.md) §2).
- Versioned: `(agent, model, prompt_version)` recorded on every run.

## 5. Orchestration

- A **workflow/orchestration framework** drives the pipeline with defined steps, retries, and rollback semantics (ADR-002).
- **Human-in-the-loop** gates: Review agent inserts a check when confidence is low or impact is high; the pipeline pauses at that gate.
- **Queues** decouple agents; each agent consumes from its input queue and publishes to the next.
- **Failure policy:** retry with backoff → fallback model → mark `needs_review` → DLQ for operational alert ([FR-C09-4]).

## 6. Governance & Audit

- **Governance agent** enforces source policy, model policy, RBAC, and audit on every stage.
- Every agent run writes an `agent_runs` row and appends to `audit_log` ([07_Database_Design](./07_Database_Design.md)).
- No stage bypasses governance: even Review decisions are audited.

## 7. Edge Cases

| Case | Behavior |
|---|---|
| Unavailable source | Retry/backoff → alert |
| Changed page structure | Quarantine parser result |
| Conflicting sources | Retain claims, reduce confidence |
| Duplicate | Merge under canonical finding |
| LLM failure | Retry → fallback → review |
| Low confidence | Do not promote automatically |
| Report failure | Retry + alert; never publish incomplete report |
