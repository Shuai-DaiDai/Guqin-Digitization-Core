# gui-tools 与 KuiSCIMA importer 实施计划

## 目标

优先实现两个 importer：

1. `gui-tools` importer
2. `KuiSCIMA` importer

它们的共同目标，是把外部结构化数据统一导入我们自己的 dataset workspace，并最终支持投影到 `Jianzi-Code`。

## 为什么先做这两个

因为这两个 importer 合在一起，能最早解决第二部分最关键的两种输入：

- `gui-tools`：我们自己做出来的标注数据
- `KuiSCIMA`：外部现成的 image-linked、symbol-level 机器可读数据

有了这两个 importer，我们第二部分就不再只是空架子，而是开始真正有数据流。

## 总体原则

### 1. Importer 只负责“理解外部格式”

它不负责做所有事情。

Importer 的职责应该只到这里：

- 读外部文件
- 校验外部最小必要字段
- 转成内部中间对象
- 记录来源和转换日志

### 2. Importer 不直接写最终训练集

它的输出应该先进 internal workspace。

后面的：

- 清洗
- 对齐
- 导出
- 切分

都应由 pipeline 后续阶段负责。

### 3. 每个 importer 都要保留来源痕迹

至少要保留：

- source type
- source file
- source object id
- import timestamp

这样后面发现问题时，能追溯回原文件。

## 统一内部输出对象

两个 importer 第一版都输出到同一组内部对象：

- `SourceManifest`
- `PageRecord`
- `GlyphRecord`
- `ImportLog`

第二版再补：

- `AlignmentRecord`
- `ScoreRecord`
- `JianziCodeCandidate`

## gui-tools importer

### 输入

- `gui-tools` 的 jianzipu JSON
- 对应图像文件

### 第一版要抽取的字段

- image path
- annotation order
- `box_type`
- `text_coordinates`
- `notation_coordinates`
- `notation_content`

### 第一版输出

- 生成页级记录
- 生成 box / glyph 级记录
- 把 notation 内容原样保留到内部 `raw_notation_payload`

### 第一版不做

- 完整语义归一化
- 自动生成完整 `Jianzi-Code`
- 多页面复杂对齐

### 验收标准

- 给定一个 `gui-tools` 标注项目，能稳定导入
- 导入后页数、box 数、主要 box 类型统计正确
- 原始 notation 信息没有丢

## KuiSCIMA importer

### 输入

- KuiSCIMA JSON
- 对应图像引用

### 第一版要抽取的字段

- piece metadata
- images list
- symbol-level positions
- notation / text content
- notation type

### 第一版输出

- 生成页级记录
- 生成 symbol / glyph 级记录
- 生成 piece 级来源记录

### 第一版重点

重点不是“完全翻译成我们的语义层”，而是先把：

- image-linked structure
- notation object
- metadata

稳定吸进 internal workspace。

### 第一版不做

- 完整的 jianzipu 语义解释
- 把所有 KuiSCIMA notation 都强行塞进 `Jianzi-Code`

### 验收标准

- 至少能导入一批 KuiSCIMA 样本
- 页、符号、元数据的关系不丢
- 导入结果能进入后续 pipeline

## 两个 importer 的差异

### gui-tools importer

更偏“我们自己的标注生产工具入口”。

关键点：

- 兼容人工标注结果
- 接住 box-first JSON

### KuiSCIMA importer

更偏“外部公开语料入口”。

关键点：

- 兼容已有 image-linked corpus
- 给第三部分提供冷启动粗标注

## 建议的文件结构

建议未来实现时按下面方式组织：

```text
apps/dataset-tools/src/dataset_tools/
  adapters/
    gui_tools.py
    kuiscima.py
  models/
    manifest.py
    page.py
    glyph.py
    import_log.py
  pipeline/
    ingest.py
    normalize.py
```

## 实施顺序

### Phase 1

先写 `gui-tools` importer。

原因：

- 它更接近我们马上能拿到的自建标注数据
- 能最快形成我们自己的最小闭环

### Phase 2

再写 `KuiSCIMA` importer。

原因：

- 它更适合作为外部冷启动数据源
- 导入后能帮助第三部分提前做实验

### Phase 3

统一 importer 输出结构，并补：

- 统计报告
- 基本校验
- 导入失败日志

## 第一版成功标准

如果下面 4 件事都做到，就算 importer 第一版成功：

1. 能读入 `gui-tools` 标注结果
2. 能读入 KuiSCIMA 样本
3. 两者都能统一落到 internal workspace
4. 后续 pipeline 可以基于这些数据继续处理

## 不要一开始做的事情

第一版不要试图：

- 解决所有 notation 差异
- 自动还原所有古琴语义
- 做复杂多版本对齐
- 直接追求“最终完美格式”

第一版只要做到：

把外部数据稳稳接住，而且不丢信息。

## 一句话策略

先把 `gui-tools` 和 `KuiSCIMA` 变成我们能读懂的输入，再谈更高层的清洗、对齐和导出。Importer 第一版的价值，不是“翻译得多漂亮”，而是“接得稳、留得全、能往后走”。
