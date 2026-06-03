# 参数完整性审计规则

## 规则 1: 焊接参数完整性 (parameter_completeness)

**类型**: COMPLETENESS
**严重度**: MEDIUM
**检查字段**: current_range, voltage_range, travel_speed

**规则描述**:
焊接工艺参数必须完整。以下三个参数是生成 pWPS 草案的最低要求：
- current_range (电流范围)
- voltage_range (电压范围)
- travel_speed (焊接速度)

缺少任何一个参数都会导致草案不完整。

**修复建议**:
补充缺失的参数。可以通过以下方式获取：
1. 从知识库中查询相同材料+焊法+厚度的 WPS/PQR 实例
2. 从标准文档中查找推荐参数范围
3. 由焊接工程师提供

---

## 规则 2: 热输入一致性 (heat_input_consistency)

**类型**: RISK
**严重度**: MEDIUM
**检查字段**: current_range, voltage_range, travel_speed, heat_input

**规则描述**:
热输入（heat_input）应与电流、电压、速度的计算结果一致。

**公式**:
```
heat_input (kJ/mm) = current(A) × voltage(V) × 60 / (travel_speed(cm/min) × 1000)
```

**检查方法**:
1. 取电流、电压、速度的平均值
2. 用公式计算热输入
3. 与声明的热输入比较
4. 如果差异 > 0.5 kJ/mm，标记为不一致

**示例**:
- 电流: 180A-240A (平均 210A)
- 电压: 22V-28V (平均 25V)
- 速度: 25-35 cm/min (平均 30 cm/min)
- 计算: 210 × 25 × 60 / (30 × 1000) = 10.5 kJ/mm
- 如果声明的热输入是 0.8-1.6 kJ/mm，则明显不一致

**修复建议**:
- 重新计算热输入
- 或调整电流/电压/速度使之一致
