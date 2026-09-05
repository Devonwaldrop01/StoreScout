# StoreScout audit and Codex handoff

Current application baseline: `ff555bb2842a05f55dcc83403bfef80bc7eb17cf`, preserved under local documentation checkpoint `11c1205`. The new handoff is documentation/evidence only. Do not push, deploy, modify production data/configuration, send outreach, or pay without the owner’s explicit authorization.

**Start here:** [measured Codex priorities](real-world/StoreScout-Codex-Discovery-Priorities.md), [real-index results](real-world/StoreScout-Real-Index-and-Discovery-Results.md), [implementation specifications](real-world/IMPLEMENTATION-SPECS.md), then [measured resume](real-world/MEASURED-RESUME.md). Discovery remains **Weak**: core P@5 28.3%, three-useful coverage 7/24. These are original local-endpoint replays on actual production-index captures, not a live production/paid-AI benchmark or independent blind merchant validation.

| Folder/file | Contents and precedence |
|---|---|
| `ARTIFACT-INVENTORY.md`, `.csv` | All located task artifacts classified, source paths, hashes, inclusion/redaction reasons |
| `PROPOSED-FILE-TREE.md` | Exact file tree presented before committing |
| `real-world/` | Original 25-business panel, saved evaluation protocol, measured results, priorities, specs and resume |
| `real-world/evidence/` | Directly readable 38,221-row public index snapshot, PostgreSQL captures, all 50 runs, 331 placement labels, health sample, metrics and reproduction utilities |
| `real-world/StoreScout-Discovery-Evidence.zip` | Original unchanged measured archive; convenient portable checkpoint. Unpacked evidence is Codex’s direct working input |
| `product/` | Complete 58-feature/actionability audit, Playbook architecture, core product logic and dated public catalog sample |
| `discovery-synthetic/` | Earlier synthetic baseline/after/wording evidence; never substitute these numbers for real discovery quality |
| `source-audit/` | Initial readiness review, offline reproductions and former quality-audit README; historical findings may already be fixed |
| `resume/` | Current full state/customer plan with private account billing/support text removed |
| `restoration/` | Sanitized operational findings and approval gates; no invoice/account/payment records |
| `prospects/` | Public research, 20-prospect ranking, ten opening drafts and older sales assets; drafts are unsent |
| `feature-route-inventory.json`, `real-world/feature-audit-coverage.json` | Existing source coverage: 137 handlers, 21 pages, 32 jobs, 58 feature groups; not live certification |

Historical blocker/null fields in `baseline-manifest.json`, `replay-plan.json` and archived report sections record earlier preparation. The completed `real-world/evidence/measured-manifest.json`, measured results and priorities supersede them. The original reference ground truth and source fingerprints remain unchanged.

Private billing/account/support records, raw scraped page bodies, failed environmental DNS attempts, duplicate page exports, old report generators, environments and caches are excluded. Public business contact routes in prospect research are sourced professional contacts, not private customer records. No live credentials were found in the selected evidence. The index snapshot exports public catalog/business fields only.

Reproduction instructions are in [real-world/evidence/README.md](real-world/evidence/README.md). Frozen observations and labels support recomputation without database access. Running public checks again creates new evidence and is not part of this handoff. Existing application tests and evaluations were not rerun.
