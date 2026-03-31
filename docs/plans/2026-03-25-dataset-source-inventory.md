# Dataset Source Inventory

## 目标

这份清单用于回答一个实际问题：

第二部分 `dataset-tools` 现在有哪些现成数据可以接，哪些只能参考，哪些必须由我们自己采集和标注。

## 结论先行

现有公开资源足够让我们启动第二部分，但不够直接完成第二部分。

它们能解决的是：

- 曲目元数据
- 定弦信息
- 机器可读乐谱
- 部分演奏语义

它们解决不了的是：

- 谱面扫描图的大规模稳定来源
- 图像到谱字的对齐关系
- 谱字框 / 部件框标注
- OCR 训练标签
- 人工修订历史

所以第二部分的数据策略必须分成两层：

1. 先接现成的结构化资源。
2. 再自建一小批带图像与对齐关系的核心工作集。

## 一、可立即接入的资源

### 1. neuralfirings/guqincomposer

链接：

- [guqincomposer](https://github.com/neuralfirings/guqincomposer)

可提供：

- 一套成熟的古琴录入思路
- 弦、徽位、左右手、滑音、装饰动作等语义线索
- 部分减字标准与技法说明图片
- 可作为“导入器参考格式”的 shorthand 逻辑

不提供：

- 成体系的古谱扫描页
- 图像到谱字的标注
- 可直接训练 OCR 的数据包

适合用途：

- 做 `guqincomposer -> internal workspace -> Jianzi-Code` 的 adapter
- 借鉴演奏语义字段设计
- 借鉴装饰音和手法词汇

不适合作为：

- 主训练数据源
- 主图像数据源

### 2. lukewys/Guqin-Dataset

链接：

- [Guqin-Dataset](https://github.com/lukewys/Guqin-Dataset)

可提供：

- `reference.csv` 曲目元数据
- 大量 MusicXML 文件
- 曲目、段落、小节级的整理成果
- 一套“简谱速录 -> MusicXML” 的桥接思路

不提供：

- 对应的古谱扫描页
- 谱字级图像标注
- 图像到音符的对齐关系
- 减字部件拆分标签

适合用途：

- 做 `MusicXML / metadata -> internal workspace` 的 adapter
- 作为曲目级、段落级元数据来源
- 作为 `Jianzi-Code` 音响层和桥接层的校对参考

不适合作为：

- OCR 图像训练数据
- 视觉检测或识别标注来源

### 3. yufenhuang/Guqin-dataset

链接：

- [Guqin-dataset](https://github.com/yufenhuang/Guqin-dataset)

可提供：

- 与 `Guqin-Dataset` 相近的 MusicXML 和 metadata 资源

价值判断：

- 更像是同类资源补充，而不是新增一类关键数据

适合用途：

- 交叉核对
- 备用镜像来源

## 二、可作为辅助参考的外部资源

### 4. Chinese Text Project 上的古琴谱影印与 OCR 文本

示例：

- [《西麓堂琴統》](https://ctext.org/wiki.pl?if=gb&res=814636)

可提供：

- 古琴古籍的公开页面入口
- OCR 文本与影印页对照入口
- 适合后续建立“谱面图 + 文本参考”的工作集

风险：

- OCR 文本本身并不可靠
- 页面结构不一定规则
- 抓取和整理成本不低

适合用途：

- 作为自建图像工作集的公开来源之一
- 用于页级导入与人工校对试点

### 5. 古琴减字谱百科

链接：

- [古琴减字谱百科](https://jianzipu.wikidot.com/)

可提供：

- 减字词条
- 部分字形截图
- 指法术语和解释

不提供：

- 成体系训练集
- 曲谱级连续标注

适合用途：

- 做术语词典
- 做减字部件与指法说明参考
- 辅助建立视觉部件词汇表

### 6. Guqin Tabs

链接：

- [Guqin Tabs](https://guqintabs.com/)

可提供：

- 现代数字谱录入界面思路
- 简谱 / 减字谱 / TAB / staff 的联动概念

不提供：

- 稳定开放的数据集
- 图像训练标注

适合用途：

- 借鉴交互设计
- 借鉴字段组织方式

### 7. GuqinSonGest

链接：

- [GuqinSonGest](https://zenodo.org/records/15838294)

可提供：

- 古琴演奏技法的音视频数据

适合用途：

- 将来做技法语义、音色验证、多模态研究

不适合作为：

- 当前第二部分的数据清洗主来源

## 三、第二部分真正缺的是什么

要让 `dataset-tools` 真正成立，至少还缺下面 5 类核心数据：

### 1. 谱面扫描页

我们需要的是：

- 原始页图
- 页码
- 来源信息
- 清晰的文件组织

### 2. 页到谱字的切分信息

我们需要的是：

- 每个谱字在页面上的位置
- 区域框或多边形
- 所属页、所属行、所属段

### 3. 谱字到语义事件的对齐

我们需要的是：

- 这个图像对象对应哪个音
- 这个音在曲子里的位置
- 这个对齐是机器给的还是人工确认的

### 4. 人工修订记录

我们需要的是：

- 谁修了什么
- 改前是什么
- 改后是什么
- 为什么改

### 5. 面向训练的导出标签

我们需要的是：

- detection 数据
- classification 数据
- OCR 识别数据
- review / eval split

## 四、我建议的最小可行数据策略

### Phase A：先用现成结构化数据搭桥

先接这三类：

- `Guqin-Dataset` / `Guqin-dataset` 的 metadata 和 MusicXML
- `guqincomposer` 的 shorthand 语义
- 我们自己的 `Jianzi-Code`

这样先把：

- 曲目
- 段落
- 小节
- 单音事件

这一层打通。

### Phase B：自建一个小型图像工作集

建议先收一批不大的样本：

- 5 到 20 页谱面扫描图
- 覆盖 2 到 5 首曲子
- 最好包含 1 到 2 个不同版本来源

然后先只做：

- 页面登记
- 谱字切分
- 粗对齐
- 人工确认

不追求一开始就做全量。

### Phase C：把图像工作集和结构化乐谱桥起来

当我们已经有：

- 页图
- 谱字框
- 曲目结构
- `Jianzi-Code`

就可以开始建立真正对 OCR 和后续校订有价值的 alignment layer。

## 五、现在能不能开始

可以。

因为第二部分最早期的工作，不依赖我们先拥有大而全的数据集。

我们现在已经足够开始：

- 设计内部 workspace
- 写 `Guqin-Dataset` adapter
- 写 `guqincomposer` adapter
- 定义 manifest / page / glyph / alignment 的数据模型

但如果要进入真正有价值的图像对齐阶段，我们很快就需要一批自建样本。

## 六、最需要用户尽快提供的外部协助

优先级最高的是：

1. 一小批真实古琴谱页图像
2. 这些图像对应的基本来源信息
3. 如果可能，至少几页的人工理解或粗标注

只要这三样到位，第二部分就可以从“架构设计”进入“真正有价值的实现”。
