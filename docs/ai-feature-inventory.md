# Comicarr AI inventory and Kapowarr-AI port plan

Inspected September 27, 2026. Inventory only: no AI functionality has been ported.
Kapowarr-AI starts from Kapowarr commit `aca5d1a`, including the Pack Inbox,
indexer/client integrations and native import naming.

## Reference and provenance

- Source: https://github.com/frankieramirez/comicarr
- Inspected source revision: `4a7641ffcc3d8369914077a361aa0830718fb41a`.
- Requested image: `ghcr.io/frankieramirez/comicarr:latest`.
- Registry manifest digest observed:
  `sha256:98cbc898a26e77e3d4c258086fb05426ad88a6a5db7fbf7b83883497239b6bd3`.
- The image config has no revision labels. The inventory describes the inspected
  source, not a proven exact source match for that image. Pin the release/source
  correspondence before copying implementation from it.
- Both repositories contain GPLv3 license text. Preserve Comicarr copyright and
  license notices for adapted code and document its source revision.

Source paths below are relative to the Comicarr repository at that revision.

## User-facing features

| Feature | What the source implements | Kapowarr adaptation |
| --- | --- | --- |
| AI provider settings | OpenAI-compatible base URL, model, API key, connection test, timeout, request and daily-token limits, usage/circuit status. `frontend/src/components/settings/AiTab.tsx`, `comicarr/app/ai/client.py`, `service.py`. | Native settings page and backend service; disabled until configured. Verify authenticated model responses, not just endpoint reachability. |
| Filename parsing fallback | Suggests series, issue number, year and volume when ordinary parsing fails; checks suggested series against library. `parsing.py`, caller in `comicarr/filechecker.py`. | Start with explicit Pack Inbox suggestions; validate against real library IDs and use the existing picker/manual-match API. Naming remains Kapowarr's responsibility. |
| Search expansion | Generates alternate search queries and can persist successful alternatives. `search_expansion.py`, caller in `comicarr/search.py`. | Feed candidates through existing indexer search, preferences, matching and repeat suppression. Do not let AI bypass rejection rules. |
| Metadata enrichment | Fills blank ComicInfo.xml **Genre and AgeRating** fields in CBZs after tagging; records history and has per-field revert logic. `enrichment.py`, callers in `comicarr/postprocessor.py`. | Separate optional library-copy operation, with preview/history and atomic archive updates. Never modify torrent originals. This is not a general missing-metadata engine. |
| Metadata reconciliation | Resolves conflicts between pre/post-tagging ComicInfo metadata and records results. `reconciliation.py`, postprocessor callers. | Requires an explicit metadata policy and history model; integrate separately from file identity and naming. |
| Library chat | Streaming answers backed by a fixed catalogue of parameterized library queries. `chat.py`, `query_patterns.py`, `router.py`. | Map allowed queries to Kapowarr volumes/issues/files. No model-generated SQL execution. |
| Persistent chat and images | Stored threads/messages, image attachments and vision-model error handling. `chat_service.py`, `chat_store.py`, `chat_images.py`. | Native chat UI, authenticated storage and bounded uploads; vision depends on the chosen model. |
| Confirmed chat actions | Proposes adding series or marking issues Wanted/Skipped; previews and executes after explicit confirmation with persisted action state. `actions.py`, `router.py`. | Adapt to Kapowarr add-volume, monitoring and search services; Comicarr statuses do not map directly. Preserve uncertain-action replay protection. |
| Series recommendations | Collection-based recommendations, provider resolution, exclusion of tracked titles, caching and refresh. `recommendations.py`, weekly update caller and AI routes. | Read-only recommendations first, with normal Add Volume selection. |
| Weekly pull suggestions | Suggestions based on collection patterns and weekly release data. `pull_list.py`, `comicarr/weeklypull.py`. | Needs an appropriate weekly release data source; GetComics pack subscriptions are not an equivalent catalogue. |
| Story arcs / reading orders | Generates ordered issues, enriches through providers, maps to library and saves arcs. `story_arcs.py`, `comicarr/app/storyarcs/router.py`. | Requires a reading-order model, persistence and UI in Kapowarr, not just an AI endpoint. |
| Activity and usage | Feature activity, success/error details, latency and usage reporting. `service.py`, activity endpoint and frontend activity drawer. | Native diagnostics with credential redaction and bounded retention. |

Chat's query catalogue includes series search, completion percentages, gaps,
issue status, publisher, year, series issues, recent additions, download history
and incomplete story arcs. Each needs a Kapowarr-specific query and response shape.
An `InsightsResponse` schema and dashboard insight component also exist; a separate
AI insights generation backend was not found during this inventory, so this is
not counted as another functioning feature.

## Shared infrastructure and compatibility findings

Comicarr uses FastAPI, SQLAlchemy, React and Python 3.10+. Kapowarr's Flask,
SQLite access, templates/JavaScript and Python compatibility must remain the host
architecture. Port domain behavior and tests; do not transplant Comicarr's app,
database, postprocessor or frontend framework.

Shared AI modules provide structured response validation, input sanitization,
request/token accounting, a circuit breaker and sync/async clients. They depend
on Comicarr's runtime/configuration and activity tables, so even these need adapters.
Network calls must run outside database write transactions.

Two source inconsistencies should not be carried into the port:

- Settings say the API key may be omitted, but the client factory and connection
  test require one. Support local keyless endpoints intentionally and test them.
- HTTP-localhost checks include 10.x and 192.168.x addresses but omit private
  172.16/12 and most container hostnames. Define endpoint validation explicitly
  rather than copying that string-prefix check.

## Port order

1. Provider settings, connection test, bounded requests, validated responses and
   activity reporting, with fixture tests and no library writes.
2. Pack Inbox filename/match suggestions using existing review and import APIs.
3. Read-only library chat and recommendations; then persisted threads/images.
4. Search-query expansion with existing matching and duplicate checks.
5. Confirmed chat actions through native Kapowarr services.
6. Optional metadata enrichment/reconciliation on library copies.
7. Reading orders and weekly suggestions after their supporting data models exist.

Throughout: retain Kapowarr Rename Downloaded Files and naming formats, verified
copies, issue bindings, owned-file exclusion and seeding-safe source handling.
AI proposes identities or actions; it does not invent destination paths or replace
Kapowarr's import pipeline.

## Fork status

The separate local repository is `/home/andrew/Kapowarr-AI`, branch
`feature/comicarr-ai`. Its `kapowarr` remote points to the existing parent fork.
No new GitHub repository or container image has been published. Before publishing,
configure a dedicated Kapowarr-AI remote and review inherited workflows: container
publishing currently targets the parent's `ghcr.io/hackthecatboy/kapowarr` image.
Use a separate image, container configuration and test database for this fork.
