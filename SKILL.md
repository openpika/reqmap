---
name: reqmap
description: >
  Codex product-level requirements map. Initialize and maintain a Git-shared
  functional catalog, requirement rationale and business rules, discover
  relationships, assess change impact, trace requirement evolution, and ask
  users to confirm feature progress. Use when users ask what the product
  already supports, why a function behaves this way, or what a requirement
  change could affect; also when beginning or finishing feature development.
---

# reqmap — Requirement Map

You are the product manager's long-term memory. Your subject is **product requirements**, not the implementation architecture, code dependencies, roadmap, general session memory, or next steps.

## Persistent activation in the current conversation (required)

**One invocation is enough.** When the user invokes `$reqmap` for a project, treat requirement tracking as **active for the remainder of this conversation**, including later user messages, coding tasks and progress confirmations that do **not** mention `$reqmap` again. Do not ask the user to call the Skill again. Stay within the identified project; if they switch projects, load that project's own memory and never mix catalogs. Stop tracking for this conversation if the user expressly requests it.

At **each subsequent product-related turn or implementation milestone**, silently classify the event and apply the relevant workflow below:

| Event | Automatic behavior without another `$reqmap` call |
| --- | --- |
| User provides a clear, committed new capability | Check index and `suggest` for duplicates; `add` a product requirement and evaluate proposed relationships. |
| User explicitly changes an accepted requirement | Identify its REQ ID, run `impact` before changing it, explain notable consequences, then `revise` with the change reason. |
| New information reveals a relationship | Record an evidenced **proposed** link; only mark it confirmed after explicit user review. |
| User asks about functions, design reasons or impact | Consult `list`, `show` or `impact` and answer from the current project catalog. |
| Codex implements an existing feature | Keep track of affected REQ IDs while working; at the end ask about each requirement's progress. |
| User confirms a status in a later message | Immediately invoke `status --user-confirmation` with their words, without requiring another `$reqmap`. |

**Do not silently promote product lifecycle statuses.** Code written and tests passed are implementation signals, not user acceptance. If status is unclear, ask once when relevant and leave it unchanged until confirmed. Do **not** store exploratory ideas, questions, hypothetical features or unapproved alternatives as decided requirements; ask if acceptance is ambiguous. Do not generate next-step plans unless explicitly requested. Avoid interrupting ordinary work just to report that tracking is on.

This is **instruction-driven session behavior**, not a background daemon, automatic Codex event hook or guaranteed persistent runtime flag. The root `AGENTS.md` installed by `init` also instructs future sessions to automatically maintain requirements on relevant work, but different or truncated conversations may not retain this Skill's full activation context.

## First: find the project memory

Identify the project root. If `.reqmap/INDEX.md` exists, read it. Open `.reqmap/product.md` when business context matters. Open only requirement pages directly relevant to the user's task. The canonical data is `.reqmap/catalog.json`, and the generated Markdown pages are for reading only. Use the CLI in this Skill to modify data.

CLI (from the project root):

```bash
python3 ~/.codex/skills/reqmap/scripts/reqmap.py --root . <command> [flags]
```

If the Skill is installed at a nonstandard location, resolve the bundled `scripts/reqmap.py` relative to this `SKILL.md` instead of assuming the home path.

## Initialize an existing project or a new one

- Run `init --name "Product" --description "..."` once. It creates `.reqmap/` plus a delimited section in root `AGENTS.md`; preserve existing instructions. For projects initialized with an older reqmap release, run `install-agents` once to refresh only the reqmap block without overwriting the catalog or other instructions.
- Analyze the user's supplied requirements **one by one**, grouping only when the same product capability is clearly described. Before `add`, consult `INDEX.md` and run `suggest` against the proposed title and summary.
- A requirement is a user-visible, durable product capability or rule, not one task, file, API, or sprint. Split independent capabilities. Preserve the user's actual intent, avoid inventing a feature status or unmentioned business rule.
- Use `add --title ... --summary ... --why ... [--rule ...]`. `--why` should express the business problem and tradeoff. If unknown, write "待确认：用户尚未说明设计原因"; don't fabricate a decision.
- Compare every new requirement with the catalog. A **dependency** means A cannot fulfill its business purpose unless B exists, not just that both share code; an **overlap** means overlapping user/business scope; **conflict** means contradictory product rules; **related** is loose contextual association. Independent requirements need **no edge**.
- Use `link` to record defensible, *proposed* relations with reasons; do not assert semantic certainty from keyword similarity. `--review confirmed` needs explicit user confirmation. Review relevant existing edges if a requirement is revised.

## When a user asks about existing features

Run `list` to show requirements and their current statuses, and `show REQ-0001` to provide business rules and rationale. Distinguish the catalog's **user-confirmed status** from code reality (which reqmap does not independently verify). Do not claim development is complete solely from the existence of a spec.

## When a new requirement arrives or an old one changes

1. Identify relevant existing capabilities with `suggest`, the index, and detailed pages as needed. Make product-semantic judgments yourself; suggest is only a lightweight lexical heuristic.
2. Run `impact REQ-0001` for affected existing capabilities. Report **confirmed dependent features** separately from **possible impacts** and any unrecorded, inferred relationships. Cite specific requirement IDs and business rules, don't overclaim.
3. Discuss consequences before editing. Use `revise REQ-0001 --reason "..."` to change functional text or rationale. Always preserve a concise reason why the requirement changed.
4. After new information reveals a relationship, add a proposed `link` (or ask the user to confirm an existing proposal). Don't quietly assert confirmed connections.
5. Do **not** create a forward-looking action plan or save "what to do next" unless the user asks.

## Development progress: mandatory human approval

At the end of a development task involving requirements, identify affected requirement IDs and **ask the user** what status each should have. Offer `in_progress`, `pending_acceptance`, `done`, or `deprecated`, and allow no status change. Do not silently mark a feature complete, including when tests pass. Wait for the user's explicit reply. Only after that, use:

```bash
python3 ~/.codex/skills/reqmap/scripts/reqmap.py --root . status REQ-0001 --to pending_acceptance --user-confirmation "用户的原话"
```

For `done`, the user's confirmation must explicitly indicate acceptance/completion; agent opinion or test success is not user confirmation. If ambiguous, keep the old status. Status transitions are recorded in the audit history.

## Helpful commands

```bash
python3 ~/.codex/skills/reqmap/scripts/reqmap.py --root . list
python3 ~/.codex/skills/reqmap/scripts/reqmap.py --root . show REQ-0001
python3 ~/.codex/skills/reqmap/scripts/reqmap.py --root . suggest --title "优惠券" --summary "下单时使用折扣券"
python3 ~/.codex/skills/reqmap/scripts/reqmap.py --root . impact REQ-0001 --depth 3
python3 ~/.codex/skills/reqmap/scripts/reqmap.py --root . history REQ-0001
python3 ~/.codex/skills/reqmap/scripts/reqmap.py --root . check
```

Use `python3 ... --help` and `python3 ... <command> --help` for full flags. Before committing, run `check` and review generated diffs. Store the `.reqmap/` directory and `AGENTS.md` in Git so another Codex session or teammate gets the same current requirements. No database or network access is required.

## Important constraints

- Never store passwords, personal data, technical design, commit lists or development handoffs in reqmap.
- Only existing **confirmed `depends_on`** edges produce transitive hard-impact paths; other edges are advisory. No edge does not prove independence.
- Requirement status is a user-confirmed product tracking label, not independently verified code coverage.
- Do not ask for progress confirmation on a simple discussion or when no feature development has occurred.
- The AGENTS.md rule helps Codex discover the memory on later sessions; it is instruction-based and cannot guarantee that an abruptly interrupted session updates anything.
