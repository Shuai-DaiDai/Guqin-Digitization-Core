# Guqin Digitization Core

[中文](#中文) | [English](#english)

---

## 中文

`Guqin-Digitization-Core` 是一个面向古琴减字谱数字化的开源基础设施项目。

这个项目要解决的，不只是“把谱页扫进电脑”，而是把古琴减字谱真正变成机器可以理解、检索、校对、训练和转换的数据。我们希望最终建立一条完整链路：

1. 从古籍影印页中识别减字与相关记号  
2. 把识别结果整理成统一、可验证的结构化标准  
3. 逐步连接到演奏语义、MusicXML、MIDI 等现代输出形式

它的价值不只在古琴领域。古琴减字谱本身就是一种复杂的合体字记谱系统，所以这项工作也在为中国古代文献中的复杂字形、异体字和特殊版式数字化提供方法。

### 当前仓库包含什么

- `packages/jianzi-code-spec`
  `Jianzi-Code` 核心规范。这里定义了结构化数据格式、字段说明、示例和相关文档。

- `apps/dataset-tools`
  数据清洗与对齐工具。这里负责把 OCR 结果、人工校对结果和结构化草稿串成可反复迭代的数据流水线。

- `apps/ocr-engine`
  视觉识别引擎。这里负责页图处理、框选候选、训练数据导出，以及后续真正的检测与识别模型。

### 项目现在到了哪一步

目前已经完成了第一批可工作的基础设施：

- `Jianzi-Code` 规范草案已经建立
- OCR 结果已经能进入统一的数据工作区
- 已经有可用的人工校对页面
- 人工校对结果已经能正式回灌到数据主流程
- 已经能导出下一轮训练所需的数据

换句话说，这个仓库现在已经不是一个空架子，而是一个能持续迭代的早期工作系统。

### 仓库结构

```text
Guqin-Digitization-Core/
├── packages/
│   └── jianzi-code-spec/
├── apps/
│   ├── dataset-tools/
│   └── ocr-engine/
├── docs/
├── scripts/
└── qupu/
```

### 快速开始

#### Node / Workspace

```bash
pnpm install
```

#### Python

建议分别为 Python 应用准备独立环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/dataset-tools/requirements.txt
pip install -r apps/ocr-engine/requirements.txt
```

### 设计原则

- 先把标准定义清楚，再去训练模型
- 视觉结果、人工校对、结构化草稿要能相互回流
- 每轮识别和训练都要能比较、复现和追踪
- 大文件、原始 PDF、模型权重不直接进入 Git

### 后续重点

- 继续积累高价值人工校对数据
- 训练并接入真假框过滤器与更稳的检测模型
- 完善漏框流程与框间关系表达
- 推进从 OCR 结果到更可靠 `Jianzi-Code` 草稿的映射
- 逐步打通到 MusicXML / MIDI

如果你关心古琴、古籍数字化、OCR、结构化标注，或者想参与这类长期基础工程，欢迎一起完善这个项目。

---

## English

`Guqin-Digitization-Core` is an open-source infrastructure project for digitizing guqin jianzipu notation.

The goal is not just to scan old score pages. The real goal is to turn guqin notation into data that machines can read, validate, search, review, train on, and eventually convert into modern outputs.

In practical terms, the project aims to build an end-to-end pipeline:

1. Detect jianzipu symbols and related notation marks from scanned historical pages  
2. Normalize those results into a unified, machine-readable standard  
3. Connect them to performance meaning and modern formats such as MusicXML and MIDI

This work matters beyond guqin itself. Jianzipu is a complex composite notation system, so the methods developed here can also help with the broader digitization of historical Chinese documents that contain unusual glyphs, variant forms, and difficult layouts.

### What is in this repository

- `packages/jianzi-code-spec`
  The core `Jianzi-Code` specification. This package defines the structured data format, examples, and documentation.

- `apps/dataset-tools`
  The data workflow layer. This app connects OCR results, human review, and structured drafts into one repeatable pipeline.

- `apps/ocr-engine`
  The vision layer. This app handles page processing, candidate boxes, training-data export, and the path toward real detection and recognition models.

### Current project status

The repository already contains a usable early system:

- a working draft of the `Jianzi-Code` specification
- a shared data workspace format
- a human review interface
- a review-to-pipeline feedback loop
- training-data export for the next model iteration

So this is no longer just a placeholder repo. It is already an operational early-stage foundation.

### Repository layout

```text
Guqin-Digitization-Core/
├── packages/
│   └── jianzi-code-spec/
├── apps/
│   ├── dataset-tools/
│   └── ocr-engine/
├── docs/
├── scripts/
└── qupu/
```

### Quick start

#### Node / Workspace

```bash
pnpm install
```

#### Python

It is recommended to use isolated environments for the Python apps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/dataset-tools/requirements.txt
pip install -r apps/ocr-engine/requirements.txt
```

### Design principles

- define the data contract before scaling the models
- keep OCR output, human review, and structured drafts connected
- make every model or dataset iteration comparable and traceable
- keep large assets, raw PDFs, and weights out of Git

### What comes next

- collect more high-value reviewed pages
- train and integrate a box filter and stronger detection models
- improve missing-box handling and symbol relationship modeling
- strengthen the mapping from OCR output to reliable `Jianzi-Code` drafts
- eventually connect the pipeline to MusicXML and MIDI

If you care about guqin, document digitization, OCR, or long-term research infrastructure, this project is designed to be built in the open and improved over time.
