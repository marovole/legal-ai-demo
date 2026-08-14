# pkulaw-case-research-report · 类案检索报告

出具符合《最高人民法院关于统一法律适用加强类案检索的指导意见（试行）》（法发〔2020〕24 号）**第八条法定七要素**的类案检索报告。

**这份报告的结构不用我们发明，它是法定的。** 所以本 Skill 在要素完整性、检索顺位、效力表述上是零自由度；模型该发挥的只有一处——相似性识别与决定性差异的判断（第六条）。

## 与现有轻量类案备忘的关系

本 Skill 承接并替代已删除的 `pkulaw-mcp-case-memo`：按法发〔2020〕24 号法定七要素出正式报告，不再做「轻量备忘」形态。需要庭前研判请用 `pkulaw-pretrial-assessment`。旧模板对照第八条只满足约一个半要素（检索主体、时间、平台、方法、结果、待决争点、结果运用等大多缺失），按法院标准不能归档。

## 三个特有机制

1. **受众阻塞闸门（第 0 步）** —— 法院版、呈交法官版、内部版在"写不写检索过程"和"放不放不利案例"两点上要求**相反**，不是详略之别。受众未确认不开工。
2. **指导性案例单独检索一轮** —— 依第十条，提交指导性案例能强制法院在裁判文书说理中回应，所以它的优先级高于事实相似度。法宝按相关度排序，不会替你做这件事。
3. **劝退能力** —— 适格类案不足或规则已明确时，主动说明不必做这份报告并给替代方案。一份凑出来的报告比不做更糟。

## 文件

| 文件 | 内容 |
|---|---|
| [SKILL.md](./SKILL.md) | 八步流程、交付物纪律、降级策略 |
| [template.md](./template.md) | 输出模板 + 生成时逐项自查的硬性要求 |
| [examples.md](./examples.md) | 三个测试用例（主用例／劝退／受众冲突）+ 18 项验收标准 + 已知失分模式 |
| [references/statutory-structure.md](./references/statutory-structure.md) | 法发〔2020〕24 号**十二条逐字原文**（法宝逐条取回）+ 落地规则 |
| [references/search-protocol.md](./references/search-protocol.md) | 三种法定检索方法 → 法宝 MCP 映射，**含两处能力缺口的近似做法** |
| [references/similarity-and-screening.md](./references/similarity-and-screening.md) | 三维度比对、决定性差异、数量与位阶、三重核验、冲突处理 |
| [references/audience-variants.md](./references/audience-variants.md) | 三种受众的相反要求与编排骨架 |
| [references/guardrails.md](./references/guardrails.md) | **由 `scripts/build-guardrails.ps1` 生成，勿手改** |
| [references/guardrails-appendix.md](./references/guardrails-appendix.md) | 本域补充：措辞禁区、引注陷阱 |

## 引注说明

`references/statutory-structure.md` 里的十二条原文于 **2026-07-29** 经北大法宝逐条取回（[法宝原文](https://pkulaw.com/chl/0749b01d6f2da00dbdfb.html)，时效性「现行有效」），未经转述。核验中的两点发现已写入 Skill：

- **第十一条**给了处理类案冲突的**法定**因素（法院层级、裁判时间、是否经审判委员会讨论），与实务界的"民再 > 民终 > 民初 > 民申"位阶不是一回事，两者不得混用。
- **第三条**列举的检索平台为中国裁判文书网、审判案例数据库，**不含北大法宝**——法院版报告的「检索平台」要素必须据实披露。

## 尚未验证

**本 Skill 未附 `sample-output`。** 产出物由使用者按 [examples.md](./examples.md) 的示例提示词实跑生成，再对照 18 项验收标准核。注意主用例的正确行为是**第一轮先问受众**，不是直接出报告。
