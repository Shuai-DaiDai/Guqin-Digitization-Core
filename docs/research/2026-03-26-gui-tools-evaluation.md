# gui-tools Evaluation for Guqin-Digitization-Core Dataset Tools

## Scope of this evaluation

This note evaluates whether [`SuziAI/gui-tools`](https://github.com/SuziAI/gui-tools) can serve as the annotation front-end for our second module, `apps/dataset-tools`, in `Guqin-Digitization-Core`.

The evaluation is based only on the repository’s own files and official documentation referenced from the repository:

- `README.md`
- `requirements.txt`
- `json_schema_jianzipu.json`
- `extract_dataset_from_corpus.py`
- `readme_files/extract_dataset_from_corpus.md`
- `annotation_editor.py`
- `src/plugins/jianzipu.py`
- `src/plugins/jianzipu/gui_config.json`
- `src/auxiliary.py`
- `src/programstate.py`

## Short answer

`gui-tools` is a serious and useful piece of software. It is not just a demo. It already supports image annotation, segmentation boxes, notation annotation, JSON schema validation, and dataset export.

However, it does **not** line up cleanly with our long-term source-of-truth model.

It fits best as a **temporary annotation front-end** for cold-start data creation, not as the core data system of our project.

## 1. Supported notation scope

The repository README says the tool supports `suzipu`, `lülüpu`, and `jianzipu`. The annotation tool is explicitly presented as a way to annotate images with segmentation boxes and notation information for OMR projects.

For our purposes, the important part is that the repository includes a dedicated `jianzipu` plugin and a separate `json_schema_jianzipu.json`.

That plugin is not generic. It contains jianzipu-specific symbol assets and GUI configuration for:

- full jianzipu structures
- left-hand annotations
- string-number annotations
- right-hand plucks
- technique symbols

This is a strong sign that the tool genuinely covers jianzipu and is not merely “notation-agnostic”.

## 2. Data model and schema fit

The strongest positive point is that `gui-tools` does have a real schema.

The jianzipu schema models a piece as:

- top-level piece metadata like `version`, `notation_type`, `composer`, `images`
- an ordered `content` list
- box-level annotations with `box_type`
- separate `text_coordinates` and `notation_coordinates`
- structured `notation_content`

For jianzipu, `notation_content` supports three forms:

- `LEFT_HAND`
- `STRING_NUMBER`
- `FULL_JIANZIPU`

The `FULL_JIANZIPU` case is especially relevant to us. It uses a tree structure with ideographic description operators such as `⿰`, `⿱`, `⿲`, `⿳`, `⿸`, `⿺`, and `⿹`, plus child nodes. This means the tool already thinks in terms of compositional structure rather than flat labels.

That is close to our goals, but not the same as `Jianzi-Code`.

Main mismatch:

- `gui-tools` is box-first
- `Jianzi-Code` is event-first

`gui-tools` stores annotated image regions in reading order. Our design needs stable page, glyph, alignment, and semantic event records that can survive import, export, re-segmentation, and review. `gui-tools` does not appear to provide those IDs or that provenance layer.

## 3. Image annotation workflow

The repository provides a desktop annotation application via `annotation_editor.py`.

From the code and README, the workflow is roughly:

1. load image files
2. create or refine boxes
3. mark box types
4. annotate notation and text
5. save to the repository’s JSON format
6. export cropped OMR datasets with `extract_dataset_from_corpus.py`

There are some genuinely useful features here:

- box creation and editing
- ordering support
- line-break handling
- notation-specific annotation widgets
- a segmentation assistant based on HRCenterNet
- optional OCR/text assistance through Tesseract

This is enough to make the tool practical for creating a first annotated corpus.

But it is still a desktop app centered on manual editing. It is not a workflow server, task queue, or collaborative review system.

## 4. Export format

The export script is helpful but limited.

`extract_dataset_from_corpus.py` walks through JSON corpus files and exports:

- cropped notation images
- cropped text images
- `dataset.json` files with image path, type, annotation, and a few metadata fields

This is good for bootstrapping OMR datasets.

But the export format is still custom and narrow:

- it is not COCO
- it is not YOLO
- it is not our `Jianzi-Code`
- it does not preserve the richer review/provenance information we want in dataset-tools

In other words, the tool can help us create raw supervised data, but we would still need our own import layer to convert that output into our internal workspace.

## 5. Platform and runtime constraints

This is the biggest operational warning.

The README states:

- Windows is currently not supported because of conflicts between `tkinter` and OpenCV
- macOS also “seems to be not supported”
- the application was developed and tested on Ubuntu 24.04.3

It also requires:

- Python 3.10 with `tkinter`
- OpenCV
- Torch and Torchvision
- Pytesseract
- a downloaded `HRCenterNet.pth.tar` weight file
- a Chinese Tesseract traineddata file for the “Intelligent Fill” function

That is a real dependency stack, not a lightweight tool.

For a research workstation on Ubuntu, this is manageable.
For a mixed team using laptops across platforms, this is a serious adoption friction point.

## 6. Dependency and maintenance risks

The tool has three practical risks for us:

### A. Environment fragility

It depends on desktop GUI behavior, OpenCV, Torch, Tesseract, and external weights.

That creates more setup risk than a simple browser-based annotation front-end.

### B. Custom internal format

Its JSON format is coherent, but it is its own world.

If we adopt the tool, we must treat its JSON as an import format, not as our source of truth.

### C. Partial domain fit

It supports jianzipu, but it was built for a broader family of ancient Chinese notation projects, not specifically for a manifest-first guqin digitization workflow with `Jianzi-Code`, cross-source provenance, and alignment records.

## 7. Integration cost with our manifest-first dataset-tools design

Integration is very possible, but not cheap enough to call “plug-and-play”.

What we would need to build around it:

- an importer from `gui-tools` JSON into our internal manifest/page/glyph/alignment records
- a mapping from `FULL_JIANZIPU` tree annotations into our visual layer
- a mapping from `LEFT_HAND` / `STRING_NUMBER` annotations into our physical layer
- stable IDs and provenance records on top of their box ordering
- a clean export path from our dataset-tools workspace back into training formats

What we would **not** need to build immediately if we adopt it temporarily:

- our own first annotation GUI from scratch
- our own first box editing workflow from scratch
- our own first jianzipu symbol picker from scratch

So the integration cost is real, but it is still lower than building a serious annotation front-end from zero.

## 8. Best fit by module

### For module 2: `apps/dataset-tools`

Good fit as:

- a temporary corpus annotation front-end
- a way to generate initial box-level and notation-level data
- a source format that our import pipeline can translate

Bad fit as:

- the long-term source-of-truth store
- the only workflow system
- the canonical data model for Guqin-Digitization-Core

### For module 3: `apps/ocr-engine`

Indirectly useful because it can generate initial annotated datasets and crop-level supervision, but it is not the OCR engine itself.

## 9. Decision

**Recommendation: adopt temporarily**

Reasons:

1. It already supports jianzipu in a real way.
2. It already does the most painful early UI work: boxes, annotations, ordering, and export.
3. It is good enough to help us cold-start an annotated corpus faster than building our own GUI.
4. But its schema, platform support, and export model do not match our long-term architecture closely enough to make it our permanent front-end or source of truth.

## 10. Practical meaning of “adopt temporarily”

If we use it, we should do it with strict boundaries:

- use `gui-tools` only to create or refine annotations
- immediately import its JSON into our own dataset-tools workspace
- keep `Jianzi-Code` and our manifest records as the project truth
- avoid coupling the rest of the pipeline directly to `gui-tools` internals

That way we get its speed advantage without locking the whole project into its constraints.
