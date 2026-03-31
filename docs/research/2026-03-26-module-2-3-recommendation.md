# 第二部分与第三部分的外部项目采用建议

## 结论先行

这几个项目和论文都很契合我们的目标，但它们**不能替代**我们的第二部分和第三部分开发。

更准确地说：

- 它们能明显缩短我们的起步时间
- 能帮我们避免从零定义任务和界面
- 也能给我们冷启动一部分粗标注和研究基线
- 但它们没有一个能直接成为我们的长期主系统

## 一句话判断

- `gui-tools`：适合**临时采用**，当第二部分早期的标注前端
- `KuiSCIMA`：适合**转换接入**，作为第二部分和第三部分的冷启动参考数据与结构参考
- `guqinMM`：适合**借思路**，主要服务第三部分，不适合作为现成数据基础
- `Recognition of Radicals ... by YOLOs`：适合**借任务拆分思路**，但论文里的数据集目前不能当现成资产

## 对第二部分的意义

第二部分是 `dataset-tools`，本质是：

- 原始图像整理
- 标注与校对
- 图像对象到语义对象的对齐
- 导出训练集、评测集和 `Jianzi-Code`

### 哪个最契合

最契合的是 `gui-tools`。

原因很简单：

- 它已经有 jianzipu 标注界面
- 已经支持 segmentation boxes
- 已经有 notation annotation
- 已经能导出 OMR 数据

这意味着我们不必第一天就自己写一个标注 GUI。

### 但为什么不能直接替代第二部分

因为 `gui-tools` 的数据组织方式仍然是：

- box-first
- tool-first
- custom JSON first

而我们第二部分真正需要的是：

- manifest-first
- page / glyph / alignment / provenance-first
- 最终能稳定投影到 `Jianzi-Code`

所以正确做法不是“把 `gui-tools` 变成我们的主系统”，而是：

- 用它作为早期标注前端
- 再把它导出的 JSON 导入我们自己的工作区

## 对第三部分的意义

第三部分是 `ocr-engine`，本质是：

- 从谱面图像中检测对象
- 识别减字或部件
- 输出可供第二部分和 `Jianzi-Code` 消费的候选结果

### 哪些最有价值

第三部分里最有价值的是：

- `KuiSCIMA v2.0`
- `guqinMM`
- radicals 识别论文

它们共同说明三件事：

1. 历史中国音乐记谱确实可以做 OMR
2. 类别不平衡和小数据是真问题
3. 把任务拆成“结构 / 部件 / radicals / symbol”会比直接端到端整字识别更稳

### 但为什么还需要自己做

因为这些资源虽然方向对，但目标域不完全等于我们的目标域：

- `KuiSCIMA` 的核心世界是 *Baishidaoren Gequ* 的 notation corpus
- `guqinMM` 更像研究原型
- radicals 论文数据范围很窄，而且资产本身没有直接开放成可用数据包

所以它们可以提供：

- 基线
- 任务拆分方式
- 数据结构思路

但不能直接替我们完成“面向真实古琴谱、面向我们自己工作流”的 OCR 系统。

## 冷启动数据怎么判断

实际排名如下：

### 1. 可转化接入

`KuiSCIMA`

这是目前最有机会转成冷启动粗标注资产的。

它的价值在于：

- 有 machine-readable JSON
- 有 symbol-level positions
- 有 image-linked representation
- 包含 jianzipu

但它需要转换，而且它不是完整覆盖我们真实古琴谱世界的数据。

### 2. 只适合参考

`gui-tools`

它是工具，不是数据集。

`guqinMM`

它说明方向对，但从当前公开材料看，不足以把它当成稳定现成数据源。

### 3. 当前不能直接拿来

radicals 论文中的数据集

它证明任务可行，但不是现成可接入的公开资产。

## 最终采用建议

### 第二部分

建议：

- **短期采用 `gui-tools` 作为临时标注前端**
- **同时坚持自建 `dataset-tools` 工作区和导入层**

也就是说：

- 不自己从零写第一版 GUI
- 但也不把 `gui-tools` 当长期主系统

### 第三部分

建议：

- **借 `KuiSCIMA` 和 `guqinMM` 的任务拆分与研究方向**
- **坚持自建我们自己的古琴谱 OCR 训练与评估链路**

也就是说：

- 不自己从零摸索问题定义
- 但也不假设别人已经帮我们把核心工作做完

## 真正需要自己开发的部分

下面这些部分，基本还是必须自己做：

1. `gui-tools JSON -> internal workspace` 导入器
2. `KuiSCIMA JSON -> internal workspace` 导入器
3. page / glyph / alignment / provenance 数据模型
4. `internal workspace -> Jianzi-Code` 投影器
5. 面向我们目标域的 train / val / test 切分与评估协议
6. 面向古琴谱的 OCR 训练链路和误差分析

## 我建议的推进顺序

### Step 1

先把 `gui-tools` 当成临时前端来评估和接入。

### Step 2

优先写两个 importer：

- `gui-tools` importer
- `KuiSCIMA` importer

### Step 3

用导入后的数据搭一个最小冷启动数据工作区。

### Step 4

在这个基础上再开始第三部分的第一版检测 / 识别实验。

## 结论

所以最后的答案是：

**非常契合，但仍然需要自己开发。**

只是这个“自己开发”，不再是从零开始重造一切，而是：

- 借 `gui-tools` 的界面和导出思路
- 借 `KuiSCIMA` 的数据结构和冷启动资产
- 借 `guqinMM` 与 YOLO radicals 论文的任务拆分与基线方向
- 然后把这些都收进我们自己的第二部分和第三部分体系里
