# 第三部分设计：`ocr-engine` 架构规划

## 1. 目标定义

第三部分的目标不是单纯“识别一个字是什么”，而是构建一条从古琴谱影印页到结构化候选结果的视觉识别链路。

它需要服务两个下游：

1. 第二部分 `dataset-tools`
   负责接住 OCR 输出，做对齐、校对、导出和回填。
2. 第一部分 `jianzi-code-spec`
   负责定义最终标准格式。

所以第三部分的正确定位应该是：

- 输入：谱页图像、谱字切块、已有粗标注
- 输出：带置信度的 page / glyph / component / structure 候选
- 不直接假装给出最终真相
- 必须天然支持人工复核和回填

## 2. 外部参考资料的意义

### `guqinMM`

参考价值：

- 它明确把问题拆成 `Jianzipu OCR` 和后续音乐生成两层
- 强调图像数据和 jianzi 分解树并行存在
- 说明“字形分解”不是附属功能，而是核心任务

限制：

- 更像研究原型，不像可直接复用的工程主线
- 数据和流程都还不够稳定，不适合作为我们的长期主系统

来源：

- [guqinMM GitHub](https://github.com/wds-seu/guqinMM)

### `KuiSCIMA v2.0`

参考价值：

- 强调 scarce + imbalanced data 下的识别问题
- 采用 leave-one-edition-out 这类更稳的评估方式
- 说明 calibration 不能省略
- 数据已经包含 symbol-level positions，说明“位置 + 语义并存”是正确路线

限制：

- 主要世界是 `Baishidaoren Gequ`
- 不等于我们真实古琴谱目标域

来源：

- [KuiSCIMA GitHub](https://github.com/SuziAI/KuiSCIMA)
- [KuiSCIMA v2.0 论文信息](https://tugraz.elsevierpure.com/en/publications/58455cb2-f276-45ff-8ffc-d01900472b47)
- [ICDAR 2025 accepted papers](https://www.icdar2025.com/program/accepted-papers)

### `gui-tools`

参考价值：

- 已经支持 `suzipu / lülüpu / jianzipu`
- 已经支持 segmentation boxes 和 notation annotation
- 可直接作为标注前端，支持第三部分数据构建

限制：

- 它是标注工具，不是 OCR 引擎
- 输出仍然需要接回我们自己的工作区

来源：

- [gui-tools GitHub](https://github.com/SuziAI/gui-tools)

### YOLO radicals 论文

参考价值：

- 证明“radical / component 识别”是可行子任务
- 说明把问题拆到部件层有工程价值

限制：

- 数据只覆盖很窄的曲目和版本范围
- 论文自己也指出 full notation 上仍有检测困难

来源：

- [Recognition of Radicals of Guqin Music Notation by YOLOs](https://link.springer.com/chapter/10.1007/978-981-95-3141-7_11)

## 3. 三种可选路线

### 路线 A：端到端整页直接输出 `Jianzi-Code`

优点：

- 看起来最“AI 一步到位”

缺点：

- 对数据量要求太高
- 对复杂版面和古籍噪声太敏感
- 调错成本极高
- 结果不可解释，不利于和第二部分做人工闭环

判断：

- 不适合当前阶段

### 路线 B：整字识别为主，部件识别为辅

优点：

- 比端到端稳
- 可以较快做出首版

缺点：

- 遇到罕见字、破损字、变体字时泛化不够好
- 无法充分利用减字谱的组合结构

判断：

- 可作为早期 baseline，但不应是长期主架构

### 路线 C：多阶段组合式 OCR

推荐路线。

核心思路：

1. 先做页级预处理和版面规范化
2. 再做谱字 / 标注对象检测
3. 再做 glyph-level 识别和 component-level 识别
4. 再做结构解码和候选融合
5. 最后把结果送给第二部分做规范化和人工复核

优点：

- 和减字谱的组合性质最匹配
- 更适合小数据和长尾类别
- 错误可定位、可解释、可修复
- 与第二部分天然闭环

缺点：

- 系统更复杂
- 需要设计清晰的数据接口

判断：

- 这是最适合我们当前项目阶段的架构

## 4. 推荐总架构

```text
Page Image
  -> Preprocess / Rectify
  -> Layout & Glyph Detector
  -> Glyph Crop Bank
  -> Whole-Glyph Recognizer
  -> Component / Radical Detector
  -> Structure Decoder
  -> Candidate Fusion + Calibration
  -> OCR Output Bundle
  -> dataset-tools
  -> Jianzi-Code / Review Queue
```

### 4.1 Page Preprocess

职责：

- 去噪
- 灰度化 / 二值化实验
- 倾斜校正
- 页边裁切
- 对比度增强

输出：

- 规范化页图
- 预处理元数据

### 4.2 Layout & Glyph Detector

职责：

- 从整页中找出可疑谱字区域
- 同时检测标题、正文、旁注、行列结构辅助对象

推荐首版：

- YOLO 系列检测器作为 baseline
- 输出 box + confidence + page position

原因：

- YOLO 路线已有外部研究支撑
- 对冷启动更快

### 4.3 Whole-Glyph Recognizer

职责：

- 对切下来的单字图进行粗识别
- 给出 top-k glyph 候选

推荐首版：

- 先做图像分类 baseline
- 后续再上序列或结构模型

### 4.4 Component / Radical Detector

职责：

- 在单个 glyph crop 内定位关键部件
- 输出 radical / component box 与类别

推荐首版：

- 小目标检测器或部件分类器
- 首批类别只覆盖高频部件，不追求一步全覆盖

### 4.5 Structure Decoder

职责：

- 把 whole-glyph 候选和 component 候选拼成结构化结果
- 填 canonical slots：
  `top_left`, `top_right`, `bottom_inner`, `bottom_outer`

这一层是第三部分真正和第一部分握手的关键。

### 4.6 Candidate Fusion + Calibration

职责：

- 融合整字识别和部件识别结果
- 给出 top-k 候选及置信度
- 标记低置信度条目

这一层必须做 calibration。
原因不是学术漂亮，而是第二部分后面要靠它决定哪些条目优先人工处理。

## 5. 与第二部分的接口

第三部分不直接输出最终 `Jianzi-Code`，而是输出 OCR bundle，交给第二部分消化。

建议最小输出对象包括：

- `page_id`
- `glyph_id`
- `bbox`
- `box_type`
- `glyph_candidates`
- `component_candidates`
- `layout_guess`
- `confidence`
- `model_version`
- `provenance`

第二部分再负责：

- 导入
- 对齐
- 规则补全
- review queue
- 人工回填

## 6. 推荐评测体系

第三部分不能只看一个总准确率。

必须分层评估：

### 6.1 Page / Detection 层

- mAP
- Recall
- 小目标召回率
- 漏检率

### 6.2 Glyph 层

- Top-1
- Top-3
- Character Error Rate
- 长尾类召回

### 6.3 Component 层

- component mAP
- slot fill accuracy
- 高价值技法部件召回

### 6.4 End-to-End 实用层

- 进入第二部分后，多少条被自动补成可用草稿
- 多少条进入高优先级 review queue
- 人工修订量是否下降

### 6.5 泛化层

- leave-one-edition-out
- leave-one-source-out
- 跨版本评估

## 7. Phase 规划

### Phase 0：数据接口冻结

目标：

- 定义 OCR 输出 bundle 结构
- 与第二部分接口完全对齐

### Phase 1：检测 baseline

目标：

- 在页图上稳定找到谱字框

首版建议：

- YOLO detector

### Phase 2：整字识别 baseline

目标：

- 在 glyph crop 上建立 top-k 候选能力

### Phase 3：部件识别 baseline

目标：

- 从 glyph crop 中检测关键 radicals / components

### Phase 4：融合与结构解码

目标：

- 生成真正可供第二部分消费的 OCR candidates

### Phase 5：校准与评测

目标：

- 建立可靠置信度
- 接入工作区统计和误差分析

## 8. 关键决策

### ADR-1

不选择端到端整页直出 `Jianzi-Code` 作为首架构。

原因：

- 现在数据还不够
- 组合结构比端到端黑盒更重要

### ADR-2

首版检测器采用 YOLO baseline。

原因：

- 外部研究已有验证
- 工程落地快

### ADR-3

长期主架构采用“整字识别 + 部件识别 + 结构解码”的组合路线。

原因：

- 最符合减字谱组合式本质
- 与第一部分和第二部分接口最好

### ADR-4

第三部分必须输出校准后的候选，而不是单个强行定值。

原因：

- 第二部分需要拿它生成 review queue

## 9. 风险与缓解

### 风险 1：真实页图质量差异太大

缓解：

- 预处理参数集
- source-aware evaluation

### 风险 2：长尾 glyph 和罕见部件太多

缓解：

- component-first 设计
- top-k 输出
- review loop

### 风险 3：整字识别与部件识别互相冲突

缓解：

- 单独保留两路结果
- 结构解码层做融合，不在前面硬合并

### 风险 4：模型分数不可用

缓解：

- calibration
- review priority 按校准分数而不是裸分

## 10. 最终建议

第三部分的推荐实现路线是：

**YOLO 检测 baseline + glyph classifier baseline + component detector + structure decoder + calibration + dataset-tools 闭环**

这条路线不是最炫的，但最稳、最符合项目现阶段实际，也最容易和前两部分接起来。
