# 21 — AI Layer Specification (Phase 4)

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Finalized — implementation-ready AI-layer specification
**Related docs:** [05_AI_Architecture](./05_AI_Architecture.md) · [06_Agent_Architecture](./06_Agent_Architecture.md) · [10_Backend_Architecture](./10_Backend_Architecture.md) · [14_Testing_Strategy](./14_Testing_Strategy.md) · [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md)
**ADR refs:** 0003 (LLM gateway), 0005 (idempotent jobs), 0006 (deterministic-first), 0007 (evidence-first), 0014 (locked stack: LangGraph + Celery orchestration)

> **Purpose:** define every agent precisely — name, purpose, inputs, outputs, prompt template, tools, memory, retry policy, error handling, evaluation criteria, success criteria — so the AI layer can be implemented directly from this document. Every agent traces to requirement IDs in the RTM.

---

## 1. Operating Principles Every Agent Must Honor

1. **Deterministic-first (ADR-0006).** All parsing, normalization, hashing, diffing, deduplication, and entity resolution run as *code before any model call*. The model only ever reasons over normalized, deduplicated artifacts — never raw web content.
2. **Evidence-first (ADR-0007).** Every claim the model emits must carry an evidence reference or an explicit `inferred`/`speculative` label. Unreferenced claims are dropped or marked speculative — never silently accepted.
3. **Structured output.** Every agent returns JSON validated against its schema. Invalid output → retry, then route to review. No silent acceptance.
4. **Versioned & audited.** Every run records `(agent, model, prompt_version, model_version)` in `agent_runs` and appends to `audit_log`.
5. **Idempotent & replayable (ADR-0005).** `run_id` is the idempotency key; re-running a completed step produces no duplicates.
6. **Human-in-the-loop.** Low-confidence or high-impact results go to the Review Queue. They are never auto-promoted.
7. **No deployment, no governance bypass.** No agent can deploy production changes; no agent bypasses source policy, model policy, RBAC, or audit.

---

## 2. The AI Pipeline & Agent Map

```
Scheduler → Discovery(Acquire→Parse→Normalize→Hash) → Change(Diff→Classify)
         → Evidence(Confidence→Merge→Label) → Automation(Extract→Card)
         → Architecture(Graph→Diagram) → Opportunity(Validate→Path)
         → Scoring(Rank) → Knowledge(Graph→Resolve) → Review(Gate)
         → Report(Compose→Export→Notify)
```

| Agent | Stage(s) | Primary FRs | Model tier | Output artifact |
|---|---|---|---|---|
| Discovery | Acquire → Parse → Normalize → Hash | FR-001…005, 007 | T0 (deterministic) | `candidate_items` |
| Change | Diff → Relevance → Classify | FR-006, 008–010 | T1 (cheap) | `change_record` |
| Evidence | Confidence → Merge → Label | FR-011–014 | T1/T2 | `evidence_package` |
| Automation | Extract → Classify → Card | FR-015–020 | T2 | `automation_card` |
| Architecture | Reconstruct → Diagram | FR-021–027 | T3 (capable) | `architecture_graph` |
| Opportunity | Validate → Gap → Path | FR-028–033 | T1/T2 | `opportunity_assessment` |
| Scoring | Score → Rank | FR-034–037, NFR-008 | T1 | `score_vector` |
| Knowledge | Resolve → Link → Recommend | FR-038–042, 044 | T2 | `relationships` |
| Review | Route → Gate → Capture feedback | FR-056, 059 | T1 | `review_queue_entry` |
| Report | Compose → Export → Notify | FR-045–051, NFR-002 | T3 | `report_package` |
| Governance | Enforce → Audit | FR-053–055, 057–058 | T0/T1 | `policy_events` |
| **LLM Gateway** | (all model calls) | NFR-006, 012, 013 | — | `model_response` |

**Model tiers:** T0 = no model (pure code) · T1 = cheap/fast model (classification, enum mapping) · T2 = mid-capability (structured extraction, resolution) · T3 = capable model (reconstruction, narrative). Tiers are routed by the gateway (ADR-0003), budget-aware (NFR-012).

---

## 3. The Shared Agent Contract

Every agent implements the same envelope (from [06](./06_Agent_Architecture.md) §4), validated on entry and exit:

```jsonc
{
  "agent": "architecture",
  "run_id": "run_...",                 // idempotency key
  "tenant_id": "tenant_...",
  "input_refs": ["artifact://source_version/...", "artifact://finding/..."],
  "model": "model-x@1.4.2",
  "prompt_version": "p_arch_v3",
  "output_artifacts": ["artifact://architecture_graph/..."],
  "status": "succeeded",               // succeeded | failed | needs_review | skipped
  "confidence": 0.82,
  "audit": { "trace_id": "...", "token_cost_usd": 0.0042 }
}
```

Artifacts live in object storage (MinIO) with Postgres metadata. `status: needs_review` inserts a Review-gate pause via the orchestrator (LangGraph interruption / Celery signal).

---

## 4. Agent Specifications

### 4.1 Discovery Agent

**Name:** `discovery`
**Purpose:** Find new or changed SAP ecosystem content across configured sources, respecting crawl policy, and produce normalized candidate items with provenance — without any generative reasoning (pure deterministic acquisition).
**Inputs:**
- Scheduler signal (per source schedule) or manual re-crawl request.
- Source registry rows (`sources`): url, type, tier, schedule, content hash, auth config, robots policy.
- Prior `source_versions` for change gating.
**Outputs:**
- `candidate_items[]` artifact: `{ source_id, url, retrieved_at, content_hash, tier, normalized_text, raw_ref, policy_ok }`
- Updated `crawl_runs`, `source_versions`, `sources.content_hash`.
**Prompt template:** *None — Discovery is T0. No model call. All parsing/normalization/hashing is code (HTML→text, RSS→feed items, sitemap discovery, robots.txt + rate-limit enforcement).*
**Tools:**
- HTTP fetcher with robots.txt + rate-limit + auth-boundary enforcement (FR-007, NFR-011).
- Parser adapters: HTML, RSS/API, structured docs, sitemap (FR-002).
- Normalizer + content-hash (SHA-256) functions (FR-005).
- Source-registry read/write; `crawl_runs` writer.
- **Forbidden:** any LLM call, any deployment action.
**Memory:** Ephemeral per run + durable `source_versions` (provenance) + `sources` registry state. No long-term model memory.
**Retry policy (orchestrated activity):** max attempts 3, initial interval 30s, backoff ×2, max 10m, per-URL. Idempotent via `run_id` + `source_id + retrieved_at` uniqueness.
**Error handling:**
- Unavailable source → retry/backoff → after attempts exhausted, mark source `unhealthy`, emit alert (FR-055).
- Changed page structure → quarantine parser result (`needs_review`), keep last good version.
- robots/terms violation → abort crawl, log compliance event, never bypass (NFR-011).
- Partial failure → only failed URLs re-queued; successful items persist (no all-or-nothing at this stage).
**Evaluation criteria:**
- Provenance completeness: 100% of candidate items carry url + retrieved_at + content_hash (FR-005).
- Policy compliance: 0 violations across golden compliance tests (FR-007, NFR-011).
- Source-specific acquisition: all 4 parser types pass fixture tests (FR-002).
**Success criteria:** Every scheduled source either produces a `candidate_items` artifact (or a clean "unchanged" skip via hash), with crawl policy enforced, provenance recorded, and run fully replayable with no duplicates.

---

### 4.2 Change Agent

**Name:** `change`
**Purpose:** Determine whether content materially changed and classify the change type — the deterministic gate that decides whether expensive semantic analysis runs at all (ADR-0006).
**Inputs:**
- `candidate_items` (new snapshot, hash, normalized text) + previous `source_versions` snapshot.
**Outputs:**
- `change_record`: `{ version_id, prior_version_id, diff_type: lexical|semantic|none, classification, classification_confidence, content_hash, relevant: boolean }`
- Signals "skip" (no meaningful change) → pipeline terminates for that item (cost gate).
**Prompt template:** `p_change_v1` (T1 model). Input is the normalized diff, never raw HTML:

```
You are the Change classifier for an SAP automation-intelligence platform.
Classify the following normalized diff between two versions of the same source
into EXACTLY ONE class.

Classes:
- new_capability     : a capability/feature is newly introduced
- enhancement        : an existing capability is extended or improved
- clarification      : documentation-only clarification of existing content
- deprecation        : something is deprecated or removed
- architecture       : a technical architecture or integration change
- event              : an announcement/event (webinar, release date, downtime)
- no_meaningful      : formatting, boilerplate, or editorial noise

Source authority tier: {tier}   (higher tier = more authoritative)
Diff excerpt (normalized): {diff_excerpt}

Return JSON only:
{"class":"...", "confidence":0.0-1.0, "reason":"one sentence"}

Rules:
- Only "no_meaningful" allows the pipeline to stop; anything else is meaningful.
- Do NOT infer facts beyond what the diff states. Mark them as inferred if you do.
- If the diff is ambiguous between two classes, pick the more specific one and
  keep confidence ≤ 0.6.
```
**Tools:**
- Lexical diff generator (deterministic) — token/line-level (FR-009).
- Semantic diff trigger (embedding similarity, T1) for near-identical rewording (FR-009).
- Hash gate (FR-006).
**Memory:** Read `source_versions` history; writes `changes`. No long-term memory.
**Retry policy:** max 2 attempts, 10s interval, no backoff (cheap call). Non-retryable: schema validation failure (reclassify via Evidence/review).
**Error handling:**
- Diff engine exception → re-queue to worker, alert on repeat.
- Model output fails schema → retry once → `needs_review`.
- Both diff types disagree → treat as lexical change + lower confidence; surface to Evidence.
**Evaluation criteria:**
- Classification accuracy ≥ 85% on the Change golden set (FR-010; PRD precision gate).
- Cost gate: unchanged content produces zero model calls (FR-006) — assert in tests.
- No-meaningful precision: `no_meaningful` never misclassified as a capability (prevents noise).
**Success criteria:** Every version pair resolves to a classified `change_record`; unchanged content costs nothing; meaningful changes are flagged with a confidence that downstream agents can use.

---

### 4.3 Evidence Agent

**Name:** `evidence`
**Purpose:** Establish how trustworthy a finding is — score evidence confidence, merge multi-source coverage into one canonical finding, and label every promoted fact confirmed/inferred/speculative.
**Inputs:**
- `change_record` + candidate item(s), source authority tier, retrieval metadata.
- Other source versions that reference the same claim (corroboration).
**Outputs:**
- `evidence_package`: `{ canonical_finding_id, facts[], confidence, labels, sources[] }`
- `facts[]`: each `{ fact, label: confirmed|inferred|speculative, evidence_refs[], confidence }`.
**Prompt template:** `p_evidence_v1` (T1/T2). Input is normalized facts + source metadata:

```
You are the Evidence agent. Judge the reliability of the following facts about an
SAP ecosystem change, each already normalized and de-duplicated.

Per fact, assign:
- label: confirmed (explicitly stated by an authoritative source)
         inferred (reasonably derived, but not explicitly stated)
         speculative (possible, low confidence)
- confidence: 0-1
- evidence_refs: the source_id + locator that support it (must be listed here)

Authority tiers: 1=SAP docs, 2=SAP announcements, 3=SAP Community, 4=partner,
5=customer, 6=general discovery. Recency: days since retrieval.
Corroboration: number of independent sources stating the same fact.

Fact list with context: {facts_with_sources}

Return JSON only:
{"facts":[{"fact":"...","label":"...","confidence":0-1,"evidence_refs":["..."],"reason":"..."}]}

Rules:
- A claim with no evidence_ref is DROPPED, never accepted silently.
- Conflicting sources: keep the claim, reduce confidence, note the conflict.
- Benefits stated by the source are "confirmed"; benefits you derive are
  "inferred" and must be labeled as such (FR-018).
```
**Tools:**
- Canonical-finding merge (deterministic fuzzy match on normalized title+body) — FR-012 (dedup ≥ 90%).
- Source-authority lookup, corroboration counter, recency calculator — FR-011.
**Memory:** Reads `source_versions`/`changes`; writes `findings` (canonical) + `evidence`. No long-term memory.
**Retry policy:** max 2 attempts, 15s interval. Non-retryable: merge conflict (route to Review for canonical-key adjudication).
**Error handling:**
- Duplicate detected post-hoc → merge under canonical finding, update `canonical_key` (FR-012).
- Unresolvable source conflict → retain both claims, reduce confidence, flag `needs_review`.
- Label missing on a fact → fact quarantined, never promoted.
**Evaluation criteria:**
- Duplicate consolidation ≥ 90% on multi-source fixture set (FR-012, PRD).
- Label correctness ≥ 85% on Evidence golden set (FR-013).
- 100% of promoted facts carry evidence_refs or explicit inferred/speculative label (FR-013, NFR-001).
**Success criteria:** Every priority finding is backed by a traceable evidence package; no unlabeled fact is promoted; multi-source coverage is deduplicated into canonical findings; conflicts are surfaced with reduced confidence, never hidden.

---

### 4.4 Automation Agent

**Name:** `automation`
**Purpose:** Extract the automation pattern from a change — the business problem, process, type, workflow, human involvement, and outcome — and produce a structured Automation Card mapped to the taxonomy.
**Inputs:**
- Canonical `finding` (from Evidence) + its `evidence_package`.
- Taxonomy reference (current taxonomy_version): FI/CO, SD, MM, PP, QM, PM/EAM, EWM, TM, PS, PLM, MDG, GRC, Treasury, CRM, HCM, procurement; industries.
**Outputs:**
- `automation_card`: `{ automation_id, finding_id, business_problem, process_area[], products[], automation_type, trigger, inputs[], decisions[], workflow[], human_involvement[], outcome, taxonomy_map[], benefits[], benefits_flagged[], evidence_refs[] }` (FR-015–019).
**Prompt template:** `p_automation_v1` (T2). Input is the evidence-backed finding text:

```
You are the Automation Intelligence agent. From the evidence-backed finding below,
extract the automation pattern.

Only extract a field when the finding supports it; otherwise set it to null.
Never fabricate. Benefits are recorded ONLY when the source states them; benefits
you derive yourself must be marked inferred and listed separately.

Automation types: workflow | RPA | document | api | event_driven | ai_assisted |
agentic | predictive | custom.

Business areas (taxonomy v{taxonomy_version}): {taxonomy_areas}

Finding (normalized + evidence-referenced): {finding_text}

Return JSON only, matching this schema:
{automation_type, trigger, inputs, decisions, workflow, human_involvement,
 outcome, products, process_area, business_problem, benefits_stated,
 benefits_inferred, taxonomy_map, evidence_refs, confidence}

Rules:
- Every extracted value cites evidence_refs; a value without support is dropped.
- If the change is not an automation pattern, return {"automation_type": null,
  "reason": "..."} and the pipeline stops for this item.
```
**Tools:**
- Taxonomy lookup (deterministic mapping table, versioned) — FR-019.
- Canonical automation-ID assignment (deterministic `automation_<slug>`) with temporal lineage — FR-020.
**Memory:** Reads findings/evidence; writes `automations`. No long-term memory.
**Retry policy:** max 2 attempts, 20s interval; on schema failure retry with stricter prompt, then `needs_review`.
**Error handling:**
- Empty extraction on a meaningful finding → re-run once with expanded context → `needs_review`.
- Taxonomy term not found → nearest-match via embedding, flagged `speculative`, surface for taxonomy evolution (FR-061).
- Benefit inference → always `benefits_inferred`, never merged into stated benefits (FR-018).
**Evaluation criteria:**
- Extraction field accuracy ≥ 85% on Automation golden set (FR-015).
- Automation-type classification accuracy ≥ 85% (FR-016).
- Benefit discipline: 0 stated-benefits polluted by inferred benefits across golden set (FR-018).
- Taxonomy mapping correctness ≥ 90% (FR-019).
**Success criteria:** Every meaningful automation finding becomes a structured Automation Card with canonical ID, taxonomy mapping, stated-vs-inferred benefits separated, and every field evidence-referenced.

---

### 4.5 Architecture Agent

**Name:** `architecture`
**Purpose:** Reconstruct the technical architecture behind a change — the flow trigger→data→processing→AI/rules→decision→workflow→API/event→target→monitoring — and identify SAP technologies, separating confirmed from inferred components.
**Inputs:**
- `automation_card` + `evidence_package`.
- Technology vocabulary (S/4HANA, BTP, Integration Suite, APIs, Event Mesh, Build, Process Automation, AI, Data Cloud, Datasphere, HANA, Cloud ALM, related services) — FR-022.
**Outputs:**
- `architecture_graph`: `{ nodes[], edges[], flow, technologies[], confirmed_vs_inferred, integration_patterns[], human_in_loop[], validation_flags[], diagram_summary, evidence_refs[] }` (FR-021–027).
**Prompt template:** `p_arch_v1` (T3 — most capable model). Input is evidence + the card:

```
You are the Architecture Reconstruction agent. Reconstruct the technical
architecture described by this evidence-backed automation card.

Produce:
1. flow: an ordered chain of stages:
   trigger → data source → processing → AI/rules → decision →
   workflow → API/event → target → monitoring
   (omit stages with no evidence; never invent them)
2. nodes/edges: the architecture graph entities and relations
3. technologies: match ONLY against this vocabulary {technology_vocab};
   a technology you cannot evidence is omitted or marked inferred
4. integration_patterns: sync_api | async_event | batch | workflow |
   document | agent (one per edge where supported)
5. human_in_loop: controls, approvals, exception paths if evidenced
6. validation_flags: security | audit | resilience | observability |
   data_governance concerns to verify

Card + evidence: {card_with_evidence}

Return JSON only per schema {schema}.
Every component is labeled confirmed (evidenced) or inferred (derived). A
component with neither label is invalid output.
```
**Tools:**
- Diagram generator (deterministic render from graph → Mermaid/SVG text) — FR-024.
- Technology-vocabulary matcher (deterministic + embedding assist) — FR-022.
**Memory:** Reads automations/evidence; writes `architecture_nodes`/`architecture_edges` (+ generated diagram artifact). No long-term memory.
**Retry policy:** max 3 attempts, 30s → 60s backoff (expensive call); fallback model tier on persistent failure, then `needs_review`.
**Error handling:**
- Flow stage without evidence → omitted (confirmed-empty), noted in `validation_flags`.
- Technology match uncertain → `inferred` label, referenced for human validation (FR-023).
- Graph schema violation → retry; if still invalid, degrade to text-summary-only + `needs_review`.
**Evaluation criteria:**
- Architecture usefulness ≥ 80% (SAP-architect review of generated summaries) — FR-024, PRD.
- Technology identification precision/recall ≥ 80% on golden architecture set — FR-022.
- Confirmed/inferred separation: 100% of components carry a label (FR-023).
- Human-in-loop capture presence on fixtures with approval/exception paths (FR-026).
**Success criteria:** Every automation card yields a valid architecture graph + logical diagram + text summary, every component labeled confirmed/inferred, technologies matched only against the vocabulary, and the summary judged useful by SAP architects ≥ 80% of the time.

---

### 4.6 Opportunity Agent

**Name:** `opportunity`
**Purpose:** Determine whether a finding is a real opportunity — gap classification (standard/configurable/extensible/partner-provided/genuinely missing), build path, customer pain, ECC-to-S/4 & clean-core implications, reuse, and a human validation checklist.
**Inputs:**
- `automation_card` + `architecture_graph` + `evidence_package`.
- Customer context (private knowledge spaces, existing implementations) — FR-062.
**Outputs:**
- `opportunity_assessment`: `{ gap_classification, build_path, customer_pain, manual_effort, ecc_to_s4_flag, clean_core_flag, reuse_assessment, dependencies[], validation_checklist[] }` (FR-028–033).
**Prompt template:** `p_opp_v1` (T1/T2):

```
You are the Opportunity Validation agent. Assess whether this automation finding
is a build/replace opportunity and how to classify it.

gap_classification (exactly one):
  standard | configurable | extensible | partner_provided | genuinely_missing

build_path (exactly one):
  standard_sap | configuration | extension | btp_automation | custom_app |
  ai_agent | external_integration

Answer with evidence. For ECC-to-S/4 and clean-core, only flag when the finding
supports it (or mark inferred explicitly). Produce a concrete validation_checklist
(3-7 items) a human can verify.

Card + architecture + evidence: {context}

Return JSON only per schema {schema}.
Scores and classifications here are RECOMMENDATIONS, not facts.
```
**Tools:**
- Reuse index lookup across tenants/industries (deterministic query) — FR-032.
- Dependency tracker (release/edition/licensing/services) — FR-032.
**Memory:** Reads automations/architecture; writes `opportunities`. No long-term memory.
**Retry policy:** max 2 attempts, 15s interval; then `needs_review`.
**Error handling:**
- Genuinely-missing classification must be validated by a human — always routes to Review (FR-028).
- Dependency unknown → recorded as "to-verify" checklist item, not assumed.
- Clean-core/ECC flag without evidence → dropped or marked inferred (FR-030).
**Evaluation criteria:**
- Gap classification accuracy ≥ 80% on Opportunity golden set (FR-028).
- Build-path accuracy ≥ 85% (FR-031).
- Validation checklist present on 100% of opportunities (FR-033).
**Success criteria:** Every opportunity carries a gap classification, build path, evidence-backed pain mapping, migration/clean-core implications, reuse + dependency assessment, and a human validation checklist; genuinely-missing items always reach a human.

---

### 4.7 Scoring Agent

**Name:** `scoring`
**Purpose:** Produce a deterministic, explainable score for each opportunity using the fixed weight vector, plus rationale per metric — the input to the Saturday ranking and backlog.
**Inputs:**
- `opportunity_assessment` (for the metric inputs) + optional reviewer overrides (FR-036).
**Outputs:**
- `score_vector`: `{ opportunity_id, metrics: {business_value, automation_potential, technical_feasibility, reusability, demand, differentiation, clean_core}, weights, complexity_penalty, composite, rationale_per_metric[] }` (FR-034–035).
**Prompt template:** `p_score_v1` (T1). Note: this is the *only* step allowed to produce numbers, and it explains each one:

```
You are the Scoring agent. Score this opportunity against 7 metrics, each 0-10.

Weights: business_value 20%, automation_potential 15%, technical_feasibility 15%,
reusability 15%, demand 10%, differentiation 10%, clean_core 10%.
Apply a complexity penalty up to -15% based on build/ops complexity, and explain it.

For each metric give a value, a one-sentence rationale, and the evidence it rests
on. The composite is a RECOMMENDATION: a reviewer may override any metric with a
reason, which is recorded and audited.

Opportunity assessment: {assessment}

Return JSON only per schema {schema}.
```
**Tools:**
- Deterministic composite calculator (weighted sum − penalty) — FR-034.
- Ranking sorter with stable tie-break (composite desc, then recency, then id) — FR-037.
- Override ledger (previous/new value + actor + reason) — FR-036.
**Memory:** Reads opportunities/overrides; writes `scores`. No long-term memory.
**Retry policy:** max 2 attempts, 10s interval (cheap). Non-retryable: no valid rationale → `needs_review` (NFR-008 explainability is mandatory).
**Error handling:**
- Metric outside 0–10 → clamp + flag, rationale still required.
- Composite math is deterministic code (never the model) — model only supplies metric values + rationales.
- Reviewer override changes metric → composite recomputed in code, override recorded (FR-036).
**Evaluation criteria:**
- Explainability: 100% of metrics carry rationale + evidence (NFR-008, FR-035).
- Rank stability: re-scoring identical input yields identical rank (FR-037) — asserted in tests.
- Calibration: mean absolute error vs reviewer scores ≤ 1.0 on calibration set (Continuous Learning).
**Success criteria:** Every opportunity has a complete, explainable score vector; ranking is deterministic with a documented tie-break; reviewer overrides are recorded and recompute the composite in code; no score is ever presented without its rationale.

---

### 4.8 Knowledge Agent

**Name:** `knowledge`
**Purpose:** Maintain the knowledge graph — resolve entities across sources, link sources→findings→automations→products→processes→industries→technologies→APIs→events→architectures→opportunities, and power lineage, temporal and cross-domain queries, plus related-pattern recommendations.
**Inputs:**
- All prior artifacts: `change_record`, `evidence_package`, `automation_card`, `architecture_graph`, `opportunity_assessment`, `score_vector`.
- Existing graph state (Neo4j).
**Outputs:**
- `relationships`: entity resolutions, graph upserts (nodes/edges with evidence + confidence at relationship level), and recommendation candidates (FR-038–042, 044).
**Prompt template:** `p_knowledge_v1` (T2):

```
You are the Knowledge Graph agent. Given new artifacts and the current graph
context, produce entity resolutions and relationships.

- Resolve entities against existing graph nodes (same product/process/industry/
  technology/API/event across sources) using exact + semantic matching.
- Produce typed edges with relation labels, confidence, and the evidence_ref that
  supports each edge. Edges without evidence are invalid.
- Identify which time-window (30/90/180-day) and cross-domain (e.g. AI automation
  affecting MM + manufacturing) queries this new data should surface in.
- Recommend related patterns / reusable architectures.

New artifacts: {artifacts}
Existing graph context: {graph_context}

Return JSON only per schema {schema}.
```
**Tools:**
- Entity-resolution index (deterministic exact + embedding nearest-neighbor) — FR-038.
- Graph upsert (Neo4j) with evidence/confidence on nodes and edges — FR-041.
- Lineage writer (source→extraction→validation→score→report) — FR-042.
- Semantic-search + facet index (Postgres FTS + Qdrant; ADR-0014) — FR-043.
**Memory:** The Neo4j graph *is* the agent's memory — persistent, queryable, versioned at relationship level (FR-041). No model long-term memory.
**Retry policy:** max 2 attempts, 15s interval; graph conflicts are deterministic and retried, not model-routed.
**Error handling:**
- Entity resolution ambiguity → create candidate node with `confidence < 0.6` + `needs_review` rather than merging wrong entities.
- Duplicate merge under canonical finding (post-hoc) → graph edges re-pointed, history preserved.
- Embedding index drift → re-embed only changed content (ADR-0006), never full rebuild on each run.
**Evaluation criteria:**
- Time-window queries return correct 30/90/180-day change windows on fixture data (FR-039).
- Cross-domain query correctness (e.g., AI + MM + manufacturing) on golden queries (FR-040).
- Evidence present on ≥ 95% of graph edges (FR-041).
- End-to-end lineage walkable for every report finding (FR-042, NFR-001).
- Related-pattern recommendation relevance ≥ 80% (FR-044, PRD relevance gate).
**Success criteria:** The graph is always consistent with the evidence store; every node/edge is evidence-backed and confidence-labeled; temporal and cross-domain queries answer correctly; lineage from source to report is fully walkable; search p95 < 3s (NFR-009).

---

### 4.9 Review Agent

**Name:** `review`
**Purpose:** Route uncertain or high-impact items to humans, gate the pipeline at decision points, and capture reviewer feedback for continuous learning — the human-in-the-loop control (FR-056, FR-059).
**Inputs:**
- Any artifact flagged `needs_review` (or confidence below threshold) by upstream agents.
- Reviewer decisions + feedback from the Review Queue UI (FR-059).
**Outputs:**
- `review_queue_entry`: `{ entity_ref, reason, priority, proposed_action, suggested_decision, feedback_schema }`
- Promoted/rejected decisions that un-block the pipeline (orchestrator signal / queue event).
**Prompt template:** `p_review_v1` (T1):

```
You are the Review agent. For this flagged item, prepare the review request:
- summarize what is uncertain/high-impact and why it needs a human
- propose a default decision (promote as-is / promote with edits / reject / escalate)
- list the specific questions a reviewer should answer
- attach the feedback schema so reviewer input feeds continuous learning

Flagged item + context: {item_with_evidence}

Return JSON only per schema {schema}.
```
**Tools:**
- Threshold router (deterministic): confidence < 0.6 or impact = high → Review (FR-056).
- Feedback ingestion → golden-set growth + calibration (FR-059, 060).
**Memory:** Reads `reviews`, `audit_log`; writes review queue entries. Feedback persists as training/eval data (Continuous Learning).
**Retry policy:** max 2 attempts, 10s interval (cheap). A Review *gate* never auto-promotes on retry.
**Error handling:**
- Reviewer unavailable (timeout) → re-queue with priority decay; never auto-promote (FR-056).
- Conflicting reviewer decisions → escalate to senior reviewer (tenant_admin), audited.
- Feedback malformed → validation error surfaced to reviewer, not dropped.
**Evaluation criteria:**
- Routing precision/recall: low-confidence items are caught ≥ 90% (FR-056).
- Auto-promotion rate = 0: no `needs_review` item is ever promoted automatically (NFR-002, FR-056).
- Feedback capture completeness: 100% of review decisions append `audit_log` + feedback record (FR-059, FR-054).
**Success criteria:** No uncertain or high-impact item passes without a human; every review decision is captured as feedback that improves the golden set and calibration; review gates are auditable and resumable.

---

### 4.10 Report Agent

**Name:** `report`
**Purpose:** Compose the Saturday intelligence package — executive summary, meaningful changes, automation findings, top opportunities, heat maps, ECC-to-S/4 & clean-core flags — and export PDF/HTML/JSON/CSV and notify recipients (FR-045–051).
**Inputs:**
- Six-day window of: `change_records`, `automation_cards`, `architecture_graphs`, `opportunity_assessments`, `score_vectors` (since previous Saturday).
- Tenant configuration: recipients, filters, scoring weights, schedule (FR-051).
**Outputs:**
- `report_package`: `{ report_id, period, executive_summary, changes[], automation_cards[], top_opportunities[], heat_maps[], ecc_flags[], exports: {pdf, html, json, csv}, status }`
**Prompt template:** `p_report_v1` (T3):

```
You are the Report agent. Compose the "why it matters" narrative for this week's
SAP automation intelligence report. You are a DRAFTING agent only: a reviewer must
approve before publish.

Write an executive summary + per-headline "why it matters" narratives. Ground every
claim in the provided evidence-backed items. Do not introduce facts. Flag ECC-to-S/4
and clean-core opportunities in the executive section where they exist.

Week data (evidence-backed, already scored/ranked): {week_data}

Return JSON only per schema {schema}: executive_summary, narratives[],
heat_map_annotations[], flags[].
```
**Tools:**
- Deterministic composition: executive-summary structure, rankings (pre-computed by Scoring), heat maps (from graph aggregation), exports (PDF/HTML/JSON/CSV) — FR-048, 050.
- Notification sender (configurable recipients/schedule) — FR-051.
**Memory:** Reads the six-day window + tenant config; writes `reports`/`report_items` + export artifacts. No long-term model memory.
**Retry policy:** max 3 attempts, 30s → 120s backoff (expensive call); fallback model tier; report is atomic (NFR-002).
**Error handling:**
- Any section fails → retry; incomplete report is NEVER published (NFR-002) — pipeline alerts and blocks.
- Narrative hallucination guard → narrative must reference the evidence-backed items it synthesizes; otherwise dropped.
- Export failure (e.g., PDF) → retry exporter; degrade to JSON + alert (never publish partial package silently).
**Evaluation criteria:**
- Report completeness: all sections present in every published report (FR-045, NFR-002).
- Narrative groundedness: 0 fabricated claims in golden report evals (FR-047).
- Export correctness: PDF/HTML/JSON/CSV all parse + match on fixtures (FR-050).
- On-schedule: Saturday report generated and delivered within budget (NFR-009: < 30 min end-to-end).
- Configurable per tenant: recipients/filters/weights respected (FR-051).
**Success criteria:** A complete, evidence-grounded Saturday report is composed, reviewed, exported in all four formats, and delivered to configured recipients — or the pipeline alerts loudly rather than publishing a partial report.

---

### 4.11 Governance Agent

**Name:** `governance`
**Purpose:** Enforce source policy, model policy, RBAC, tenant isolation, audit, and cost budgets on every stage — the security and compliance backstop (FR-053–055, 057–058).
**Inputs:**
- Policy configuration (source policy, model policy, per-tenant budgets).
- Every agent envelope (for pre/post execution policy checks) + RBAC context + audit stream.
**Outputs:**
- `policy_events`: allow/deny decisions, audit-log entries, alert/runbook triggers, budget-breach records.
**Prompt template:** *Mostly T0 (deterministic policy engine). T1 only for risk-text classification if policy rules need natural-language triage — default no model call.*
**Tools:**
- Policy Decision Point (deterministic rules): source allow/deny, model allow/deny, per-tenant budget check — FR-055, NFR-012.
- RBAC enforcement at every query boundary + row-level-security backstop — FR-053, 057.
- Audit-log writer (`audit_log`), prompt/model version registry — FR-054.
- Alert + runbook dispatch — FR-058.
**Memory:** Reads policy config, budgets, audit stream; writes `audit_log`, `policy_events`, alerts. No model memory.
**Retry policy:** Deterministic policy checks are not model-routed; failures are fail-closed (deny + alert). max 2 attempts for audit-log persistence, with durable write-ahead.
**Error handling:**
- Policy violation → deny + alert + runbook (FR-058); never silently allow.
- Audit write failure → fail-closed (block the action), retry, alert.
- Budget breach → downgrade model tier (ADR-0003) or pause agent, alert (NFR-012).
- Unknown entity → deny by default (least privilege, FR-057).
**Evaluation criteria:**
- Zero policy bypass across the golden adversarial suite (FR-053, 057, NFR-004).
- 100% of denied actions produce an audit entry (FR-054).
- Tenant isolation: cross-tenant access provably denied in tests (FR-057).
- Budget enforcement: breaches detected and acted on (NFR-012).
- Auditability: every report finding traces to evidence (NFR-001).
**Success criteria:** No agent action occurs without policy check, RBAC, and audit; tenant isolation holds at every boundary; budget and model-policy violations are caught, alerted, and remediated; the platform is audit-ready at all times.

---

## 5. LLM Gateway Specification

The gateway is the single choke point for every model call — the component that makes the model-agnostic, cost-controlled, versioned AI layer possible (ADR-0003).

**Name:** `llm-gateway`
**Purpose:** Provide one model-agnostic facade over all providers, with versioned prompt templates, tiered model routing, caching, structured-output validation, retry/fallback, and budget accounting. No agent calls a provider directly.
**Inputs:**
- `gateway_request`: `{ task_tier, prompt_version, input_artifacts, schema, max_cost_budget, tenant_id }` (from any agent).
**Outputs:**
- `model_response`: `{ validated_json, model, model_version, prompt_version, usage, cost_usd, latency_ms, cache_hit }`
**Prompt template:** Templates are *content* managed in the prompt registry (versioned `p_*`), never hardcoded in agents. §4 lists the canonical v1 for each agent; the gateway resolves `(task_tier, prompt_version)` → template + model.
**Tools:**
- Provider adapters (pluggable): OpenAI (chat + embeddings), Gemini (fallback), open-source (self-hosted) — behind one interface (NFR-013).
- Tier router: task_tier → model (T1/T2/T3), budget-aware (NFR-012).
- Prompt-response cache + extraction cache (ADR-0006); identical inputs hit cache.
- JSON Schema validator; invalid → retry → `needs_review`.
- Token/cost accountant (per source/agent/tenant) + budget breaker.
**Memory:** Caches (deterministic-keyed), prompt registry, model registry, cost ledger. Stateless per call otherwise.
**Retry policy:** per tier: T1 max 2 @ 5s; T2 max 2 @ 10s; T3 max 3 @ 30s→60s; on persistent failure fall back to next model in tier, then `needs_review`. Idempotent via `run_id`.
**Error handling:**
- Provider outage → fallback adapter → alert; never silent failure.
- Schema validation failure → retry → `needs_review` (never accept unvalidated output).
- Budget exceeded → refuse call, downgrade tier or pause agent (NFR-012).
- Prompt-injection in ingested content → content treated as data (never instructions); gateway strips/escapes untrusted text before templating (FR, security).
**Evaluation criteria:**
- Model lock-in: swapping a provider is config-only; proven by adapter-contract tests (NFR-013).
- Cost: tiered routing holds p95 cost per task within budget (NFR-012).
- Deterministic caching: unchanged inputs → 0 model calls (ADR-0006).
- Structured output: 100% of accepted responses validate against schema.
**Success criteria:** Every model call in the platform flows through the gateway and is versioned, budgeted, validated, cached, and audited — with no provider-specific code anywhere outside it.

---

## 6. Cross-Agent Evaluation Harness

| Capability | Metric | Target | Golden set |
|---|---|---|---|
| Change classification | accuracy / precision (genuinely-new) | ≥ 85% | `golden/change_*` |
| Automation extraction | field accuracy + type accuracy | ≥ 85% | `golden/automation_*` |
| Evidence labeling | label correctness; dedup | ≥ 85%; dedup ≥ 90% | `golden/evidence_*` |
| Architecture | usefulness (SAP-architect review); tech-ID precision/recall | ≥ 80% | `golden/arch_*` |
| Opportunity | gap + build-path accuracy | ≥ 80% / 85% | `golden/opportunity_*` |
| Scoring | rank stability; calibration MAE | stable; MAE ≤ 1.0 | `golden/scoring_*` |
| Knowledge | temporal/cross-domain correctness; edge evidence | ≥ 95% edges | `golden/knowledge_*` |
| Report | groundedness (0 fabrications); on-schedule | 0; < 30 min | `golden/report_*` |
| Review | routing recall; auto-promotion = 0 | ≥ 90%; 0 | `golden/review_*` |
| Governance | policy-bypass = 0; tenant isolation | 0 | `golden/governance_*` |

- A prompt/model/classifier change triggers a regression run against the affected golden set before promotion (NFR-006, 014).
- Reviewer feedback (FR-059) is sampled to grow the golden sets (Continuous Learning, Phase 13/15).

---

## 7. Agent → Requirement Traceability

| Agent | FRs | NFRs | Phase(s) |
|---|---|---|---|
| Discovery | FR-001, 002, 003, 004, 005, 007 | NFR-007, 011 | 4 |
| Change | FR-006, 008, 009, 010 | NFR-012 | 5 |
| Evidence | FR-011, 012, 013, 014 | NFR-001 | 5 |
| Automation | FR-015, 016, 017, 018, 019, 020 | NFR-006 | 6 |
| Architecture | FR-021, 022, 023, 024, 025, 026, 027 | — | 7 |
| Opportunity | FR-028, 029, 030, 031, 032, 033 | — | 8 |
| Scoring | FR-034, 035, 036, 037 | NFR-008 | 8 |
| Knowledge | FR-038, 039, 040, 041, 042, 043, 044 | NFR-009 | 9 |
| Review | FR-056, 059 | NFR-002 | 12/15 |
| Report | FR-045, 046, 047, 048, 049, 050, 051 | NFR-002, 009 | 11 |
| Governance | FR-053, 054, 055, 057, 058 | NFR-001, 004, 005 | 2/12 |
| LLM Gateway | — | NFR-006, 012, 013 | 3/5 |

---

## 8. Definition of Done for This Document

This AI Layer specification is complete because:
- [ ] All 11 roster agents + the LLM gateway are specified to the 11-field template.
- [ ] Every agent has a concrete, versioned prompt template (or explicit "no model" for T0).
- [ ] Every agent maps to FR/NFR IDs in the RTM.
- [ ] Evaluation criteria reference PRD metric thresholds and golden-set harnesses.
- [ ] Success criteria are testable and operational, consistent with [19_Definition_of_Done](./19_Definition_of_Done.md).
