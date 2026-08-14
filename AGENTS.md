# 本仓库对编码 Agent 的约束

任何在本仓库里工作的编码 Agent（Cursor、Cloud Agent 等）必须遵守以下规则。

## 一案一档

- 写报告前先开档：复制 `matters/_template/` → `matters/<案号或短名>/`。
- 每案目录固定六件：`brief.md`、`search-log.md`、`report.md`、`lawyer-delta.md`、`audit.md`、`signoff.md`。
- 运行时只用 `.cursor/skills/` 官方对齐版（`pkulaw-case-research-report`、`pkulaw-citation-audit`）。`docs/guide/` 是导读，运行时不要用。

## 回执规则

- 必须通过北大法宝 MCP 检索法规和案例，禁止用网页搜索代替法律库。
- 禁止编造法条、案号、裁判要点。检索不到就写「未检索到」，不要凭记忆补写。
- 每一条法条、每一个案号都必须能指回 `search-log.md` 回执（时间、工具、查询式、返回 id/案号或法条、url、回执ID）。否则不得「可以签发」。
- 禁止把列表接口的 Total 写成「共找到 N 条类案」。
- 个位数样本不得写「法院普遍认为」。
- 指导性案例必须单独检索，0 命中也留节。

## 4 个核心 MCP

`.cursor/mcp.json` 只配置这 4 个服务：

- `pkulaw-law-search`
- `pkulaw-case-semantic-search`
- `pkulaw-law-item-keyword`
- `pkulaw-citation-validator`

Token 只允许 `${env:PKULAW_ACCESS_TOKEN}` 或占位符 `YOUR_ACCESS_TOKEN`。不要把真实 Token 写进任何文件。其余官方服务见 `.cursor/mcp.full.json.example`。未配置或不通的服务按「MCP 不通」降级，禁止凭记忆补核验。

## 签发闸门

- 用途未确认（归档 / 呈法官 / 客户或所内）不开工。默认见 `profile.md`：所内/客户底稿，不是呈法官归档件。
- 签发三态置顶：可以签发 / 修正后可签发 / 不得签发。
- 可以签发必须有核验人 + ISO 时间；不得签发禁止导出。
- 废止 ≠ 自动错误；先锚定法律事实时间。
- 抽出「根据相关法律规定」无源命题。
- MCP 不通：未完成核验，不得据本底稿签发。
- 输出是底稿，不是法律意见。
- 导出前跑 `python3 scripts/check_receipts.py matters/<id>` 与 `python3 scripts/check_signoff.py matters/<id>`。

## 类案与核验

- 类案报告必须覆盖法发〔2020〕24 号第八条：检索主体、时间、平台、方法、结果，类案裁判要点，待决案件争议焦点，以及是否参照 / 参考的分析说明。
- 检索范围优先：最高法指导性案例 → 最高法典型案例及生效裁判 → 本省高院参考性案例及生效裁判 → 上一级及本院生效裁判；除指导性案例外优先近三年。
- 引用核验不过的条目必须标「不能发」并给出改法。
- 九维核验：存在性、版本与时效、条号、条文内容、整条引用、命题对应、可引性、上位法、格式。
