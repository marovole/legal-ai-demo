# 律师 AI 所内可签发工作流

给执业律师用的 Cursor 项目。数据走北大法宝 MCP，模型可换。**AI 只出底稿，律师定方向并签发。** 无一案一档、无回执、无核验人+时间，不得导出。

**试用：** 控制台注册后先领试用：9 个 MCP 服务各 100 次、30 天、每用户一次。Token 没订阅对应服务会 401/403。定价：https://mcp.pkulaw.com/pricing

## 生产回路（按这个做）

1. 在 https://mcp.pkulaw.com/console 领取 Access Token，写入环境变量 `PKULAW_ACCESS_TOKEN`（不要写进仓库）。用 Cursor 打开本仓库。
2. `.cursor/mcp.json` 已是 4 个核心服务（法规语义、案例语义、法条点查、引用核验），Token 走 `${env:PKULAW_ACCESS_TOKEN}`。其余 5 个见 `.cursor/mcp.full.json.example`。
3. 复制卷宗：`cp -R matters/_template matters/<案号或短名>`。
4. 填 `brief.md` → 出类案报告写入 `report.md`，**每条引用写 `search-log.md`**（时间 / 工具 / 查询式 / 返回id或案号或法条 / url / 回执ID）。
5. 律师改 `lawyer-delta.md`（方向和口径）。
6. 引用核验写入 `audit.md` + `signoff.md`（签发三态置顶）。
7. 导出前：

```bash
python3 scripts/check_receipts.py matters/<id> && python3 scripts/check_signoff.py matters/<id>
```

可以签发必须有核验人 + ISO 时间。不得签发禁止导出。修正后可签发退出码 2，不可导出。

8. 全仓回归：

```bash
bash scripts/eval.sh
```

可选接通检查：把 [prompts/smoke-test.md](prompts/smoke-test.md) 发给 Cursor。能返回带出处的《劳动合同法》条文 = 接通。

## 红线

- 输出是底稿，不是法律意见
- 用途未确认（归档 / 呈法官 / 客户或所内）不开工
- 没检索到的法条 / 案号 / 裁判要点禁止补写
- 每条引用必须能指回 search-log 回执，否则不得「可以签发」
- 禁止把列表 Total 写成「共找到 N 条类案」
- 个位数样本不得写「法院普遍认为」
- 指导性案例必须单独检索，0 命中也留节
- 废止 ≠ 自动错误；先锚定法律事实时间
- 抽出「根据相关法律规定」无源命题
- MCP 不通：未完成核验，不得据本底稿签发
- 对外发出前必须律师本人核验
- 检索平台写「北大法宝案例库」，不要写成裁判文书网
- 不要把真实 Token 写进任何文件

## 仓库结构

```
legal-ai-demo/
├── profile.md                 # 所内默认：客户底稿 / 上海劳动争议 / 先结论
├── matters/                   # 一案一档
│   ├── _template/
│   └── demo-labor-dismissal/
├── .cursor/skills/            # 运行时官方对齐版（不要用 docs/guide）
├── .cursor/mcp.json           # 4 个核心服务
├── scripts/                   # 回执 / 签发 / 文风 / 核验量规 / MCP 配置
└── evals/                     # 虚构夹具（均标演示）
```

运行时技能：`.cursor/skills/`。精简导读：`docs/guide/`（运行时不要用）。

## 链接

- https://mcp.pkulaw.com/
- https://mcp.pkulaw.com/docs?doc=mcp-integration
- https://mcp.pkulaw.com/pricing
- https://gitee.com/pkulaw/pkulaw-skills
- https://www.npmjs.com/package/@pkulaw/mcp-cli
