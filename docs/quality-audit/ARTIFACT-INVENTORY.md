# Artifact inventory before commit

Inventory scope: all task-generated files located in the preserved StoreScout audit workspaces, the current repository audit/evaluation artifacts, and the saved StoreScout deliverables. The CSV contains one row per located source file (raw scratch observations individually listed), plus two excluded runtime/checkout directories. No claim is made about deleted or inaccessible historical files. This is an artifact inventory, not a repeated source audit or benchmark.

The three requested deliverables are copied unchanged. The ZIP is retained as the frozen portable archive; directly useful evidence is unpacked. Two replay utilities have checkout-path-only adaptations recorded separately from original archive hashes. Full feature/Playbook/prospect sections are extracted for navigation, with source provenance, without re-auditing them.

| Classification | Located source entries | Disposition |
|---|---:|---|
| include in repository | 65 | Keep/copy current useful material or retain existing Git reference. |
| obsolete/duplicate | 32 | Do not add redundant copies or obsolete report generators. |
| temporary/scratch | 919 | Leave raw observations, failed attempts, assembly utilities and runtimes outside Git. |
| sensitive/do not commit | 2 | Leave unredacted owner account records outside Git; include a sanitized derivative only. |

| Artifact group | Classification / selected destination |
|---|---|
| Current discovery priorities, results, ZIP | Include, exact requested names under `real-world/` |
| Current implementation specs and measured resume | Include, preserve the already-pending changes under `real-world/` |
| Original 25-business panel, protocol and source manifest | Include; original panel/hash unchanged, historical null manifest explicitly labelled |
| Full feature audit and route/coverage maps | Include, `product/FULL-FEATURE-AND-ACTIONABILITY-AUDIT.md` plus existing JSON maps |
| Playbook grounding/actionability and actual catalog evidence | Include, `product/` and `product/evidence/` |
| Earlier synthetic discovery fixtures and measurements | Include as provenance mirrors under `discovery-synthetic/`; originals in `tests/evaluations/` unchanged |
| Complete state/customer plan | Original: sensitive/do not commit; sanitized full derivative under `resume/` |
| Restoration/account investigation | Include sanitized operational summary under `restoration/`; exclude invoice amounts/history, private account identifiers and support transcript |
| Current 20-prospect ranking and ten outreach drafts | Include public-source research under `prospects/`; no sending authorized |
| Earlier sales kit | Include with historical precedence banner; unique posts/experiment assets retained, newer rankings prevail |
| Initial readiness review and offline reproductions | Include under `source-audit/`, labelled pre-repair baseline |
| Reconciled public index snapshot and real PostgreSQL captures | Include unpacked under `real-world/evidence/`; allowlisted public business/catalog fields only |
| Dated public checks, labels, every case trace, health sample, metrics | Include compact evidence; preserve unknowns and single-reviewer limitations |
| Duplicate snapshot pages, text renderings, old report copies/generators | Obsolete/duplicate; keep outside Git |
| Raw scraped bodies, environmental DNS failures, caches/runtime/old checkout | Temporary/scratch; compact facts and original artifact hashes provide the handoff evidence |
| Provider keys, customer/private data or payment links | Sensitive/do not commit; none found in selected exports or credentials scan; no environment files copied |

The per-file CSV includes exact source and destination paths, reasons and source SHA256. Public professional contact addresses in prospect research were explicitly sourced; they are not customer/account exports. Existing source code, tests, deployment files and operational docs remain unchanged.

This inventory and `PROPOSED-FILE-TREE.md` are presented before the authorized local documentation commit. No push or deployment is part of this task.
