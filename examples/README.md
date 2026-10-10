# reqmap

**A Git-shared product requirement memory for Codex** — know **what features exist**, **why they were designed that way**, and **what a requirement change might affect**.

`reqmap` is intentionally *not* an implementation planner, code dependency graph, architecture knowledge base, or chat-memory dump.

## What it does

- **Feature catalog:** stable `REQ-0001` IDs, descriptions, business rules, and user-confirmed lifecycle status.
- **Decision rationale and evolution:** the why behind each feature, revision history with before/after snapshots and reasons.
- **Relationship discovery:** Codex examines multiple requirements, finds dependencies, overlaps and conflicts, and records proposed relationships with explanations. A transparent keyword-based `suggest` command narrows candidates, but does not pretend to make semantic judgments.
- **Change impact:** reports transitive impact via **confirmed business dependencies** and separately lists potential impacts from weaker or unconfirmed relationships.
- **Status approval:** a feature is not marked `done` just because Codex wrote code. Codex asks you after development; the CLI demands your explicit statement before changing any status.
- **Cross-session sharing:** `.reqmap/` and `AGENTS.md` live in the project repo. No server, embeddings, third-party APIs, or database required. All interface text supports Chinese/English.

## Install (Codex)

```bash
git clone https://github.com/YOUR_NAME/reqmap.git
mkdir -p ~/.codex/skills
cp -R reqmap ~/.codex/skills/reqmap
```

Or download/unzip this project, then copy it to `~/.codex/skills/reqmap`. Restart Codex or start a new session to discover `$reqmap`. The Skill's Python CLI requires Python 3.9+ and uses only the standard library.

**The repository URL above is a placeholder until the repository is published.**

## Create a requirement memory for your project

From **your product's project directory**:

```bash
python3 ~/.codex/skills/reqmap/scripts/reqmap.py init --name "数字商品平台" --description "创作者入驻并销售数字商品的 Marketplace"
```

This creates:

```text
my-product/
├── AGENTS.md                  # adds a small, idempotent reqmap instruction block
└── .reqmap/
    ├── catalog.json           # one canonical source of truth
    ├── product.md             # product positioning, shared business principles
    ├── INDEX.md               # generated, fast reading entry point
    ├── features/              # generated readable requirement pages
    └── history.jsonl          # append-only change log
```

Commit both `AGENTS.md` and `.reqmap/` to Git. Future sessions read the index on feature-related tasks and load requirement pages only as needed. Existing `AGENTS.md` text remains intact.

## Using `$reqmap` in Codex

Examples of what to ask Codex:

```text
$reqmap 根据以下几个需求初始化项目需求记忆，并判断它们是否互相关联：...
$reqmap 当前已经有哪些功能？分别处于什么状态？
$reqmap 为什么当初要求创作者自己定价？
$reqmap 现在增加优惠券，可能影响哪些已有需求？
$reqmap 把 REQ-0002 的退款规则改为...，记录调整原因。
$reqmap 查看 REQ-0002 的演进历史。
```

When an implementation task involving tracked features ends, Codex should ask about progress. It does *not* auto-set `done`; you can reply "REQ-0002 待验收" or "REQ-0002 验收通过，标记已完成".

## CLI examples

Use `--root /path/to/project` before the subcommand when not running in the project root.

```bash
REQMAP="python3 ~/.codex/skills/reqmap/scripts/reqmap.py"

$REQMAP add --title "微信登录" --summary "用户通过微信身份登录商城" \
  --why "降低首次购买的登录门槛" \
  --rule "账号需要绑定唯一的微信身份"

$REQMAP add --title "商品购买" --summary "用户支付后获得购买商品的访问权限" \
  --why "让消费者获得数字商品，同时形成创作者收入" \
  --rule "支付成功后交付商品访问权限"

$REQMAP suggest --title "微信登录购买" --summary "用户在商城登录后购买商品"

# A business dependency: purchase depends on login; AI proposes it, user confirms it.
$REQMAP link --from REQ-0002 --to REQ-0001 --type depends_on \
  --reason "购买流程要求先建立用户身份" --confidence high
$REQMAP review-link --from REQ-0002 --to REQ-0001 --type depends_on \
  --to-state confirmed --user-confirmation "确认购买依赖登录"

# Which requirements are affected if we change login?
$REQMAP impact REQ-0001
$REQMAP list
$REQMAP show REQ-0002

# Product requirement changes must record why they changed.
$REQMAP revise REQ-0002 --summary "支付后立即获得数字商品的可用权限" \
  --reason "细化交付时机的产品要求"
$REQMAP history REQ-0002

# Only after the user replies with a status confirmation:
$REQMAP status REQ-0002 --to pending_acceptance --user-confirmation "商品购买功能已开发，先待验收"
$REQMAP check
```

## Requirement lifecycle

| State | Meaning | Who sets it |
|---|---|---|
| `defined` | Captured as a product requirement | On creation |
| `in_progress` | User confirms feature development is underway | User approval |
| `pending_acceptance` | User confirms feature is ready for acceptance | User approval |
| `done` | User explicitly confirms it is accepted/complete | User approval |
| `deprecated` | User explicitly deprecates it | User approval |

`status` requires `--user-confirmation` and writes that statement into the audit log. The CLI enforces the *presence* of confirmation; the agent must ensure it is genuinely from the user. No automatic implementation verification is claimed.

## How impact analysis works

A recorded relationship can be `depends_on`, `overlaps`, `conflicts_with`, or `related_to`. Each has a reason, confidence and review status (`proposed`, `confirmed`, `rejected`). For example, `REQ-0002 depends_on REQ-0001` means changing login (REQ-0001) may affect purchase (REQ-0002).

`impact REQ-0001` traverses **only confirmed `depends_on`** dependencies to show downstream affected capabilities. Non-dependency relationships and proposed links appear as **possible impacts** but are never presented as verified transitive dependencies. An unrecorded link is unknown, not "independent". The agent must still use business reasoning to spot important new relationships.

## Scope and boundaries

**In scope:** product feature inventory, why/rules, product requirement revisions, feature relations, user-confirmed status. **Out of scope:** architecture, APIs, implementation details, task checklists, roadmaps, unsanctioned next steps, secrets or personal information.

Limitations: there is no automatic process-level Codex hook; the Skill and injected `AGENTS.md` govern behavior by instructions, not guaranteed event delivery. A crashed session can't guarantee a final history update. When two developers write to the same working tree simultaneously, the JSON catalog isn't a concurrent database; use normal Git branches and review merges. Regenerate derived Markdown with `sync` after resolving conflicts, then run `check`.

## Contributing / testing

```bash
python3 -m unittest discover -s tests -v
python3 scripts/reqmap.py --help
```

License: MIT.
