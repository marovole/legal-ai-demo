# 北大法宝 MCP 取数附录

> **本文件是全仓取数纪律的单一事实源。** 交付型与工具型 Skill 共用本文；工具卡仍在门户清单（`tier: tool`），参数以本文为准。
>
> **单独导入**：四个 `pkulaw-mcp-*` 工具目录内各有一份 `references/pkulaw-mcp.md` 副本（由 `scripts/build-guardrails.ps1` 同步）。改真源后请重跑脚本，勿只改副本。
>
> **两条铁律**：
> 1. **能力是契约，工具名/参数名是快照**——实际调用一律以本会话 `tools/list` / `inputSchema` 为准。
> 2. **先检索、后结论**——未拿到工具返回前，禁止写出任何具体法规名、条号、案号、法院名、裁判要点或引用结论。

---

## 一、运行时自愈三原则

1. **改名**：启动先读 `tools/list`，按用途匹配实际工具名。个别客户端把 `.` 显示为 `_`，以实际暴露名调用。
2. **新增**：`tools/list` 出现未列出的新工具，读 `description` 后按需使用。
3. **参数被拒**：报 `Unexpected keyword argument` 或校验错误时，**去掉该筛选、把条件并入主检索文本**重试，**绝不因此改为凭记忆作答**。

---

## 二、能力一览（用途 ↔ serverId ↔ 工具快照）

| 用途 | serverId | 工具（快照） | 主参数（快照） |
|------|----------|--------------|----------------|
| 法规·语义检索 | `law-semantic` | `search_article` | `text`（**不是 `query`**） |
| 法规·精确取条（法名+中文条号） | `law-semantic` | `get_article` | `title` + `number`（中文条号如「第二条」） |
| 法规·关键词列表 | `law-keyword` | `get_law_list` | `title` / `fulltext`（至少一个） |
| 法条·按条号精确点查 | `fatiao` | `get_law_item_content` | `title` + `tiao_num`（数字如 `2`、`2.1`） |
| 案例·语义检索 | `case-semantic` | `search_case` | `text` |
| 案例·关键词/深度 | `case-keyword` | `get_case_list` | `title` / `fulltext`（至少一个） |
| 法条识别 | `law-recognition` | `law_recognition` | 以 tools/list 为准 |
| 案号识别 | `case-number` | `anhao_recognition` | 以 tools/list 为准 |
| 引用核验 | `citation-validator` | `adjust_provisions` | 以 tools/list 为准 |
| 法宝超链 | `doc-link` | `get_linked_content` | 以 tools/list 为准 |

> **精确取条两条路径别混**：`fatiao` 用数字 `tiao_num`；`law-semantic.get_article` 用中文 `number`。按已订阅服务二选一。

---

## 三、分服务要点

### 法规·语义 `search_article`
- 主参 **`text`**；`lib`/`timeliness` 为**单字符串**；日期 **ISO**（`2024-01-01`）；`size` 1–20。
- 有结果=裸数组；空结果=`{"result":[]}`。
- **`issue_department` 精确匹配**：「全国人大常委会」须用此简称，全称会 0 命中。拿不准则并入 `text`。

### 法规·关键词 `get_law_list`
- `title`/`fulltext` 至少一个；`timeliness`/`effectiveness` 为**数组**；日期用**点号**（`2024.1.1`）。
- 返回 `{Message,Data,Total}`；**`Total`=全库命中总数，不是本次条数**——禁止说「共找到 N 条」。

### 案例·语义 `search_case`
- 主参 `text`；法院用 `courthouse_name`/`courthouse_province`；日期 ISO。
- 轻量字段：`ascertain` / `identified` / `referee_result`。

### 案例·关键词 `get_case_list`
- 筛选参数名与语义路径**完全不同**，混用必拒。
- `caseGrade` 为数组；日期点号字段 `start/endLastInstanceDate`。
- 研判五件套：`Ascertain` → `ControversialFocus` → `Identified` → `RefereeBasis` → `RefereeResult`。
- **权威分层**：先 `caseGrade: ["指导性案例","公报案例"]` → 再放宽；勿把「指导性案例」塞进 title/fulltext。

### 法条精确 `get_law_item_content`
- `title` + 数字 `tiao_num`；空字段勿臆造；同名/条号歧义先澄清。

### 识别 / 核验 / 超链
- 独立订阅；结果**只表示与当次返回一致**，不等于实体法结论成立。
- **有链接 ≠ 引用语义正确**；未命中禁止手工拼伪链。

---

## 四、schema drift

过时参数名（会被拒）：`province`、`department`、`type`、`date_start`  
实测正确名：`courthouse_province`、`issue_department`、`doc_type`、`decision_date_start`  

仍被拒 → 去掉筛选并入主文本，不放弃检索。

---

## 五、错误码

| 码 | 处置 |
|----|------|
| `90001` | 积分用尽——不重试 |
| `90002` | 成员用量上限——不重试 |
| `900908` | 无该服务权限——不重试 |
| `401`/`403` | 重新授权后再试 |

未列出的码：如实说暂时不可用，**不编造检索结果**。

---

## 六、检索路由 ↔ 交付物（替代旧工具卡）

| 用户意图 | 不要停在取数 | 应落到的交付物 |
|----------|--------------|----------------|
| 一个法律问题要能发出去的答复 | 法规/案例检索 | `pkulaw-legal-answer` |
| 「这条还有效吗／被谁替」 | 只取原文 | `pkulaw-statute-freshness` |
| 已知条号只要原文 | — | 步骤内调 fatiao／get_article（见上表） |
| 整份文稿签发前过引注 | 超链增强 | `pkulaw-citation-audit` |
| 正式类案检索报告 | 案例列表 | `pkulaw-case-research-report` |
| 庭前胜负开关 | 案例列表 | `pkulaw-pretrial-assessment` |
| 合同条款怎么改 | 法规检索 | `pkulaw-contract-review` |

**律师侧选卡原则**：优先选交付物；明确只要「找材料／取原文／加链接」再用工具卡。参数与错误码以本文为准。

---

## 七、输出与法律纪律底线

1. 每条依据附链接（语义类 `url`；列表类取 `Url` 裸链）。
2. 非「现行有效」或含废止／修改必须显式提示；`timeliness: 现行有效` **不保证所引上位法仍现行**。
3. 效力位阶与新法／特别法规则照常适用。
4. 案例力度：指导性案例（应参照）> 公报 > 典型／参考 > 普通；样本不足不概括裁判倾向。
5. 空结果不编造；关键词 0 命中可转语义，仍 0 则让用户换表述。
6. 资料研究与工作底稿，**不构成正式法律意见**。

更完整的溯源标签与审阅提示格式见仓库 `docs/GUARDRAILS.md`（工具 Skill 单独导入时：本副本已够用；交付型 Skill 另有自带的 `references/guardrails.md`）。
