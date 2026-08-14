# 律师 AI 落地 Demo

给执业律师用的 Cursor 项目。数据走北大法宝 MCP，模型可换。AI 只出底稿，律师定方向并签发。

## 10 分钟跑通

1. 打开 https://mcp.pkulaw.com/console 注册，控制台拿 Access Token（先领试用，按次买，不要三年包）。定价 https://mcp.pkulaw.com/pricing
2. 用 Cursor 打开本仓库。
3. 把 `.cursor/mcp.json` 里所有 `YOUR_ACCESS_TOKEN` 换成你的 Token（9 个 Server 共用同一个 Token）。
4. Cursor Settings → MCP，确认 pkulaw-* 已连接。
5. 在对话里发送 [prompts/smoke-test.md](prompts/smoke-test.md) 的那一句。能返回带出处的《劳动合同法》条文 = 接通。
6. 打开 [examples/labor-dismissal-sample.md](examples/labor-dismissal-sample.md)，对 Cursor 说：「按这份事实出类案检索报告」。
7. 改完方向后说：「对刚才的报告做签发前引用核验」。

## 每案工作流

1. 律师填写 [examples/case-brief-template.md](examples/case-brief-template.md)（案由 / 焦点 / 事实 / 初步定性，3–10 行）
2. 类案报告 → skill `pkulaw-case-research-report`（法发〔2020〕24 号第八条）
3. 律师删改方向和审判口径
4. 用顺手的国内模型按所里模板出稿
5. 签发前 → skill `pkulaw-citation-audit`

## 仓库结构

```
legal-ai-demo/
├── README.md
├── AGENTS.md
├── LICENSE
├── .gitignore
├── .env.example
├── .cursor/
│   ├── mcp.json
│   ├── rules/
│   │   └── legal-workflow.mdc
│   └── skills/
│       ├── pkulaw-case-research-report/
│       │   └── SKILL.md
│       └── pkulaw-citation-audit/
│           └── SKILL.md
├── examples/
│   ├── case-brief-template.md
│   └── labor-dismissal-sample.md
└── prompts/
    ├── smoke-test.md
    ├── run-case-report.md
    └── run-citation-audit.md
```

## 红线

- 输出是底稿，不是法律意见
- 没检索到的法条 / 案号 / 裁判要点禁止补写
- 对外发出前必须律师本人核验

## 链接

- https://mcp.pkulaw.com/
- https://mcp.pkulaw.com/docs?doc=mcp-integration
- https://mcp.pkulaw.com/pricing
- https://gitee.com/pkulaw/pkulaw-skills （官方 skills，可作对照；本仓库自带可执行的两份 skill）
- https://www.npmjs.com/package/@pkulaw/mcp-cli
