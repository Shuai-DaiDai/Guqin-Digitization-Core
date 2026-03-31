# ADR: 第三部分采用多阶段组合式 OCR 架构

## 状态

Accepted

## 背景

古琴减字谱不是普通现代印刷字符识别问题。

它同时具有这些特点：

- 组合式结构明显
- 变体和长尾多
- 历史版本差异大
- 页面质量不稳定
- 最终结果必须能进入人工复核流程

## 决策

第三部分采用多阶段组合式 OCR 架构，而不是首版就走端到端整页直出。

推荐结构：

1. page preprocess
2. layout / glyph detection
3. whole-glyph recognition
4. component / radical detection
5. structure decoding
6. calibration
7. 输出给 `dataset-tools`

## 原因

### 不选端到端直出

- 数据仍然偏少
- 错误不可解释
- 不利于人工闭环

### 不只做整字分类

- 无法充分利用减字谱的结构性
- 长尾 glyph 泛化差

### 选择组合式

- 更符合减字谱本质
- 更容易诊断错误
- 更容易把外部研究成果吸收进来
- 更容易与第二部分衔接

## 后果

正面：

- 可解释
- 易扩展
- 易与 review queue 对接

负面：

- 系统更复杂
- 需要设计清晰的数据接口

## 外部依据

- [guqinMM GitHub](https://github.com/wds-seu/guqinMM)
- [KuiSCIMA GitHub](https://github.com/SuziAI/KuiSCIMA)
- [gui-tools GitHub](https://github.com/SuziAI/gui-tools)
- [KuiSCIMA v2.0 论文信息](https://tugraz.elsevierpure.com/en/publications/58455cb2-f276-45ff-8ffc-d01900472b47)
- [Recognition of Radicals of Guqin Music Notation by YOLOs](https://link.springer.com/chapter/10.1007/978-981-95-3141-7_11)
