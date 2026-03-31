# Dataset Tools 设计草案

## 背景

第二部分 `apps/dataset-tools` 的任务，不是训练模型，而是把零散、来源各异、质量不一的古琴谱资料，整理成可追溯、可校对、可导出、可训练的数据工作流。

它要解决的核心问题是：

1. 扫描页、裁切图、OCR 结果、人工校对结果目前没有统一落点。
2. 外部资料的表示方式不同，难以对齐到 `Jianzi-Code`。
3. 训练数据、评测数据、导出数据如果没有稳定流水线，后面 OCR 引擎会反复返工。

## 我参考过的已有实现

### 1. 古琴相关

- `neuralfirings/guqincomposer`
  提供“人类可快速录入”的语义层，说明我们需要保留弦、左右手、滑音、按徽等演奏语义。

- `lukewys/Guqin-Dataset`
  提供从简谱速录到 MusicXML 的快速转换思路，说明我们需要支持“桥接已有转录成果”的导入器，而不是强迫所有数据都从图像端重新开始。

- `yufenhuang/Guqin-dataset`
  与上面基本属于同一谱系，也说明“文本速录 -> 导出格式”的工作流很重要。

### 2. 历史文献 OCR / 手稿工作流

- `OCR-D/core`
  强项是“工作区、处理阶段、验证器、文件组”的思路，非常适合借鉴其分阶段与可追溯性，但它的 METS/PAGE 体系对我们来说偏重。

- `UB-Mannheim/escriptorium`
  强项是“历史文献转写 + OCR + 人工协作修订”的闭环，说明我们的数据工具必须把人工校订放进主流程，而不是放到流程外。

- `mittagessen/kraken`
  强项是历史文献 OCR 与转写生态，说明我们未来最好保留 line / region / transcription 这类中间对象，而不是只有最后标签。

### 3. 通用数据集与标注工具

- `open-edge-platform/datumaro`
  强项是“多格式导入导出、过滤、转换、拆分、质量检查”，这对我们的 dataset curation 很有参考价值。

- `cvat-ai/cvat`
  强项是标注界面与任务管理。它适合作为外部标注 UI，但不适合当我们的唯一真相来源。

- `iterative/dvc`
  强项是数据版本化和可复现实验。它很适合管理大数据产物，但不应该代替领域数据模型。

### 4. 音乐识别与符号重建

- `OMR-Research/muscima-pp`
  它最有价值的点，不是“能识别乐谱”，而是把低层图形对象和高层语义对象通过显式关系连起来。

- `Audiveris/audiveris`
  它体现了一个很重要的现实：OMR 不会 100% 准，所以必须同时设计“识别引擎”和“人工修订流程”。

## 可选方案

### 方案 A：简单脚本流水线

做法：

- 每一步是一个 Python 脚本
- 输入输出主要是 CSV / JSON / 图片目录
- 用文件夹命名约定来串起流程

优点：

- 上手最快
- 第一周就能跑起来
- 适合快速做实验

缺点：

- 一旦数据源变多，很快失控
- 很难知道某份导出是从哪一步来的
- 人工校对与训练样本之间关系容易丢

判断：

不推荐作为主架构。可以作为原型，但不能作为项目长期底座。

### 方案 B：完整采用 OCR-D / PAGE-XML 工作区

做法：

- 把整个数据流都压到类似 OCR-D 的 workspace 模型里
- 页级、区域级、行级、版面级都使用通用 XML 描述

优点：

- 追溯性强
- 对扫描文献工作流成熟
- 和外部文献 OCR 生态更容易互通

缺点：

- 太重
- 对古琴减字这种领域语义支持不自然
- 团队早期会花很多精力在“适配框架”，而不是“解决古琴问题”

判断：

不推荐直接照搬，但它的工作区、分阶段、验证器思想值得借鉴。

### 方案 C：Manifest-First 分阶段流水线

做法：

- 我们自己定义轻量的“工作区清单”与中间产物
- 所有输入先被导入到统一 manifest
- 所有后续步骤都围绕 manifest 和标准中间对象运行
- 外部工具只做适配器，不做真相来源

优点：

- 既足够轻，又足够稳
- 能自然接 `Jianzi-Code`
- 容易兼容图像、OCR、人工标注、MusicXML、简谱数据
- 后面接 OCR 引擎、标注平台、训练导出都顺

缺点：

- 需要我们自己定义中间数据模型
- 初期设计要稍微克制，防止过度复杂

判断：

这是我推荐的方案。

## 推荐方案

我建议 `dataset-tools` 采用方案 C：`Manifest-First + Staged Pipeline`。

一句话说，就是：

先把“数据对象”和“处理阶段”设计清楚，再把脚本和模型挂上去。

## 核心设计原则

### 1. 原始数据永远不改写

扫描图、外部 XML、外部 CSV、人工原始导出都视为只读输入。

这样做的好处是：

- 任何错误都能回溯
- 可以重复导入
- 不会因为某次清洗把原始信息污染掉

### 2. 内部只认一种规范化工作区

不管输入来自 `guqincomposer`、`Guqin-Dataset`、CVAT 导出还是未来 OCR 结果，进入 `dataset-tools` 后都先变成统一内部对象。

外部格式只是入口和出口，不是中间真相。

### 3. 图像对象和语义对象分开存

我们至少要区分这几层：

- 页面与版面对象
- 谱字或部件对象
- OCR 候选对象
- 人工修订对象
- `Jianzi-Code` 语义对象

这样以后才能既做视觉训练，也做语义对齐。

### 4. 人工校对是主流程的一部分

不要把人工修订当作“最后补丁”。

正确方式应该是：

- 机器给候选
- 人工确认或修订
- 修订结果回流成标准数据
- 标准数据再反过来支持下一轮模型训练

## 建议的数据对象

### `SourceManifest`

记录原始来源。

包含：

- 曲名
- 来源书目
- 页码
- 图像文件路径
- 校验和
- 导入时间
- 来源类型（scan / xml / csv / shorthand / annotation export）

### `PageRecord`

记录单页扫描页的规范信息。

包含：

- 页面尺寸
- 旋转状态
- 裁切边界
- 行块 / 段落 / 区域信息
- 页级质量标记

### `GlyphRecord`

记录单个谱字或谱字候选。

包含：

- 所属页面
- 边界框 / 多边形
- 图像裁切路径
- OCR 候选列表
- 人工确认文本
- 视觉部件拆分结果

### `AlignmentRecord`

记录“图像中的谱字”如何对齐到“语义事件”。

包含：

- glyph id
- 对齐到的 `Jianzi-Code event id`
- 对齐置信度
- 对齐方式（自动 / 人工）
- 对齐证据

### `ScoreRecord`

记录曲目级与段落级信息。

包含：

- 标题
- 定弦
- 版本来源
- 段落 / 小节切分
- 与 `Jianzi-Code document` 的对应关系

## 建议的流水线阶段

### Stage 1: Ingest

把外部数据导入统一工作区。

输入：

- 扫描图片
- `Guqin-Dataset` 的 metadata / MusicXML
- `guqincomposer` 的 shorthand
- 手工整理表格
- 标注平台导出

输出：

- `SourceManifest`
- 原始文件注册表

### Stage 2: Normalize

统一命名、元数据、定弦表示、曲名与版本字段。

重点处理：

- 文件命名不一致
- 定弦文本不统一
- 版本来源写法不统一
- 页码和段号不统一

### Stage 3: Layout / Segmentation Prep

生成页级与区域级中间对象，为后面的裁切、检测、标注做准备。

输出：

- `PageRecord`
- 区域框
- 行块 / 段落候选

### Stage 4: Symbol / OCR Alignment

把 OCR 候选、人工确认、已有转录结果对齐到谱字层。

这是整个模块最关键的一步。

它的目标不是直接“识别成功”，而是把：

- 图像中的对象
- 人工理解的对象
- 外部转录的对象

建立稳定映射关系。

### Stage 5: Semantic Projection

把修订后的结果投影成 `Jianzi-Code`。

这里会生成：

- note event
- document
- 对齐记录

### Stage 6: Dataset Export

面向不同用途导出不同数据包。

至少应支持：

- 检测训练集
- 分类训练集
- OCR 识别训练集
- `Jianzi-Code` 标准导出
- 统计与审阅报告

### Stage 7: Split / Evaluation

生成 train / val / test，且避免泄漏。

我的建议是优先按“曲目 / 版本 / 页面来源”切分，而不是随机按单个 glyph 切分。

否则同一谱本的相邻页会同时出现在训练和测试里，评估会虚高。

## 建议的目录与模块划分

建议未来把 `apps/dataset-tools/src` 扩成下面这样：

```text
apps/dataset-tools/src/
  dataset_tools/
    cli.py
    config.py
    models/
      manifest.py
      page.py
      glyph.py
      alignment.py
      score.py
    adapters/
      guqin_dataset.py
      guqincomposer.py
      cvat.py
      pagexml.py
      musicxml.py
    pipeline/
      ingest.py
      normalize.py
      layout.py
      align.py
      project.py
      export.py
      split.py
    validators/
      integrity.py
      schema.py
    reports/
      summary.py
```

## 建议的命令行入口

未来建议以 CLI 驱动，而不是散脚本。

例如：

```bash
python -m dataset_tools ingest
python -m dataset_tools normalize
python -m dataset_tools align
python -m dataset_tools export --target jianzi-code
python -m dataset_tools split
python -m dataset_tools validate
python -m dataset_tools report
```

## 外部工具如何接入

### 标注工具

建议把 CVAT 这类工具当“标注前端”，不是当主数据库。

也就是说：

- 任务可以从我们这里导出给 CVAT
- 标注结果可以再导回
- 但内部最终真相仍然写回我们自己的 manifest / alignment / `Jianzi-Code`

### 数据版本管理

建议后期接入 DVC 管理大数据产物，例如：

- 原始扫描包
- 裁切图
- 导出的训练集
- 评测集

但 DVC 只负责“版本化文件”，不负责“理解古琴语义”。

## 风险与已知边界

### 1. 同时音 / 和弦问题

当前 `Jianzi-Code v1` 还是单音事件中心，这会影响对复杂同时音的完整表达。

所以 `dataset-tools` 设计时要预留 group / cluster 的位置，但不必一开始就把它做满。

### 2. 来源追溯还不够细

如果后面要做严肃校勘，我们很可能还需要：

- page number
- crop coordinates
- source image id
- revision history

这部分建议在 `dataset-tools` 先做内部字段预留，再视情况推动 `Jianzi-Code v2`。

### 3. 对齐步骤会是最难点

从图像对象到语义对象的对齐，不会是纯规则，也不会是纯模型。

它大概率会是：

- 规则初配
- 候选打分
- 人工修订
- 回流更新

所以这里要从一开始就按“半自动系统”来设计。

## 我建议的实施顺序

### Phase 0

先做最小骨架：

- manifest 数据模型
- ingest / normalize / validate 三条命令
- 一个最小 workspace 目录

### Phase 1

做外部导入器：

- `Guqin-Dataset` adapter
- `guqincomposer` adapter
- 图像页导入器

### Phase 2

做最小对齐链路：

- 页级对象
- glyph 级对象
- `Jianzi-Code document` 导出

### Phase 3

做训练集导出：

- detection
- classification
- review reports

## 结论

第二部分不应该做成“几个处理脚本的集合”。

它应该做成一个以工作区清单为中心、以对齐和可追溯为核心的数据流水线系统。

我推荐的方向是：

`Manifest-First + Staged Pipeline + Adapter-based Imports/Exports + Human-in-the-loop Alignment`

这条路的好处是，它既能承接你现在已经找到的古琴数据资源，也能为后面的 OCR 引擎、人工校对平台和标准导出提供稳定底座。

## 参考实现

- [neuralfirings/guqincomposer](https://github.com/neuralfirings/guqincomposer)
- [lukewys/Guqin-Dataset](https://github.com/lukewys/Guqin-Dataset)
- [yufenhuang/Guqin-dataset](https://github.com/yufenhuang/Guqin-dataset)
- [OCR-D/core](https://github.com/OCR-D/core)
- [UB-Mannheim/escriptorium](https://github.com/UB-Mannheim/escriptorium)
- [mittagessen/kraken](https://github.com/mittagessen/kraken)
- [open-edge-platform/datumaro](https://github.com/open-edge-platform/datumaro)
- [cvat-ai/cvat](https://github.com/cvat-ai/cvat)
- [iterative/dvc](https://github.com/iterative/dvc)
- [OMR-Research/muscima-pp](https://github.com/OMR-Research/muscima-pp)
- [Audiveris/audiveris](https://github.com/Audiveris/audiveris)
