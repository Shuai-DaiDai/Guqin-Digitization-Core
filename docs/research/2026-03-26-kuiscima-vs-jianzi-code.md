# KuiSCIMA vs. Jianzi-Code

## Scope

This note compares the official KuiSCIMA repository and the KuiSCIMA v2.0 paper with the current `Jianzi-Code` specification in this repository.

Sources used:

- KuiSCIMA repository: <https://github.com/SuziAI/KuiSCIMA>
- gui-tools repository: <https://github.com/SuziAI/gui-tools>
- KuiSCIMA v2.0 paper: <https://arxiv.org/abs/2507.18741>

## Short answer

KuiSCIMA and `Jianzi-Code` are close in one very important sense: both try to preserve notation structure instead of collapsing everything immediately into modern staff notation.

But they solve different layers of the problem.

- KuiSCIMA is strongest as an image-linked, notation-near corpus format for historical Chinese music notation.
- `Jianzi-Code` is strongest as a normalized semantic interchange format for guqin notation, especially once performance meaning and acoustic output matter.

So the relationship is not “replace ours with KuiSCIMA”.

The right relationship is:

- reuse KuiSCIMA ideas where it is stronger,
- adapt selected structures into our pipeline,
- keep `Jianzi-Code` custom where our goals are different.

## What object levels KuiSCIMA models

From the official repository README, KuiSCIMA is described as “a digital machine-readable dataset of both purely symbolic and OMR-oriented representations” and its JSON format is “semantically close to the original notation” with “symbol-level annotations of the textual and musical contents with their positions.”

From the official `json_schema_jianzipu.json` in `gui-tools`, the modeled levels are roughly:

1. **Piece level**
   - version
   - notation type
   - composer
   - mode properties
   - ordered image list

2. **Box / region level**
   - `box_type` such as `Title`, `Mode`, `Preface`, `Music`, `Lyrics`, `Unmarked`
   - image coordinates for text and notation
   - textual content
   - notation content

3. **Notation content level**
   - `LEFT_HAND`
   - `STRING_NUMBER`
   - `FULL_JIANZIPU`

4. **Recursive glyph structure level**
   - `FULL_JIANZIPU` is stored as a decomposition tree
   - inner nodes use composition operators such as `⿰`, `⿱`, `⿲`, `⿳`, `⿸`, `⿺`, `⿹`
   - leaf nodes store actual notation symbols

This means KuiSCIMA is not just a folder of cropped images. It has a real notation-aware object model.

## How image regions map to notation semantics in KuiSCIMA

KuiSCIMA maps image regions to semantics through annotated boxes.

The important design choice is that the box is the bridge between image space and notation meaning:

- a box has image coordinates,
- a box has a semantic role (`Title`, `Lyrics`, `Music`, etc.),
- a music box can carry notation content,
- jianzipu notation content can be represented as a recursive decomposition tree.

This is very useful for OMR and corpus curation because it keeps:

- where something is on the page,
- what type of thing it is,
- and what notation it represents

in one linked structure.

That is stronger than our current `Jianzi-Code` on page-layout linkage.

## Whether jianzipu is directly represented

Yes, but in a specific way.

The repository README says KuiSCIMA v2.0 includes “all 109 pieces ... including lülüpu, and jianzipu musical notations.”

In the official `gui-tools` jianzipu schema, jianzipu is directly represented under `notation_type = "Jianzipu"` and `notation_content` can contain:

- `LEFT_HAND`
- `STRING_NUMBER`
- `FULL_JIANZIPU`

The strongest part is `FULL_JIANZIPU`, which stores the notation as a recursive decomposition tree rather than as a single flat label.

So yes, jianzipu is directly represented.

But it is represented as a notation-structure object, not yet as a full guqin semantic event with performance and acoustic normalization.

## How this compares to Jianzi-Code

Our current `Jianzi-Code` is built around:

1. **Document level**
   - piece metadata
   - tuning
   - sections
   - measures
   - event order

2. **Note event level**
   - `visual`
   - `physical`
   - `acoustic`

3. **Normalized semantic meaning**
   - note type (`open`, `stopped`, `harmonic`)
   - string
   - hui/fraction position
   - right hand
   - left hand
   - ornaments
   - pitch / MIDI / duration / MusicXML bridge

This means `Jianzi-Code` currently does **more semantic normalization** than KuiSCIMA, but does **less page-linked structural modeling** than KuiSCIMA.

## Compact mapping table

| KuiSCIMA concept | Current role in KuiSCIMA | Closest place in Jianzi-Code | Reuse status | Notes |
|---|---|---|---|---|
| Piece object | top-level corpus/piece metadata | `document.piece` | `adapt` | Strong overlap, but our piece object is guqin-centered and includes tuning explicitly |
| Ordered image list | page linkage | no first-class equivalent yet | `adapt` | Important for dataset-tools, not yet central in `Jianzi-Code` |
| Content box | page region with semantic role and coordinates | no first-class equivalent yet | `adapt` | Better fit for dataset-tools or a future image-linked extension |
| `box_type` | distinguishes title/preface/music/lyrics/etc. | partially `sections` / future provenance layer | `adapt` | Useful for page parsing; not core to our current note-event spec |
| Text coordinates | image linkage for text | none | `adapt` | Strong candidate for pipeline-level records, not core spec v1 |
| Notation coordinates | image linkage for notation | none | `adapt` | Same as above |
| `LEFT_HAND` | notation content subtype | `physical.left_hand` | `adapt` | Our model is richer and more normalized |
| `STRING_NUMBER` | notation content subtype | `physical.string` | `reuse directly` | Straight conceptual match |
| `FULL_JIANZIPU` tree | recursive glyph decomposition | `visual` | `adapt` | Better than our fixed 4-slot model for some complex compositions |
| Recursive IDS operators | explicit composition grammar | none directly | `adapt` | Strong candidate for a future `visual_tree` extension |
| Symbol-level annotation with position | OMR-friendly object | none directly | `adapt` | Belongs in dataset-tools and possibly a future image-linked layer |
| Performance semantics | limited / notation-near | `physical` | `keep custom` | Our guqin-specific performance layer is a core differentiator |
| Acoustic normalization | not the main focus | `acoustic` | `keep custom` | KuiSCIMA is not a drop-in replacement here |
| Measure/event sequencing | not the main organizing principle | `sections -> measures -> events` | `keep custom` | Needed for export and downstream guqin workflows |

## What can be reused

### Reuse directly

These are safe direct ideas or concepts:

- the distinction between piece-level data and lower image-linked annotation objects
- explicit `STRING_NUMBER` semantics
- the idea that image-linked annotation should remain semantically close to the original notation instead of flattening too early

### Adapt

These are valuable, but should be adapted rather than copied:

- image boxes with semantic roles
- coordinate-linked notation objects
- the recursive `FULL_JIANZIPU` decomposition tree
- the split between purely symbolic editing and image-linked annotation workflows

The biggest concrete lesson is this:

our current `visual.components` model is easy to use, but KuiSCIMA’s recursive tree is more expressive for complex notation composition.

So if we ever extend `Jianzi-Code`, the clean move is probably **not** to replace `visual.components`, but to add an optional richer decomposition field such as `visual_tree` or `visual.decomposition_tree`.

## Where Jianzi-Code must stay different

There are several places where we should keep our own model rather than bending to KuiSCIMA:

1. **Three-layer design**
   - `visual`
   - `physical`
   - `acoustic`

   This is central to our project and is broader than KuiSCIMA’s current notation-near representation.

2. **Guqin-specific performance semantics**
   - note type
   - hui/fraction
   - right-hand technique
   - left-hand technique
   - ornaments

   These are exactly the kinds of normalized meanings we need and should not give up.

3. **Acoustic bridge**
   - pitch name
   - MIDI
   - duration
   - MusicXML bridge

   KuiSCIMA is useful for recognition and structured notation storage, but it is not our target interchange format for sound-level output.

4. **Document sequencing**
   - sections
   - measures
   - events

   This is important for downstream guqin export, alignment, and playback workflows.

## Practical recommendation

### Reuse directly

- piece-level corpus thinking
- notation-near annotation philosophy
- string number concept

### Adapt

- image-box semantics
- coordinate-linked notation annotations
- recursive jianzipu decomposition tree
- split between annotation tool and symbolic editor

### Keep custom

- `Jianzi-Code` document/event hierarchy
- `visual` / `physical` / `acoustic` three-layer contract
- guqin-specific performance semantics
- acoustic normalization and export bridge

## Final judgment

KuiSCIMA is highly compatible with our **second module** as a reference for dataset representation and annotation workflow.

KuiSCIMA is only partially compatible with our **core `Jianzi-Code` spec**.

The best move is:

- keep `Jianzi-Code` as the canonical semantic format,
- let dataset-tools learn from KuiSCIMA’s image-linked object design,
- and consider adding a future optional recursive visual decomposition field inspired by `FULL_JIANZIPU`.

In short:

- **reuse directly**: a small part
- **adapt**: a large part
- **keep custom**: the semantic heart of `Jianzi-Code`
