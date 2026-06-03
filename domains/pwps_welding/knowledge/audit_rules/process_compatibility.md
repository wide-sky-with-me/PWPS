# 工艺兼容性审计规则

## 规则 1: 焊法与焊材匹配 (process_consumable_match)

**类型**: HARD
**严重度**: HIGH
**检查字段**: welding_process, consumable

**规则描述**:
焊法（welding_process）和焊材（consumable）必须兼容。不同焊法使用不同类型的焊材：

| 焊法 | 兼容焊材类型 | 不兼容焊材 |
|------|------------|-----------|
| GMAW | 实芯焊丝 (ER50-6, ER70S-6等) | 药芯焊条 (J422, E7018等) |
| SMAW | 药芯焊条 (J422, E7018, E5015等) | 实芯焊丝 |
| GTAW | 实芯焊丝 (ER50-6, ER80S-B2等) | 药芯焊条 |
| SAW | 焊丝+焊剂 (H08A+SJ101等) | 手工焊条 |

**典型错误**:
- GMAW + J422: J422 是 SMAW 用的药芯焊条，不能用于 GMAW
- SMAW + ER50-6: ER50-6 是 GMAW/GTAW 用的实芯焊丝，不能用于 SMAW

**修复建议**:
- 更换焊材为与焊法兼容的类型
- 或者更改焊法以匹配用户指定的焊材

---

## 规则 2: 焊接位置与焊法兼容 (position_process_compatibility)

**类型**: HARD
**严重度**: HIGH
**检查字段**: welding_process, welding_position

**规则描述**:
某些焊法对焊接位置有限制：

| 焊法 | 允许的位置 | 说明 |
|------|-----------|------|
| SAW (埋弧焊) | 仅 flat (平焊) | SAW 通常只能在平焊位置使用 |
| GMAW | 所有位置 | 但立焊和仰焊需要特殊技术 |
| SMAW | 所有位置 | 最灵活的焊法 |
| GTAW | 所有位置 | 但效率较低 |

**典型错误**:
- SAW + vertical: 埋弧焊不能在立焊位置使用
- SAW + overhead: 埋弧焊不能在仰焊位置使用

**修复建议**:
- 更改焊接位置为 flat
- 或者改用支持所需位置的焊法（如 SMAW、GMAW）

---

## 规则 3: 材料与焊材兼容 (material_consumable_compatibility)

**类型**: RISK
**严重度**: HIGH
**检查字段**: base_material, consumable

**规则描述**:
焊材必须与母材的化学成分和力学性能匹配：

- 低碳钢 (Q235B, Q345R): 使用 ER50-6, J422, E7018 等
- 不锈钢 (304, 316): 使用 ER308, ER316, A102 等
- 铬钼钢 (Cr-Mo): 使用 ER80S-B2, E8018-B2 等
- 镍基合金: 使用 ERNiCrMo-3, ENiCrMo-3 等

**检查方法**:
查询知识库中对应材料的标准焊材推荐。
