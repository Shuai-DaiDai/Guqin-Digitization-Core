# Cold-Start Data Audit: guqinMM, KuiSCIMA, and gui-tools

## Scope

This note audits whether the **data assets** in or around the following projects can help us cold-start rough labeled data for:

- **Module 2**: dataset-tools
- **Module 3**: ocr-engine

The focus is deliberately practical:

- What data appears to be **actually present**
- What is only **described**
- Whether image pages, boxes, labels, notation semantics, and splits are available
- Whether the assets look directly usable, usable after conversion, only useful as reference, or not available

## Short Answer

- **KuiSCIMA** is the strongest cold-start candidate, but it still needs conversion and careful scope control.
- **gui-tools** is very useful as a **tooling and format reference**, but it is not itself a dataset source.
- **guqinMM** is promising as a research direction, but based on the official repo landing materials it is not yet a dependable cold-start data source.

## What I checked

### Official repos

- [wds-seu/guqinMM](https://github.com/wds-seu/guqinMM)
- [SuziAI/KuiSCIMA](https://github.com/SuziAI/KuiSCIMA)
- [SuziAI/gui-tools](https://github.com/SuziAI/gui-tools)

### Official linked documents

- [KuiSCIMA v2.0 paper](https://arxiv.org/abs/2507.18741)
- [Recognition of Radicals of Guqin Music Notation by YOLOs](https://link.springer.com/chapter/10.1007/978-981-95-3141-7_11)

## 1. guqinMM

### What appears to be present

From the official README:

- It claims to have a `datasets` folder for a published jianzipu dataset.
- It says the dataset is an **image-notation dataset**.
- It says each image has a **decomposed tree notation**.
- It says the data comes from **Wushen scores** and **gui-tools** annotations.
- It frames the project as both **Jianzipu OCR** and **music generation**.

Relevant official statements:

- README says: “We have published a jianzipu dataset in `datasets` folder.”
- README says the dataset includes “basic jianzipu finger technique collection and a jianzi character collection.”
- README says: “Each image has its own decomposed tree notation.”

### What is directly visible

On the current repo landing page, the visible top-level tree shows:

- `guqin_audio`
- `guqin_jzp`
- `images`
- `JZPannotation.drawio`
- `README.md`

The landing page does **not** visibly show a top-level `datasets` folder, even though the README says such a folder exists.

### What is missing or unclear

From the official materials I checked, I could not verify:

- a browsable released image corpus
- explicit segmentation boxes
- train / val / test split files
- a stable exported annotation schema
- a ready-to-download corpus index

The README also says the JSON-string tool for Jianzi character description is “in developing, to be continued,” which suggests the representation layer is still incomplete.

### Cold-start value

For **Module 2**:

- Good as a clue about desired objects: image -> annotation -> decomposed tree
- Not yet dependable as a primary ingestion source

For **Module 3**:

- Good as a task-definition reference for guqin-specific OCR
- Not yet strong enough, from the official materials alone, to count as a ready-made training corpus

### Verdict

**Ranking: only reference**

Reason:

- It clearly points in the right direction.
- But the actual released, directly accessible data assets are too unclear from the official repo materials to treat it as dependable cold-start data.

## 2. KuiSCIMA

### What appears to be present

This is the strongest case.

From the official README and repo tree:

- The repository contains a top-level `KuiSCIMA` folder.
- It also contains an `artificial_suzipu_dataset` folder.
- The README describes the dataset as both **purely symbolic** and **OMR-oriented**.
- The README says the JSON format is semantically close to the original notation and includes **symbol-level annotations with positions**.
- The README says v2.0 contains **all 109 pieces** of *Baishidaoren Gequ*, including **suzipu**, **lülüpu**, and **jianzipu**.

Relevant official statements:

- README: “The JSON format employed in this dataset is semantically close to the original notation and features symbol-level annotations of the textual and musical contents with their positions.”
- README: v2.0 contains all 109 pieces, including jianzipu notation.
- README: the annotation tool for viewing, editing, and exporting is `gui-tools`.

### What data structure it seems to provide

Based on the official README:

- image-linked representation
- symbol-level positional information
- textual and musical contents
- machine-readable JSON
- multiple notation systems

This is exactly the kind of structure that can be converted into:

- page records
- segmentation boxes
- symbol labels
- notation semantics

### What is still unclear

From the public materials I checked, I did **not** verify ready-made split files such as:

- `train.json`
- `val.json`
- `test.json`

The paper says the evaluation uses **leave-one-edition-out cross-validation** across five editions, which is useful for us as a protocol, but that is not the same thing as shipping ready-to-run split files in the repo.

### Artificial dataset

The README also says the repo includes `artificial_suzipu_dataset` with:

- 36 handwritten instances
- all 77 suzipu classes

But the README also says this artificial data was **not used**, because training with it worsened results overall.

That makes it weak as a direct cold-start asset for our goals.

### Cold-start value

For **Module 2**:

- Very useful as a real example of image-linked, symbol-level annotated Chinese historical notation data
- Useful for designing import adapters, internal workspace objects, and validation checks

For **Module 3**:

- Useful for bootstrapping OCR experiments and transfer learning ideas
- Especially useful for learning how to structure character recognition under scarce, imbalanced conditions

### Important limitation

KuiSCIMA is not a guqin corpus in the full sense we need. It is a high-quality historical Chinese notation corpus that includes jianzipu, but it is centered on *Baishidaoren Gequ*, not on the broader guqin scorebook world we care about.

So it helps a lot, but it does not remove the need for our own guqin-target data.

### Verdict

**Ranking: usable with conversion**

Reason:

- The data appears to be genuinely present and machine-readable.
- It contains positional symbol annotations and notation semantics.
- But it needs conversion into our internal workspace and `Jianzi-Code` world.
- Its domain only partially overlaps with our true target domain.

## 3. gui-tools

### What appears to be present

This repository is primarily a **tooling repo**, not a corpus repo.

From the official README and visible file tree:

- JSON schemas are included:
  - `json_schema.json`
  - `json_schema_suzipu.json`
  - `json_schema_lvlvpu.json`
  - `json_schema_jianzipu.json`
- There is an annotation tool:
  - `annotation_editor.py`
- There is an export script:
  - `extract_dataset_from_corpus.py`
- There is also a notation editor for symbolic work

### What the schema and export script show

From the official `json_schema_jianzipu.json`:

- a piece may reference one or more `images`
- `content` contains annotated boxes
- each box can carry:
  - `box_type`
  - `text_coordinates`
  - `text_content`
  - `notation_coordinates`
  - `notation_content`

The jianzipu schema also supports notation content types such as:

- `LEFT_HAND`
- `STRING_NUMBER`
- `FULL_JIANZIPU`

That is highly relevant for our needs.

From the official export script:

- the script extracts cropped images from annotated boxes
- it creates dataset JSONs for text and music
- it writes image paths and annotations to exported JSON files

So the tool definitely supports the creation of OMR-ready assets.

### What is not present

The repo does **not** itself present a corpus of finished annotated pages as a data asset.

What it gives us is:

- a schema
- a GUI
- an export path

What it does **not** directly give us is:

- a sizeable released labeled corpus
- train / val / test splits
- a ready-made cold-start dataset for guqin

### Cold-start value

For **Module 2**:

- Very useful for studying a real annotation/export workflow
- Potentially useful as a temporary annotation front-end
- Useful for understanding how an image-linked corpus can be organized

For **Module 3**:

- Indirectly useful, because it can produce crops and labels
- Not itself a cold-start dataset

### Platform caveat

The official README says the tool was developed and tested on Ubuntu 24.04.3, and that Windows and macOS are currently not supported in practice due to `tkinter` / OpenCV issues.

That matters operationally, but it does not change the data audit: this is still mainly a tool, not a dataset source.

### Verdict

**Ranking: only reference**

Reason:

- The repo is excellent as a schema/tooling reference.
- But as a data asset for cold-start, it does not ship the kind of labeled corpus we need.

## 4. The YOLO radicals paper

This is not one of the three repos, but it matters because it is the most explicit official description of a guqin-specific labeled set in the materials checked.

From the paper:

- The authors created a dataset of radicals from six versions of **Chun Xiao Yin**.
- It contains **20 radical classes** from **26 types of characters**.
- It has **1,176 images** in total.
- It uses **943** images for training and **233** for evaluation.

This is important evidence that guqin-specific radical-level data can be built and can work for YOLO-style detection/classification.

However:

- the dataset is described in the paper
- it is not presented as a directly downloadable repo asset in the materials checked
- it is narrow in scope, centered on one piece and a radical task

### Verdict

**Ranking: unavailable**

Reason:

- It is strong proof-of-concept evidence.
- It is not a directly accessible cold-start data asset from the official materials checked.

## 5. Practical ranking

### Immediately usable

- **None**

I did not find any of the checked official materials to be a ready, directly plug-in cold-start dataset for our full Module 2 / Module 3 needs.

### Usable with conversion

- **KuiSCIMA**

Best current candidate for cold-start rough labels, especially for:

- image-linked annotation structure
- symbol-level boxes
- notation semantics
- OCR experiment bootstrapping

### Only reference

- **guqinMM**
- **gui-tools**

Both are valuable, but mainly as:

- workflow references
- schema references
- annotation/export references
- task-decomposition references

### Unavailable

- **The radicals dataset described in the YOLO paper**, as a directly accessible asset from the official materials checked

## 6. What this means for us

For **Module 2**:

- We should treat **KuiSCIMA** as the best external seed for import/conversion experiments.
- We should treat **gui-tools** as a likely schema/tooling reference, maybe even a temporary annotation front-end.
- We should not assume **guqinMM** gives us a ready ingestible corpus.

For **Module 3**:

- We should treat **KuiSCIMA** as useful cold-start supervision and evaluation inspiration.
- We should treat **guqinMM** as a guqin-specific research direction, not a finished data foundation.
- We should treat the **YOLO radicals paper** as evidence that radical-level modeling is promising, but not as an immediately obtainable dataset.

## Bottom line

If the question is:

“Can these projects give us cold-start rough labeled data?”

the answer is:

- **KuiSCIMA: yes, with conversion**
- **gui-tools: no dataset, but useful tool/format reference**
- **guqinMM: promising, but not dependable as released data**

So we still need our own guqin-target corpus buildout, but we do **not** need to start blind.
