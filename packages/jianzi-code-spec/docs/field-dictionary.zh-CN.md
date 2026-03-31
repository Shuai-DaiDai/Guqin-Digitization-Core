# Jianzi-Code 字段词典

这份词典用于统一 `Jianzi-Code` 里的关键术语，方便古琴、打谱、OCR 和工程人员共同沟通。

## 使用说明

- 这里的解释优先面向“怎么理解这字段代表什么”，不是面向“代码怎么写”。
- 当前词典按我们已经定义的两个层级来整理：`Jianzi-Code Note Event` 和 `Jianzi-Code Document`。
- 如果未来字段扩展，优先先改这份词典，再改示例和工具文档。

## 1. 音符事件层

### `id`

每个音符事件的唯一编号。

它的作用是让一条记录在整首曲子里可以被稳定指认，比如校对意见、错误回溯、版本比较都要靠它。

### `visual`

视觉层。记录这个减字“长什么样”。

适合给 OCR、前端展示、人工校对使用。

### `visual.char_text`

这个减字的完整汉字兜底写法。

当字形部件还没有完全拆开，或者 OCR 需要一个总览文本时，用它兜底。

### `visual.layout`

字形结构类型。

它描述的是减字的整体布局方式，比如上下结构、左右结构、包围结构等。它不是书法风格，而是帮助系统知道部件如何摆放。

### `visual.components`

视觉部件槽位。

它把一个减字拆成几个固定位置，方便机器和人工对照。当前固定为四个槽位：

- `top_left`
- `top_right`
- `bottom_inner`
- `bottom_outer`

这些槽位不是要求每个字都必须填满，而是给识别和排版一个统一框架。

### `physical`

物理动作层。记录“怎么弹”。

这一层是古琴知识最核心的部分，因为它承载了弦、徽位、指法和按法这些演奏信息。

### `physical.note_type`

音类。

当前有三种基础值：

- `open`：散音，空弦发声
- `stopped`：按音，左手按弦后发声
- `harmonic`：泛音

### `physical.string`

弦号。

范围是 `1` 到 `7`，表示古琴第几弦。

### `physical.position`

徽位位置。

它描述音在琴弦上的位置，由两个部分组成：

- `hui`：第几个徽
- `fraction`：徽与徽之间的细分位置

如果是散音，这一项可以为空；如果是按音或泛音，一般需要更精确的位置信息。

### `physical.position.hui`

徽位编号。

表示落在第几个徽附近。当前支持 `1` 到 `13`，也允许为空。

### `physical.position.fraction`

徽位之间的细分位置。

这是一个从 `0` 到 `1` 之间的数，表示在两个徽之间的相对位置，也允许为空。

### `physical.right_hand`

右手动作。

它描述拨弦的手指和技法。

### `physical.right_hand.finger`

右手用的手指。

当前值包括 `thumb`、`index`、`middle`、`ring`、`little`、`unknown`。

### `physical.right_hand.technique`

右手技法。

例如 `gou`、`mo`、`tiao`、`ti` 等。

这字段描述“用什么动作发声”，不是只写哪个手指碰到了哪根弦。

### `physical.left_hand`

左手动作。

它描述按、吟、猱、绰、注、泛音等左手语义。

### `physical.left_hand.finger`

左手用的手指。

当前值包括 `thumb`、`index`、`middle`、`ring`、`little`、`none`、`unknown`。

### `physical.left_hand.pitch_variation`

音高变化方式。

它记录左手如何改变音高，例如吟、猱、绰、注、进、退等。

### `physical.left_hand.timbre_variation`

音色变化方式。

它记录声音的性质变化，例如空弦、泛音、按音、震音、滑动感等。

### `physical.ornaments`

附加演奏标记。

它用来记录一些不完全属于“按位”和“指法”本体、但对理解和回放很重要的动作，比如滑入、滑出、连音、装饰音、吟猱连接等。

### `acoustic`

音响结果层。记录“听起来是什么”。

这一层面向 MusicXML、MIDI、播放和分析。

### `acoustic.pitch_name`

音名。

例如 `C3`、`Bb2`。

### `acoustic.midi_note`

MIDI 音高编号。

这是现代数字音乐系统最容易直接使用的表示方式之一。

### `acoustic.duration_beats`

时值，单位是拍。

它表示这一音持续多久，不是纸面上的记号本身。

### `acoustic.musicxml_snippet`

MusicXML 片段。

它是一个可以直接给乐谱软件使用的最小输出片段，适合做导出和联通。

### `acoustic.numbered_notation`

简谱桥接信息。

它用来连接简谱类数据源，方便和 `Guqin-Dataset` 这类资料对接。

## 2. 整曲文档层

### `schema_version`

文档版本号。

它表示这份整曲文档遵循哪个规范版本。当前值是 `jianzi-document-v1`。

### `piece`

曲目主信息。

它保存整首曲子的标题、定弦、来源等核心元数据。

### `piece.title`

曲名。

### `piece.subtitle`

副标题。

可用于卷名、段名、别名或出版信息中的附加标题。

### `piece.notation_systems`

使用过的记谱体系列表。

它用于说明这份数据和哪些表示法有关，比如减字谱、简谱、MusicXML、MIDI、NLTabs。

### `piece.tuning`

定弦信息。

它保存这首曲子采用的定弦名称，以及七根弦的基准音高。

### `piece.tuning.label`

定弦名称。

例如“1=F 正调定弦”。

### `piece.tuning.strings`

七根弦对应的音高列表。

顺序固定为 1 到 7 弦。

### `piece.source`

来源信息。

它保存这份谱的出处、整理人、演奏者和参考仓库等信息。

### `piece.source.edition`

来源书名或版本名。

### `piece.source.original_source`

原始出处。

例如古谱名、卷册名或谱集名。

### `piece.source.performer`

演奏者。

### `piece.source.transcriber`

打谱者或记谱者。

### `piece.source.reference_repository`

参考仓库地址。

用于记录这份数据从哪里来的公开参考来源。

### `sections`

段落列表。

一首曲子可以分成多个段，每段再往下分小节和事件。

### `section.id`

段落编号。

它应该在整首曲子内部稳定、唯一，便于引用。

### `section.label`

段落显示名称。

例如“第一段”“慢板”“尾声”。

### `measures`

小节列表。

每个小节包含若干音符事件。

### `measure.index`

小节序号。

### `measure.time_signature`

拍号。

它用于帮助播放、导出和对齐分析。

### `measure.events`

当前小节内的音符事件序列。

## 3. 枚举术语统一

### `open`

散音。

不按弦，直接让空弦发声。

### `stopped`

按音。

左手按弦后发声。

### `harmonic`

泛音。

通过特定触弦位置产生泛音效果。

### `gou`、`mo`、`tiao`、`ti`

常见右手技法名称。

这些值应尽量保持统一，不要在不同数据集里随意改写成别的拼法。

### `jin`、`tui`、`yin`、`nao`、`chuo` 等

常见左手动作名称。

如果未来遇到更细的地方性写法，建议先用 `custom:` 扩展，而不要直接改掉已有通用词。

## 4. 命名约定

- `id` 类字段要稳定，不要因为导出顺序变化而变化。
- 术语优先用当前 schema 已定义的英文枚举，必要时在说明文档里补中文解释。
- 新增术语时，优先保持旧术语不动，再考虑兼容写法。

