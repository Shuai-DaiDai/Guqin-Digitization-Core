# jianzi-code-spec

这个模块定义 `Jianzi-Code` 的核心数据协议，是整个仓库的公共语言层。

## 设计依据

在参考现有三个古琴相关仓库之后，我们刻意没有直接复用它们任意一种格式作为主标准：

- `guqincomposer`
  很擅长表达“怎么弹”。它把一个音拆成弦、右手、左手、滑音、按徽等演奏信息，适合做录入和渲染中间层。

- `Guqin-Dataset`
  很擅长表达“最后听到什么”。它把简谱快速转成 MusicXML，并保留曲目元信息、定弦和段落切分，适合做符号音乐输出层。

- `Guqin-dataset`
  与 `Guqin-Dataset` 基本属于同一条数据谱系，重点仍然在简谱录入与 MusicXML 转换。

因此，`Jianzi-Code` 的目标不是替代它们，而是做一个更底层、更稳定的“规范格式”：

1. 能容纳 OCR 看到的减字结构。
2. 能容纳演奏动作语义。
3. 能容纳最终音高、时值和导出格式。
4. 能同时承接简谱、NLTabs、MusicXML 等外部表示，而不被它们绑死。

## 当前提供

- `schema/jianzi-v1.schema.json`
  单个音符事件的核心三层结构。

- `schema/jianzi-document-v1.schema.json`
  整曲级文档结构，包含曲目信息、定弦、段落、小节与音符事件。

- `examples/jianzi-document-v1.example.json`
  一个最小可读示例，演示如何把曲目元信息、小节和单音事件连起来。

- `OVERVIEW.zh-CN.md`
  面向非程序背景读者的中文说明页，用来解释这套规范的意义、价值和使用方式。

- `docs/field-dictionary.zh-CN.md`
  面向协作成员的字段词典，统一术语含义。

- `docs/versioning-policy.zh-CN.md`
  独立项目的版本升级规则和兼容性原则。

- `docs/real-examples-review.md`
  用真实样式样本回压当前规范后得到的缺口复盘。

- `docs/validation.md`
  本地校验脚本的使用说明。

- `docs/ocr-to-jianzi-code-bridge.zh-CN.md`
  从 OCR 输出一路桥接到 `Jianzi-Code` 草稿的分层说明，明确每一步保留什么、人工确认什么。

- `types/index.ts`
  与 Schema 对齐的 TypeScript 类型定义。

## 为什么不用“速记格式”直接做标准

因为速记格式解决的是“人如何快录”，而不是“系统如何长期存”。像 `guqincomposer` 的键盘速记，或者简谱速录里的 Excel 单元格编码，都非常适合输入，但它们有三个问题：

- 含义依赖录入约定，不够自解释
- 对 OCR 和视觉结构不友好
- 很难同时兼顾演奏动作与现代音乐导出

所以 `Jianzi-Code` 采用分层设计，把“输入法”和“交换格式”分开。

## 核心结构

### 1. Document 层

整曲文件保存：

- 曲名、来源、打谱者、演奏者
- 定弦
- 使用过哪些表示体系（减字谱、简谱、MusicXML、NLTabs）
- 段落与小节
- 小节中的事件序列

### 2. Note Event 层

每个音符事件都保留三层信息：

- `visual`
  减字字形与部件槽位，服务 OCR、前端渲染和人工校对。

- `physical`
  弦位、徽位、右手指法、左手按法、泛音/按音/散音类别，以及滑音、吟猱等装饰。

- `acoustic`
  音高、MIDI、时值、MusicXML 片段，以及可选的简谱表示。

## 推荐原则

- 把 `Jianzi-Code` 当作规范主格式
- 把 NLTabs、简谱速录、MusicXML 当作导入或导出视图
- OCR 阶段优先填满 `visual`
- 语义标注阶段补全 `physical`
- 播放与分析阶段消费 `acoustic`
