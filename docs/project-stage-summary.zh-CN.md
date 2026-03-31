# 项目阶段总结与协作说明

这份说明写给项目协作者。它的目标很简单：

- 让新加入的人快速明白三部分分别做到哪一步了
- 让大家知道现在能直接用什么
- 让大家知道当前还缺什么
- 让大家知道外部应该从哪里参与

## 一句话结论

这个项目已经不是“从零搭骨架”的阶段了，而是进入了“可以协作推进、可以持续回灌、可以按批次迭代”的阶段。

三部分现在的关系是：

1. 第一部分负责定标准。
2. 第二部分负责收数据、清数据、对齐数据。
3. 第三部分负责从图片里把候选结果识别出来，再交回第二部分和第一部分继续收敛。

## 三部分当前阶段

### 1. 第一部分：`jianzi-code-spec`

**当前阶段**

已经完成核心协议草案，具备独立项目的基本轮廓，可以作为当前协作的统一语言。

**当前可用能力**

- 已有 `Jianzi-Code` 的核心 Schema
- 已有整曲级文档结构
- 已有 TypeScript 类型定义
- 已有示例文件
- 已有字段词典、版本规则、校验说明和真实样本回压记录

**当前主要缺口**

- 还需要更多真实谱例来继续压测字段边界
- 还需要更细的装饰音、后续处理和特殊情况规则
- 还需要把更多导入/导出映射文档补齐

**外部参与入口**

- 适合音乐专业协作者：一起确认字段语义、谱字规则、装饰音表达
- 适合工程协作者：补转换器、校验器和示例数据
- 适合整理协作者：提供更多真实样例和边界案例

相关入口文件：

- [packages/jianzi-code-spec/README.md](../packages/jianzi-code-spec/README.md)
- [packages/jianzi-code-spec/OVERVIEW.zh-CN.md](../packages/jianzi-code-spec/OVERVIEW.zh-CN.md)
- [packages/jianzi-code-spec/docs/field-dictionary.zh-CN.md](../packages/jianzi-code-spec/docs/field-dictionary.zh-CN.md)
- [packages/jianzi-code-spec/docs/versioning-policy.zh-CN.md](../packages/jianzi-code-spec/docs/versioning-policy.zh-CN.md)

---

### 2. 第二部分：`dataset-tools`

**当前阶段**

已经从“规划”进入“可实际使用的工作流”阶段。它不再只是一个设想，而是已经能接入外部数据、人工标注和 OCR 输出。

**当前可用能力**

- 能导入 `gui-tools`
- 能导入 `KuiSCIMA`
- 能导入人工准备的来源表和粗标注表
- 能导入第三部分输出的 OCR bundle
- 能做数据总览、标准化、中间结果整理和事件草稿生成
- 能生成人工复核队列、复核批次和交付包
- 能把线上校对结果回灌到主数据里
- 能评估这轮人工复核带来了什么变化
- 能推荐下一批更值得继续处理的页面

**当前主要缺口**

- 还需要把“漏框”纳入更完整的人工作业闭环
- 还需要继续增强批次挑选和质量判断
- 还需要把更多外部来源统一到同一种内部工作区模型里
- 还需要持续补版本追踪和来源追溯的细节

**外部参与入口**

- 适合数据协作者：准备 PDF、页图、来源信息、人工判断结果
- 适合标注协作者：继续处理复核批次
- 适合工程协作者：补 importer、校验器、导出器和评估规则

相关入口文件：

- [apps/dataset-tools/README.md](../apps/dataset-tools/README.md)
- [apps/dataset-tools/docs/manual-workflow.zh-CN.md](../apps/dataset-tools/docs/manual-workflow.zh-CN.md)

常用入口能力：

- `import-gui-tools`
- `import-kuiscima`
- `import-manual-csv`
- `import-ocr-bundle`
- `process-bundle`
- `build-review-queue`
- `apply-online-review-db`
- `evaluate-review-impact`
- `recommend-next-batch`

---

### 3. 第三部分：`ocr-engine`

**当前阶段**

已经有了可跑的第一版 OCR 骨架，不是正式模型，但已经能和第二部分联动，形成完整的识别-回流路径。

**当前可用能力**

- 有页级预处理和基础检测流程
- 有 OCR bundle 输出
- 有检测训练集导出
- 有人工复核裁切集导出
- 有检测训练、分类训练、评估和过滤任务入口
- 能把结果稳定交回第二部分继续处理

**当前主要缺口**

- 还没有训练成熟的正式检测模型
- 还没有真正稳定的高质量识别模型
- 还需要更强的评测体系来衡量每一轮提升
- 还需要更多真实训练数据和更完整的难例覆盖

**外部参与入口**

- 适合视觉协作者：提供更多页图样本和难例
- 适合标注协作者：继续修正误框、补充漏框线索
- 适合工程协作者：训练模型、做评测、优化过滤规则

相关入口文件：

- [apps/ocr-engine/README.md](../apps/ocr-engine/README.md)
- [apps/ocr-engine/docs/runtime-environment.zh-CN.md](../apps/ocr-engine/docs/runtime-environment.zh-CN.md)
- [apps/ocr-engine/docs/reviewed-filter-training.zh-CN.md](../apps/ocr-engine/docs/reviewed-filter-training.zh-CN.md)

常用入口能力：

- `detect`
- `summarize`
- `export-yolo-detect`
- `export-reviewed-crops`
- `train-yolo-detect`
- `train-yolo-classify`
- `evaluate-yolo-classify`
- `filter-yolo-bundle`

## 当前最重要的协作入口

如果你是新加入的协作者，建议按这个顺序看：

1. 先看本文件，知道三部分现在分别到哪一步。
2. 再看第一部分的 `Jianzi-Code` 规范，确认“我们到底在记录什么”。
3. 再看第二部分的 `dataset-tools`，理解“数据怎么被整理进标准里”。
4. 最后看第三部分的 `ocr-engine`，理解“机器怎么把图像先变成候选结果”。

## 现在适合谁加入

### 音乐专业协作者

你最适合参与的是：

- 确认减字、装饰音、后续处理的表达是否合理
- 解释边界情况
- 审核示例是否符合古琴演奏与谱学常识

### 数据协作者

你最适合参与的是：

- 准备 PDF 和页图
- 准备来源信息
- 补人工粗标注
- 处理复核批次

### 工程协作者

你最适合参与的是：

- 补 importer
- 补评测
- 补训练流程
- 补导出与回灌流程

## 目前的协作方式

现在最有效的方式不是“先等一个大而全系统完成”，而是边做边回流：

1. 第一部分先把标准定住。
2. 第二部分把真实数据整理进标准。
3. 第三部分把 OCR 结果源源不断喂回第二部分。
4. 人工校对结果再反向改进第三部分和第一部分。

这意味着项目已经可以长期协作，而不是一次性脚本工程。

## 下一步的共同目标

接下来最值得继续推进的事情是：

- 增加更多真实样本，继续压测第一部分
- 扩大第二部分的漏框和复核闭环
- 等 GPU 资源恢复后，正式推进第三部分模型训练
