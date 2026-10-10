# reqmap

**面向 Codex 的项目级需求记忆 Skill**。帮助 Codex 跨会话回答三个问题：**项目有哪些功能？为什么这样设计？修改一个需求会影响什么？**

`reqmap` 只关注产品需求，不是开发任务规划器、代码依赖分析工具、技术架构知识库，也不会把聊天记录全部保存为记忆。

## 核心能力

- **功能清单**：为需求分配稳定的 `REQ-0001` 编号，记录功能描述、业务规则及经用户确认的状态。
- **设计原因与演进历史**：保存「为什么这样设计」，需求修改时记录修改前后内容和变更原因。
- **需求关系发现**：Codex 分析多个需求，识别依赖、重叠、冲突等关系，并解释判断依据。CLI 的 `suggest` 命令只按关键词筛选候选需求，不假装具备 AI 语义推理能力。
- **变更影响分析**：沿已确认的业务依赖分析间接影响，并单独列出尚未确认或较弱关联带来的潜在影响。
- **进度确认**：Codex 完成开发后应询问用户，不能因为代码写完就自动将需求标记为 `done`。CLI 修改状态时必须提供用户明确确认的原话。
- **跨会话共享**：通过项目仓库中的 `.reqmap/` 和 `AGENTS.md` 持久保存；不需要服务器、向量数据库、第三方 API 或独立数据库，支持中英文内容。

## 安装到 Codex

```bash
git clone https://github.com/openpika/reqmap.git
mkdir -p ~/.codex/skills
cp -R reqmap ~/.codex/skills/reqmap
```

也可以下载并解压仓库，将文件夹复制到 `~/.codex/skills/reqmap`。

重新启动 Codex 或新建会话后，即可使用 `$reqmap`。内置 CLI 要求 **Python 3.9+**，仅依赖 Python 标准库。


### 已安装用户如何升级

如果之前已经安装过 `reqmap`，先更新 Skill，然后到**已初始化的产品项目根目录**刷新 `AGENTS.md` 规则：

```bash
git -C ~/.codex/skills/reqmap pull --ff-only
python3 ~/.codex/skills/reqmap/scripts/reqmap.py install-agents
```

`install-agents` 只更新 `AGENTS.md` 内的 reqmap 规则区块，不会重建项目、覆盖原有需求或删除其他项目指令。若最初使用 ZIP 安装且没有 Git 仓库，请重新复制新版 Skill 文件夹，再运行第二条命令。重新开启 Codex 会话，以确保加载新版 Skill。

## 初始化项目需求记忆

在**你的产品项目根目录**执行：

```bash
python3 ~/.codex/skills/reqmap/scripts/reqmap.py init --name "数字商品平台" --description "创作者入驻并销售数字商品的 Marketplace"
```

初始化后生成：

```text
my-product/
├── AGENTS.md                  # 增加 reqmap 说明，不覆盖原有内容
└── .reqmap/
    ├── catalog.json           # 需求数据的唯一事实来源
    ├── product.md             # 产品定位和通用业务原则
    ├── INDEX.md               # 自动生成的需求索引，便于快速读取
    ├── features/              # 自动生成、方便阅读的需求文档
    └── history.jsonl          # 只追加的需求变更历史
```

将 `AGENTS.md` 和 `.reqmap/` 一起提交到 Git。后续 Codex 会话遇到需求相关任务时，先读取索引，再按需查看具体需求，避免每次加载全部内容。已有 `AGENTS.md` 不会被覆盖。

## 一次激活，当前会话持续跟踪

在项目目录的当前 Codex 会话里，只需要**首次调用一次** `$reqmap`。此后继续用自然语言提出需求、修改规则、开发功能、询问进度或回复验收结论，**无需再次写 `$reqmap`**。

```text
你：$reqmap 初始化这个项目的需求记忆，功能有微信登录、商品购买。

你：增加优惠券功能，看看对已有需求有什么影响。
Codex：分析并登记已明确的新需求，记录可能的关联，说明影响范围。

你：把商品购买改成允许使用优惠券支付。
Codex：自动识别已有 REQ，分析影响并记录需求演进原因。

你：开始开发优惠券功能。
Codex：按正常开发流程实现，并关联已有 REQ。

Codex：本次开发已结束。REQ-0003 的需求进度要更新为哪种状态？
你：先标记为待验收。
Codex：根据你的明确确认更新状态与历史记录。
```

自动跟踪遵循以下边界：

- **自动记录明确需求**：已确定的新增、修改及设计原因会更新到项目记忆，相关关系先以待确认记录；讨论中的想法、假设不擅自入库。
- **自动查询影响**：需求发生变化前主动检查关联需求，区分已确认依赖与潜在影响。
- **进度需用户确认**：即使代码完成或测试通过，也只询问是否更新状态；你确认后自动执行更新，不需要再调用 Skill。
- **只作用于当前项目**：跨会话信息保存在 Git 管理的 `.reqmap/` 与 `AGENTS.md`；切换项目时重新读取对应项目的数据。
- **可以随时暂停**：在会话中明确说「本会话暂停 reqmap 跟踪」，Codex 应停止主动更新。

**实现边界：** 这里的“自动”指 Codex 在会话中遵循 Skill 和 `AGENTS.md` 规则主动调用本地 CLI，不是后台常驻服务或可靠事件钩子。异常退出、上下文被截断或没有执行到对应步骤时，不能保证变更已落盘；必要时使用 `check` 核验。

## 在 Codex 中使用

直接通过 `$reqmap` 描述需求或提问：

```text
$reqmap 根据以下几个需求初始化项目需求记忆，并判断它们是否互相关联：...
当前已经有哪些功能？分别处于什么状态？
为什么当初要求创作者自己定价？
现在增加优惠券，可能影响哪些已有需求？
把 REQ-0002 的退款规则改为...，记录调整原因。
查看 REQ-0002 的演进历史。
```

开发涉及已登记需求的功能后，Codex 应主动询问进度，**不会自行确认「已完成」**。你可以回复「REQ-0002 待验收」或「REQ-0002 验收通过，标记已完成」。

## CLI 使用示例

不在项目根目录执行时，可以在子命令前指定 `--root /path/to/project`。

```bash
REQMAP="python3 ~/.codex/skills/reqmap/scripts/reqmap.py"

# 添加两个需求
$REQMAP add --title "微信登录" --summary "用户通过微信身份登录商城" \
  --why "降低首次购买的登录门槛" \
  --rule "账号需要绑定唯一的微信身份"

$REQMAP add --title "商品购买" --summary "用户支付后获得购买商品的访问权限" \
  --why "让消费者获得数字商品，同时形成创作者收入" \
  --rule "支付成功后交付商品访问权限"

# 为新需求寻找潜在关联
$REQMAP suggest --title "微信登录购买" --summary "用户在商城登录后购买商品"

# 记录业务依赖：购买依赖登录（先提出关系，再由用户确认）
$REQMAP link --from REQ-0002 --to REQ-0001 --type depends_on \
  --reason "购买流程要求先建立用户身份" --confidence high
$REQMAP review-link --from REQ-0002 --to REQ-0001 --type depends_on \
  --to-state confirmed --user-confirmation "确认购买依赖登录"

# 修改登录功能时，哪些需求可能受影响？
$REQMAP impact REQ-0001
$REQMAP list
$REQMAP show REQ-0002

# 修改需求时必须记录原因
$REQMAP revise REQ-0002 --summary "支付后立即获得数字商品的可用权限" \
  --reason "细化交付时机的产品要求"
$REQMAP history REQ-0002

# 只有收到用户的状态确认后，才能执行
$REQMAP status REQ-0002 --to pending_acceptance --user-confirmation "商品购买功能已开发，先待验收"
$REQMAP check
```

## 需求状态

| 状态 | 含义 | 设置条件 |
|---|---|---|
| `defined` | 已定义 | 创建需求时自动设置 |
| `in_progress` | 开发中 | 用户确认正在开发 |
| `pending_acceptance` | 待验收 | 用户确认开发已完成、进入验收 |
| `done` | 已完成 | 用户明确确认验收通过或需求完成 |
| `deprecated` | 已废弃 | 用户明确确认废弃 |

`status` 命令强制要求 `--user-confirmation`，并将确认内容写入审计历史。**CLI 只能检查确认参数是否存在；Codex 必须保证这段确认确实来自用户。** 工具不会声称已经自动验证功能实现情况。

## 需求关联与影响分析

支持以下关系：

| 关系类型 | 含义 |
|---|---|
| `depends_on` | 依赖 |
| `overlaps` | 功能或业务范围重叠 |
| `conflicts_with` | 存在冲突 |
| `related_to` | 一般关联 |

每条关系都记录原因、置信度，以及审核状态（`proposed` 待确认、`confirmed` 已确认、`rejected` 已否决）。

例如，`REQ-0002 depends_on REQ-0001` 表示「商品购买依赖微信登录」，因此修改登录需求时，购买流程可能受到影响。

执行 `impact REQ-0001` 时：

1. 仅沿 **已确认的 `depends_on` 关系**追踪下游依赖。
2. 对尚未确认的关系及其他关联，只列为**潜在影响**，不当作确定的传递依赖。
3. 没有登记关联，不代表两个需求一定独立。Codex 仍需结合业务语义继续识别遗漏的联系。

## 使用边界

**负责：** 功能清单、业务规则、设计原因、需求变更历史、需求关联、影响分析和用户确认的进度。

**不负责：** 技术架构、API 或代码实现细节、任务清单、路线图、未经要求的下一步计划，以及密钥或个人敏感信息。

当前限制：

- Codex 没有由本 Skill 提供的可靠进程级事件钩子；自动读取和更新依赖 Skill 与 `AGENTS.md` 的行为约束，不保证每个事件都被捕获。
- 会话意外中断时，无法保证最后一次需求变更已经写入。
- `catalog.json` 不是并发数据库。多人或多个会话同时写入时，应通过 Git 分支管理并检查合并冲突。
- 解决冲突后运行 `sync` 重新生成 Markdown 文档，再运行 `check` 检查数据一致性。

## 开发与测试

```bash
python3 -m unittest discover -s tests -v
python3 scripts/reqmap.py --help
```

**开源协议：** MIT。
