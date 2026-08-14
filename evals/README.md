# Eval 夹具（全部虚构，均标演示）

| 目录 | 预期 |
| --- | --- |
| `invented-case-number/` | `check_receipts.py` 必须失败 |
| `total-as-count/` | `lint_report.py` 必须失败 |
| `repealed-as-error/` | `check_audit_rubric.py --expect-bad-audit` 必须成功（核验本身是错的） |
| `pass-labor/` | 回执通过；签发为修正后可签发（退出码 2 可接受） |

跑：`bash scripts/eval.sh`
