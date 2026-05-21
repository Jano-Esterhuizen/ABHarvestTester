agent: 'Scraper' parent_document: 'TestForge Architecture Decision Document' owner: 'Agile Bridge' date: '2026-05-21'

status: 'Design — pre-implementation' Scraper Agent — Detailed Design Companion document to the TestForge architecture. This document is the full specification for the Scraper agent: the second agent in the flow. It is responsible for producing a complete, test-ready API contract document by harvesting MCP descriptors, Swagger/OpenAPI documents, and — when neither is sufficient — crawling the codebase directly using the Repo Reader's outputs as its map.

Purpose & Position in the Flow The Scraper is the API contract layer of TestForge. The Repo Reader gives a high-level inventory of routes; the Scraper turns that inventory into a full, structured, test-writable specification of every endpoint — its schema, auth requirements, examples, error cases, and intended behaviour. The downstream Test Writers depend on this artefact to generate accurate tests.
CONFIG ──▶ ORC ──▶ REPO READER ──▶ ┌─────────────────┐ ──▶ WRITERS ──▶ REVIEWER │ SCRAPER │ │ (this agent) │ └─────────────────┘ │ └──▶ api-contract.md (endpoint-by-endpoint spec) Contract with the rest of the system Concern Commitment Inputs accepted context-document.md + codebase-overview.txt + repo_local_path (all from Repo Reader) Source preference MCP descriptors and Swagger/OpenAPI docs first; codebase crawl as fallback Outputs produced api-contract.md (required, single file) Side effects on target repo Read-only. Never writes, modifies, or commits to the target Failure mode Fail loudly with an explicit list of endpoints it could not characterise; never silently drop endpoints from the inventory Source merging When both MCP and Swagger exist, both are consumed and merged into one unified spec. Conflicts are surfaced, not silently resolved 2. Inputs The Scraper consumes everything the Repo Reader produced plus direct access to the cloned repository. The Orchestrator passes a single input object:

{ "context_document_path": "/runs/<run-id>/context-document.md", "codebase_overview_path": "/runs/<run-id>/codebase-overview.txt", "repo_local_path": "/tmp/testforge-repos/<hash>/", "repo_commit_sha": "<sha>", "output_path": "/runs/<run-id>/api-contract.md" } Required reads from context-document.md:

§1 Tech Stack — informs which framework idioms to look for during crawl §2 Repository Structure — the file tree map §4.1 Backend HTTP Routes — the starting inventory the Scraper expands §5 Data Models — feeds schema synthesis when no Swagger types exist §6 Authentication & Authorization — describes auth flow and role checks §11 Environment & Configuration — needed when documentation references env-driven URLs §12 Open Questions / Confidence Notes — sections marked low-confidence get extra verification during crawl The Scraper does not re-do the Repo Reader's work. It trusts the route inventory as the starting set and only adds endpoints if the crawl uncovers ones the Repo Reader missed (in which case it flags this back via the output).

Outputs The Scraper produces one artefact: api-contract.md. Written to the run's working directory. Markdown format with a strict schema so the Test Writers can reliably extract per-endpoint blocks by heading.
3.1 api-contract.md — Endpoint-by-endpoint specification A markdown document where each endpoint is its own subsection under a domain/resource grouping. Audience: the BE Test Writer agent, which will read this file and emit Playwright spec files from it.

Schema for api-contract.md
repo_name: <string> repo_commit_sha: <git SHA> scraped_at: <ISO 8601 timestamp> scraper_version: <semver> source_strategy: <mcp_only | swagger_only | mcp_and_swagger_merged | crawl_only | mixed> sources_consumed: mcp_files: [<path>, ...] # paths relative to repo root swagger_files: [<path>, ...] crawled_files: [<path>, ...] # only populated when crawl was used endpoint_count: <integer> confidence_summary: high: <integer> medium: <integer>

low: <integer>
API Contract
Overview
<2–4 paragraphs: what this API is, base URL(s), versioning, auth model, global conventions like pagination, error envelope, content-type defaults. Drawn from Swagger info block, MCP server descriptors, or — for crawl-only — synthesised from the codebase.>

Global Conventions
Base URL(s)
Production: <url or "Not detected">
Staging: <url or "Not detected">
Local dev: <url or "Not detected">
Source of base URL: <env var name, config file, Swagger servers block>
Authentication
Scheme: <bearer | session_cookie | basic | api_key | oauth2 | none>
Header / cookie name: <e.g., Authorization, X-API-Key, session_id>
Token acquisition: <login endpoint, OAuth flow, static env var>
Required env var(s): <e.g., API_TOKEN, USER_EMAIL/USER_PASSWORD>
Token lifetime: <if known>
Roles in this API: <list, cross-referenced with §6.1 of context document>
Error Envelope
<The standard error response shape used by this API. Drawn from Swagger components/responses or observed pattern in handlers.>

{ "error": { "code": "<string>", "message": "<string>", "details": <object?> } }
Pagination
Style: <offset | cursor | page-number | none>
Parameters: <limit, offset, page, cursor, etc.>
Response envelope: <how pagination metadata is returned>
Content Types
Request default: application/json
Response default: application/json
Exceptions: <list endpoints that diverge — file upload, etc.>
Endpoints
Endpoints are grouped by resource. Each endpoint follows the same sub-schema so the Test Writers can parse them uniformly.

Resource: <ResourceName>
<1–2 sentences: what this resource represents in domain terms. Cross-reference §7 Business Domain Glossary of the context document.>

<METHOD> <path>
Summary: <one-line purpose>
Purpose (detailed): <2–4 sentences explaining what the endpoint does, when it is called, what it changes, and why a tester should care.>
Source: <file path:line, e.g., src/routes/users.py:42>
Source type: <mcp | swagger | crawl | mcp+swagger | swagger+crawl>
Auth required: <yes | no | optional>
Roles allowed: <list of roles, or "any authenticated", or "public">
Rate limit: <if documented>
Idempotent: <yes | no | unknown>
Path parameters
Name	Type	Required	Description	Example
id	uuid	yes	User ID	550e8400-...
Query parameters
Name	Type	Required	Description	Default	Example
limit	int	no	Page size	20	50
Headers (non-auth)
Name	Required	Description	Example
Request body
Content-type: application/json
Schema:
{
  "field_name": "<type — required/optional — description>",
  ...
}
Example:
{ ... }
Responses
Status	Meaning	Body schema	Example
200	Success — user returned	(see below)	(see below)
401	Missing or invalid auth	error envelope	—
403	Authenticated but lacks role	error envelope	—
404	User not found	error envelope	—
422	Validation failure	error envelope with details[]	—
200 response schema
{ "id": "<uuid>", "email": "<string>", "role": "<enum: user|admin>" }
200 response example
{ "id": "550e8400-...", "email": "alice@example.com", "role": "user" }
Side effects
<What this endpoint changes in the system: DB writes, events published, emails sent, external service calls. Drawn from handler code during crawl.>

Notes for testers
<Anything the Test Writer should know: known quirks, ordering dependencies, data setup required, fields that look optional but aren't, etc.>

Confidence
Schema confidence: <high | medium | low>
Behaviour confidence: <high | medium | low>
Rationale: <one line — e.g., "Schema from Swagger; behaviour confirmed by reading handler in src/routes/users.py:42–88">
<next endpoint>
...

Endpoints Not Characterised
Endpoints discovered but not fully specified. The Test Writer should treat these as out-of-scope unless the gap can be filled.

Method	Path	Source	Reason not characterised
GET	/internal/debug	crawl	Handler exists but no schema; appears to be debug-only
Discrepancies & Open Questions
Where MCP, Swagger, and the codebase disagreed, or where the Scraper was uncertain. The Test Writers should treat affected endpoints with care.

POST /api/users — body schema conflict: Swagger declares email required; handler at src/routes/users.py:55 also requires name. Treated the handler as authoritative.
DELETE /api/projects/{id} — auth conflict: MCP descriptor marks this as public; handler requires admin role. Treated handler as authoritative.
... Why a strict schema The BE Test Writer reads this file as its primary source of truth. It expects exact heading patterns (#### <METHOD> <path>) to enumerate endpoints, and exact sub-headings (##### Request body, etc.) to extract per-endpoint fields. Schema drift here breaks the writer.

Source Strategy — MCP, Swagger, Crawl Three sources are possible for any given endpoint. The Scraper's job is to consult them in priority order, merge what it gets, and crawl only when necessary.

4.1 Source priority Priority Source When used 1 MCP descriptors If the repo contains MCP server definitions (e.g., mcp.json, .mcp/, files with mcpServers blocks, descriptors emitted by frameworks like FastMCP) 2 Swagger / OpenAPI If the repo contains openapi.yaml, openapi.json, swagger.yaml, swagger.json, or generates one at a known build path 3 Code crawl Always run as a verification pass when either of the above is present; run as the sole source when neither is 4.2 When both MCP and Swagger exist — merge Both are consumed in full. Output strategy: source_strategy: mcp_and_swagger_merged. Per-endpoint merge rules:

If both sources describe the same endpoint and agree: take either, mark Schema confidence: high, list both in Source. If both describe it but disagree: list both, take the codebase as tiebreaker via a targeted crawl read of the handler. The disagreement and resolution are recorded under Discrepancies & Open Questions. If only one source describes it: take that one, mark Schema confidence: medium, schedule a targeted crawl read to upgrade to high if the handler is unambiguous. 4.3 When neither exists — full repo crawl The Scraper falls back to crawling the codebase. This is the heavyweight path. Strategy:

Start from §4.1 Backend HTTP Routes of the context document — that's the inventory.

For each row in that inventory, walk routes → controllers → handlers → services → models, reading each file in full. Specifically:

The route file gives method + path + handler reference. The handler/controller gives request parsing, validation, and response shape. The model file (cross-referenced with §5 Data Models in the context document) gives field types and constraints. Middleware referenced by the route gives auth requirements and role checks. Services called by the handler reveal side effects (DB writes, external calls). Run a second sweep of the repo to find endpoints the Repo Reader may have missed. Look for the same route-definition patterns the Repo Reader used (Pass 1 heuristics in the Repo Reader spec, §4.2). Any endpoint not in §4.1 is added to the output with source_type: crawl_only and a Schema confidence: medium pending the same handler-reading treatment.

Synthesise the per-endpoint spec by reading the handler chain end-to-end. Type information comes from:

ORM model definitions (for response shapes and persisted fields) Validation declarations (Pydantic models, Zod schemas, Joi, class-validator decorators, Rails strong_params, etc.) — for request body shapes Return statements and serialisers — for response shapes Test fixtures, if present, as a sanity check for example values 4.4 When MCP/Swagger exist but are partial Common case. Some endpoints are documented, some are not. The Scraper:

Treats documented endpoints per §4.2. Treats undocumented endpoints per §4.3. Sets source_strategy: mixed. 4.5 Verification crawl is always run Even when MCP and Swagger are both present and complete, the Scraper runs a lightweight verification pass: confirm each documented endpoint actually has a matching handler in the codebase, and flag any documented endpoints with no handler (stale docs) under Endpoints Not Characterised.

Analysis Strategy — Hybrid Pipeline Like the Repo Reader, the Scraper uses heuristics to narrow scope and LLM calls to synthesise. The pipeline runs in passes.
5.1 Pass 0 — Source Discovery No LLM. Pure code. Walks the repo (using the Repo Reader's file inventory if available; otherwise its own walk) and detects:

MCP indicator Treatment mcp.json, .mcp/, mcp.config.* Read in full Files declaring mcpServers block Read in full Python files with @mcp.tool, mcp.server.Server(...) Read in full TypeScript/Node files importing @modelcontextprotocol/sdk Read in full Swagger indicator Treatment openapi.{yaml,yml,json}, swagger.{yaml,yml,json} Read in full Files under api-docs/, docs/api/, openapi/ Read in full Framework decorators that generate Swagger (FastAPI auto-docs, NestJS @ApiTags, Springdoc annotations, drf-yasg) Note the generator; if a built spec exists at a known path, read it; otherwise treat the decorators as inline Swagger Output of Pass 0: a SourceManifest listing which strategy applies (mcp_only, swagger_only, mcp_and_swagger_merged, crawl_only, mixed) and the paths of all source files found.

5.2 Pass 1 — Parse Documented Sources For each MCP and Swagger file found in Pass 0: parse it deterministically (no LLM). MCP descriptors and OpenAPI documents are both structured formats with well-defined parsers — we use them.

Library / approach Source type openapi-spec-validator + PyYAML/orjson OpenAPI/Swagger Custom MCP descriptor parser (per current MCP schema spec) MCP Build an intermediate DocumentedEndpoints structure: a dict keyed by (method, normalised_path) holding the merged information from all documented sources, with provenance per field (so we know which fields came from MCP, which from Swagger, which conflict).

5.3 Pass 2 — Crawl Plan Compare DocumentedEndpoints (from Pass 1) with §4.1 of the context document (the inventory):

In docs ∩ inventory: schedule a lightweight verification read of the handler. In docs only: schedule a verification read; if handler is missing, mark as stale docs. In inventory only: schedule a full crawl read of the handler chain. Neither (discovered during Pass 0's second sweep): schedule a full crawl read. Output: a CrawlPlan — an ordered list of files to read in full, deduped, with the reason each one is scheduled.

5.4 Pass 3 — Targeted LLM Reads For each file in the CrawlPlan, send the file contents to the LLM (Claude Sonnet 4) with a focused prompt:

"For each route handler in this file, extract: method, path, auth requirements, role checks, request body schema, response shapes per status code, side effects, and any notes a tester should know. Respond as JSON with this schema."

Batched in groups of ~5–8 files per call to stay under context limits. Each batch produces a partial CrawlFindings object that gets merged into a running aggregate.

When a handler delegates to a service or model, the LLM is instructed to flag the dependency but not chase it inline — those files are queued for a follow-up batch. This keeps individual prompts focused and avoids quadratic blow-up.

Budget control: default ceiling of 250K input tokens of source code across Pass 3. If exceeded, lowest-priority files (handlers for endpoints already fully documented by MCP + Swagger agreement) are demoted to "summary only" — first 50 lines + last 20 lines.

5.5 Pass 4 — Merge & Reconcile Pure code, no LLM. Merge DocumentedEndpoints (Pass 1) with CrawlFindings (Pass 3) into a single UnifiedEndpoints structure. Per-field merge rules:

Field Rule method, path Must match; mismatch is a parser bug, raise auth requirement Code wins over docs; record conflict roles Code wins; record conflict request schema Code wins on required-field set; docs win on field descriptions response schema Code wins on field set; docs win on examples and descriptions status codes Union of both; for each status, code's body shape wins side effects Code-only (docs rarely capture this) Every conflict is recorded for the Discrepancies & Open Questions section of the output.

5.6 Pass 5 — Synthesis Two LLM calls (Claude Sonnet 4):

Per-endpoint markdown synthesis — given the UnifiedEndpoints aggregate plus the schema template, generate one markdown block per endpoint. Batched (~10 endpoints per call) to control context size. Strict instruction: every required sub-heading present; unknowns marked "Not detected"; no invented fields. Document assembly — given all endpoint blocks plus global metadata (base URLs, auth scheme, error envelope, pagination, conventions), assemble api-contract.md with the global Overview and Conventions sections. 5.7 Pass 6 — Validation A pure-code validator (no LLM) checks:

Frontmatter is well-formed YAML and contains all required keys All global sections present: Overview, Base URL(s), Authentication, Error Envelope, Pagination, Content Types Every endpoint block has all required sub-headings endpoint_count in frontmatter matches the actual number of endpoint blocks No endpoint has zero responses listed Confidence field is one of the allowed enum values If validation fails: one retry of Pass 5 with the validator's complaints fed back. If it fails again: emit what we have, log gaps, raise a warning to the Orchestrator. Do not silently ship malformed output.

Tools Used by the Agent Tool Purpose When used file_read_tool Read individual files Pass 0, Pass 1, Pass 3 directory_list_tool Walk the file tree for source discovery Pass 0 openapi_parser_tool Deterministic parse of Swagger/OpenAPI documents Pass 1 mcp_descriptor_parser_tool Deterministic parse of MCP descriptor files Pass 1 file_write_tool Write api-contract.md Pass 5 / Pass 6 schema_validator_tool Validate api-contract.md against its schema Pass 6 openapi_parser_tool and mcp_descriptor_parser_tool are new and need to be implemented under src/testforge/tools/spec_parsers.py. The schema_validator_tool from the Repo Reader is extended with a validate_api_contract function.

CrewAI Agent Definition 7.1 agents.yaml scraper: role: "API Contract Specialist" goal: > Produce api-contract.md: a complete, endpoint-by-endpoint specification of every HTTP endpoint in the target repository. Prefer MCP and Swagger sources; merge them when both exist; fall back to a full codebase crawl when neither is sufficient. Honest about confidence; explicit about discrepancies; never silently drops endpoints. backstory: > You are an API archaeologist. You read OpenAPI documents and MCP descriptors fluently, but you don't trust them blindly — you verify against the handler code, because docs lie and code doesn't. When the docs are missing, you read controllers end-to-end and synthesise the contract from what the code actually does. You report what you know, what you guessed, and what you couldn't determine. tools:

file_read_tool
directory_list_tool
openapi_parser_tool
mcp_descriptor_parser_tool
file_write_tool
schema_validator_tool llm: claude-sonnet-4 max_iter: 5 memory: true verbose: true 7.2 tasks.yaml discover_sources: description: > Walk the repository at repo_local_path and detect MCP descriptors and Swagger/OpenAPI documents. Produce a SourceManifest declaring the source_strategy (mcp_only | swagger_only | mcp_and_swagger_merged | crawl_only | mixed) and the paths of every source file found. expected_output: > A SourceManifest with {source_strategy, mcp_files, swagger_files, swagger_generator_hint?}. agent: scraper
parse_documented_sources: description: > Parse each MCP and Swagger file in the SourceManifest using deterministic parsers. Build a DocumentedEndpoints dict keyed by (method, path) with per-field provenance so conflicts can be detected later. expected_output: > A DocumentedEndpoints structure listing every endpoint that appears in any documented source, with provenance. agent: scraper context: - discover_sources

build_crawl_plan: description: > Compare DocumentedEndpoints with §4.1 of context-document.md. Schedule verification reads for documented endpoints and full crawl reads for undocumented ones. Produce a CrawlPlan listing files to read in full, each annotated with the reason it was scheduled. expected_output: > A CrawlPlan: ordered list of file paths with rationale per file. agent: scraper context: - parse_documented_sources

execute_crawl: description: > For each file in the CrawlPlan, extract route handler details: method, path, auth, roles, request schema, response shapes per status, side effects, tester notes. Batch reads (5–8 files per LLM call). Respect the source-token budget. Aggregate into CrawlFindings. expected_output: > A CrawlFindings structure: per-endpoint extracted details with source file:line references for traceability. agent: scraper context: - build_crawl_plan

merge_and_reconcile: description: > Merge DocumentedEndpoints and CrawlFindings into a single UnifiedEndpoints structure using the field-by-field merge rules. Record every conflict for the Discrepancies section of the output. expected_output: > A UnifiedEndpoints structure and a Discrepancies list. agent: scraper context: - parse_documented_sources - execute_crawl

synthesise_api_contract: description: > Given UnifiedEndpoints, global metadata, and the api-contract.md schema template, produce the full markdown contract. Every required heading must appear. Unknown values marked "Not detected." No invented fields. Each endpoint includes its source provenance and confidence rating. expected_output: > A markdown string conforming to the api-contract.md schema. agent: scraper context: - merge_and_reconcile

validate_and_write: description: > Run the schema validator over api-contract.md. If it fails, retry synthesis once with the validator's feedback. Write the artefact to output_path. Update shared state with the file path and an endpoint coverage summary. expected_output: > Path to api-contract.md plus a validation report and coverage summary. agent: scraper context: - synthesise_api_contract 7.3 Updates to TestForgeState Two new fields on the shared state to expose the Scraper's outputs to downstream agents:

Add to TestForgeState:
api_contract_path: str = "" # Path to api-contract.md api_contract_source_strategy: str = "" # mcp_only | swagger_only | merged | crawl_only | mixed api_endpoint_count: int = 0 api_endpoints_low_confidence: list = field(default_factory=list) # [(method, path), ...] — flagged for the Test Writers to handle with care api_discrepancies: list = field(default_factory=list) # Surface count to the Reviewer for failure-triage context 7.4 Schema Validator extension Extend the validator at src/testforge/tools/schema_validator.py with a function for the API contract:

REQUIRED_GLOBAL_SECTIONS = [ "# API Contract", "## Overview", "## Global Conventions", "### Base URL(s)", "### Authentication", "### Error Envelope", "### Pagination", "### Content Types", "## Endpoints", "## Endpoints Not Characterised", "## Discrepancies & Open Questions", ]

REQUIRED_ENDPOINT_SUBHEADINGS = [ "##### Path parameters", "##### Query parameters", "##### Headers (non-auth)", "##### Request body", "##### Responses", "##### Side effects", "##### Notes for testers", "##### Confidence", ]

def validate_api_contract(md: str) -> ValidationResult: # 1. Frontmatter parses; required keys present # 2. Global sections appear in order # 3. Every endpoint block matches the pattern #### \<METHOD> <path>`` # 4. Every endpoint block contains all required sub-headings # 5. endpoint_count in frontmatter matches counted endpoint blocks # 6. Confidence values are in {high, medium, low} ... 8. Operational Prompt — Embedded Agent Instructions The Scraper's system prompt at runtime. Mirrors the BE Test Writer prompt style: imperative, scoped, with explicit ask-points.

You are an API contract specialist. Your sole responsibility is to produce a single artefact, api-contract.md, describing every HTTP endpoint in the target repository. You do not write tests, you do not run code, you do not modify the repo. You read, parse, and synthesise.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ INPUTS (priority order) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MCP descriptors found in the repository. Highest authority for endpoints they describe.
Swagger / OpenAPI documents found in the repository. High authority for schemas; medium authority for behaviour.
context-document.md from the Repo Reader. Authoritative for the route inventory (§4.1), data models (§5), and auth model (§6).
The repository source tree. Authoritative for behaviour. Used to verify documented endpoints and to characterise undocumented ones.
When MCP and Swagger both exist: consume both, merge into one output, record conflicts under Discrepancies. Code is the tiebreaker.

When neither MCP nor Swagger is present or sufficient: crawl the codebase. Start from §4.1 of context-document.md and walk routes → controllers → handlers → services → models for every endpoint. Add any endpoints the Repo Reader missed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ OUTPUT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Format: markdown (.md), single file
Path: provided by the orchestrator in output_path — never invent one
Schema: the api-contract.md schema in the Scraper design document
Every required section and sub-heading must appear, even if marked "Not detected"
Every endpoint must include its source provenance and a confidence rating
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ SOURCE STRATEGY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detect sources in this order:

Indicator Treatment ───────────────────────────────── ────────────────────────────────── mcp.json, .mcp/, mcpServers blocks Parse as MCP, treat as primary @mcp.tool / @modelcontextprotocol/sdk Parse as MCP, treat as primary openapi.{yaml,json}, swagger.{yaml,json} Parse as OpenAPI, treat as primary FastAPI / NestJS / Springdoc / drf-yasg Use built spec if present; decorators otherwise treat decorators as inline Swagger None of the above Full crawl from context-document §4.1

Even when documented sources are complete, run a verification crawl: confirm every documented endpoint has a matching handler in the code. Flag stale docs under Endpoints Not Characterised.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ PER-ENDPOINT SPECIFICATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each endpoint, populate every sub-heading defined in the schema:

Summary, Purpose (detailed), Source, Source type
Auth required, Roles allowed, Rate limit, Idempotent
Path parameters, Query parameters, Headers
Request body (content-type, schema, example)
Responses table with one row per status code
Per-status response schema and example
Side effects (DB writes, events, external calls — drawn from handler code)
Notes for testers (quirks, ordering dependencies, setup requirements)
Confidence (schema confidence, behaviour confidence, rationale)
Confidence rules: - high: schema and behaviour both verified against handler code - medium: schema from docs, behaviour partially verified, OR schema from code with ambiguity - low: significant gaps; Test Writer should treat with caution

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ CONFLICT RESOLUTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When MCP, Swagger, and the codebase disagree:

Field Authority ────────────────── ────────────────────────── Auth requirement / roles Code wins Request required fields Code wins Response field set Code wins Field descriptions Docs win (more human-readable) Examples Docs win when present, otherwise synthesise from schema defaults Status codes Union; code wins on body shape per status Side effects Code only (docs rarely capture these)

Every conflict goes into Discrepancies & Open Questions with the resolution taken.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ WHEN TO STOP AND ASK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Condition Question to ask ──────────────────────────────── ──────────────────────────────────────── No context-document.md provided "Repo Reader output is required. Please confirm the path to context-document.md." context-document.md missing §4.1 "Context document has no route inventory. Run the Repo Reader first or confirm crawl-only mode is acceptable." Conflicting sources, no handler "Sources disagree on [endpoint] and the handler cannot be located. Confirm which source takes precedence or remove the endpoint from scope." Repo is huge, budget exceeded "Source-token budget exceeded at [endpoint count] endpoints. Continue with summary-only mode for remaining files, or raise the budget?" Swagger references external $ref "Swagger uses an external $ref to [url]. Fetch it (network), inline a placeholder, or treat the schema as Not detected?" (Default: placeholder; never make network calls without confirmation.) Endpoint discovered with no clear "Endpoint [METHOD /path] discovered but behaviour the handler delegates to code outside the repo (vendored binary, external service). Mark as Not Characterised?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ WHAT NOT TO DO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do not write tests; that is the BE Test Writer's job
Do not run any commands against the target repo or its dependencies
Do not make network calls to fetch external $refs without explicit confirmation
Do not invent endpoints, fields, or examples — mark gaps as "Not detected"
Do not silently drop documented endpoints whose handlers cannot be found — list them under Endpoints Not Characterised with the reason
Do not collapse the Discrepancies section if there were conflicts; surface them
Do not modify, create, or delete any file in the target repository
Failure Modes & Handling Scenario Handling context-document.md missing or malformed Fail immediately; instruct Orchestrator to re-run Repo Reader Repo has no detectable HTTP endpoints Produce minimal output: global sections + empty Endpoints + explanation in Overview; mark source_strategy: crawl_only, confidence_summary: 0/0/0 MCP descriptor is malformed Skip the file, log the parse error, continue with other sources; record in Discrepancies Swagger has external $ref that can't be resolved Inline a placeholder schema, mark field-level confidence as low, list in Discrepancies Documented endpoint has no matching handler List under Endpoints Not Characterised with reason "Stale documentation — no handler found" Handler exists but body is unreadable (minified, generated) List endpoint with what is known from docs; mark behaviour confidence: low; note in Notes for testers Crawl budget exceeded Demote already-documented endpoints to summary-only LLM reads; never demote endpoints relying solely on the crawl LLM returns malformed endpoint block Retry once with stricter prompt; if still bad, list endpoint under Endpoints Not Characterised Schema validator fails after retry Emit what we have, log all violations, flag downstream agents; never silently ship malformed output Endpoint duplication across MCP and Swagger (same method+path) Merge per §5.5 rules; record source_type: mcp+swagger Path normalisation collision (e.g., /users/{id} vs /users/:id) Normalise to OpenAPI style ({id}); if collision is genuine (two different endpoints), keep both and flag in Discrepancies The agent's commitment: always produce api-contract.md, even degraded. Gaps are explicit, never implicit. Every endpoint either has a full spec or appears under Endpoints Not Characterised — none are silently dropped.

Performance & Cost Considerations Lever Default Tuneable Pass 3 batch size 6 files per LLM call Config Pass 3 total budget 250K tokens of source --max-crawl-tokens Pass 5 batch size 10 endpoints per synthesis call Config Verification crawl depth Handler + immediate middleware --verify-depth Synthesis model Claude Sonnet 4 --scraper-model Documented-source-only mode Off by default --skip-crawl (risky — disables verification) Cost ceiling for a typical mid-sized API (~80 endpoints, mix of documented and undocumented): - Pass 3: ~15 batched LLM calls @ ~18K input tokens each ≈ 270K input tokens - Pass 5: ~8 synthesis calls @ ~25K input + ~6K output - Estimated total: ~470K input / ~50K output Sonnet tokens per run

The Scraper is the second-most expensive agent after the Repo Reader. The source-priority strategy (use docs first, crawl second) exists specifically to keep this bounded — repos with good Swagger/MCP cost a fraction of crawl-only repos.

Security Considerations Concern Mitigation Reading sensitive endpoint payloads (real PII in examples) Examples are extracted from Swagger/MCP example fields only, or synthesised from schema. Code-level extraction never reads test fixtures containing real data — only schema declarations External $ref resolution Never performed automatically. The agent asks before making any network call Malicious repo content Read-only file access. No eval, no exec, no script execution. Same posture as Repo Reader Credentials in Swagger If Swagger contains hardcoded tokens (anti-pattern but seen), they are stripped from any output and the path is logged. The Scraper never includes credentials in api-contract.md regardless of source Endpoint paths revealing internal infrastructure Treated as part of the contract; included in output. If the user needs redaction, they configure it at the Orchestrator level — outside the Scraper's scope
Definition of Done The Scraper's task is complete when all of the following hold:
api-contract.md exists at the configured output path Schema validator returns PASS (or, after one retry, PASS_WITH_WARNINGS logged) Every endpoint in context-document.md §4.1 either has a full spec or appears under Endpoints Not Characterised with a reason endpoint_count in frontmatter matches the rendered endpoint blocks sources_consumed lists every MCP and Swagger file the agent read, plus the crawled files Shared state has api_contract_path, api_contract_source_strategy, api_endpoint_count, api_endpoints_low_confidence, and api_discrepancies populated The Orchestrator has been signalled that the next agents (BE Test Writer, FE Test Writer) can begin 13. Open Questions for the Team Things flagged for the wider TestForge team to confirm before implementation:

WebSocket / SSE endpoints — In scope for the Scraper, or HTTP-only? Default proposal: HTTP-only for v1; flag any WebSocket endpoints in Endpoints Not Characterised with reason "Real-time endpoint — out of v1 scope". GraphQL APIs — A GraphQL endpoint is technically one HTTP route, but the contract is the schema. Default proposal: detect GraphQL, generate a single entry under /graphql with the SDL embedded in the request body section, and flag for the Test Writers to handle specially. External API consumption — If the target app calls third-party APIs (Stripe, SendGrid), do we document those too? Default proposal: no — only document endpoints the target app exposes. External calls appear in Side effects on individual endpoints. Versioned APIs — If both /v1/users and /v2/users exist, do we group them under one resource? Default proposal: separate resources per version (Resource: Users (v1), Resource: Users (v2)) so the Test Writers can target each independently. Generated Swagger from running app — Some apps only emit Swagger when running (e.g., /docs endpoint). Default proposal: we do not start the app. Only documents present in the repo at rest are consumed. If the user wants live-Swagger ingestion, that's a future enhancement. Caching across runs — Same as Repo Reader Open Question #6: if the same commit_sha was scraped before, can we reuse api-contract.md? Default proposal: opt-in via --use-cache, same flag as Repo Reader. Schema dereferencing depth — When Swagger nests $refs deeply, do we inline everything or keep the references? Default proposal: dereference up to 5 levels for readability in the output; deeper references are inlined as { "$ref": "..." } with a note. 14. Handoff to Downstream Agents The Scraper's output is consumed as follows:

Downstream agent Consumes How BE Test Writer api-contract.md in full Parses endpoint blocks by heading pattern. Uses Request body, Responses, Auth, and Roles to generate Playwright tests. Uses Confidence to decide where to add expect.soft vs hard expects, and which endpoints to flag for human review FE Test Writer api-contract.md global Auth section + endpoints called by frontend pages Cross-references context-document.md §4.2 (frontend routes) with api-contract.md to understand what API calls each page makes Reviewer Discrepancies & Open Questions when triaging failures Uses recorded conflicts to judge whether a failing test indicates an app bug, a doc bug, or a test bug The handoff is the reason the Confidence and Discrepancies sections of api-contract.md matter: they tell the Test Writers which endpoints to trust and which to write with extra defensive assertions. The Reviewer uses the same signals when explaining failures.