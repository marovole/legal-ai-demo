# 一案一档

一案一目录。写报告前先开档。每条引用必须有回执。导出前跑闸门脚本。

## 开档

```bash
cp -R matters/_template matters/<案号或短名>
```

然后填 `brief.md`（案由 / 焦点 / 事实 / 初步定性）。用途未确认不开工。

## 每案六件

| 文件 | 谁写 | 规则 |
| --- | --- | --- |
| `brief.md` | 律师 | 不要让 Agent 补写事实 |
| `search-log.md` | Agent | 时间 / 工具 / 查询式 / 返回id或案号或法条 / url / 回执ID |
| `report.md` | Agent | 类案报告底稿；每条引用必须能指回本表回执 |
| `lawyer-delta.md` | 律师 | 改方向和口径；Agent 不得自行改回 |
| `audit.md` | Agent | 九维核验 + 签发三态置顶 |
| `signoff.md` | 核验人 | 可以签发必须有核验人 + ISO 时间；不得签发禁止导出 |

演示卷宗：[`demo-labor-dismissal/`](./demo-labor-dismissal/)。

## 导出闸门

```bash
python3 scripts/check_receipts.py matters/<id>
python3 scripts/check_signoff.py matters/<id>
```

`check_signoff.py`：可以签发 → 0；修正后可签发 → 2（不可导出）；不得签发 / 未核验 / 缺核验人时间 → 1。

全仓回归：`bash scripts/eval.sh`。
