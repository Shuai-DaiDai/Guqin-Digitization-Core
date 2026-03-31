# Real-Example Review

I pressure-tested the `Jianzi-Code` spec against the three reference repositories:

- `guqincomposer`
- `Guqin-Dataset`
- `Guqin-dataset`

The examples added in this pass are conservative on purpose. They model concrete patterns already visible in those repositories, without trying to invent a richer notation than the sources justify.

## Main Gaps Found

### 1. Chords and simultaneous notes are not fully modeled

`guqincomposer` can express multiple notes at once, including combined fingering and layered notation. `Guqin-Dataset` also contains music transcription workflows that are not strictly one-note-at-a-time in the human sense.

Current gap:

- `Jianzi-Code v1` still treats the core event as a single note event.
- There is no first-class group object for a chord, grace cluster, or multi-note gesture.

Why it matters:

- This is fine for a first pass, but it is not enough for every real score pattern.
- A future v2 likely needs an event group or simultaneity wrapper.

### 2. Tuning context is still too implicit

The dataset repositories make it clear that tuning is essential to interpretation, but a note event does not always carry enough local context by itself.

Current gap:

- Tuning lives at the document level.
- A note event does not reference which tuning assumption was used when it was interpreted.

Why it matters:

- The same visual pattern can map differently under different tunings.
- This is especially important when the spec is used for cross-score comparison.

### 3. Ornament vocabulary is incomplete

The shorthand patterns in `guqincomposer` show more than simple pluck and stop behavior. Slides, grace timing, vibrato-like movements, and combined hand actions appear in real scores.

Current gap:

- `ornaments` helps, but the vocabulary is still coarse.
- Some real patterns are better thought of as motions with start/end timing rather than single labels.

Why it matters:

- A future editing or validation tool will need more precise motion semantics.
- Right now the spec can store the idea, but not always the exact shape of the idea.

### 4. Source provenance is not detailed enough

The dataset repositories include score titles, editions, performers, transcribers, and split/segment behavior. That is useful, but still not enough for line-level provenance.

Current gap:

- We can record the source edition and repository.
- We do not yet have a standard place for page number, scan ID, crop box, or staff/location metadata.

Why it matters:

- OCR and editorial workflows need traceability back to the image.
- Without this, it is harder to explain why a given interpretation was chosen.

### 5. Numbered-notation bridge is intentionally narrow

The `Guqin-Dataset` lineage is built around simplified numbered notation and MusicXML export.

Current gap:

- The bridge only covers one pitch at a time, with simple octave and accidental flags.
- It does not fully describe rests, grouped rhythms, or multiple simultaneous pitches.

Why it matters:

- This is enough for the first bridge layer.
- It is not enough to represent every transcription feature found in the dataset pipeline.

## Practical Conclusion

The current spec is good enough as a shared foundation for:

- OCR alignment
- human correction
- single-note semantic tagging
- basic MusicXML / MIDI export

It is not yet enough to be the final word on every guqin notation edge case.

That is acceptable at this stage. The right next step is to keep `v1` conservative, build real tooling on top of it, and let the hardest edge cases drive the shape of `v2` instead of overfitting the first release.
