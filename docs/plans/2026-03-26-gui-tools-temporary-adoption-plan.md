# gui-tools 临时接入方案

## 目标

在不把 `gui-tools` 变成长期主系统的前提下，把它作为第二部分早期的临时标注前端接入，尽快形成第一批可用的谱面标注数据。

## 为什么现在就接

原因很直接：

- 它已经支持 jianzipu
- 它已经支持 segmentation boxes
- 它已经支持 notation annotation
- 它已经能导出 OMR 数据

这意味着我们可以少做一件高成本工作：第一版标注 GUI。

## 接入原则

### 1. `gui-tools` 不是主系统

它只是前端工具。

项目里的长期真相仍然是我们自己的：

- dataset workspace
- manifest
- page / glyph / alignment records
- `Jianzi-Code`

### 2. 只借它的“标注能力”

我们借的是：

- 图像加载
- 框选
- jianzipu 标注界面
- 导出能力

我们不借的是：

- 长期数据模型
- 项目主存储
- 版本管理中心

### 3. 一开始只做最小闭环

第一阶段不追求所有功能都接。

只做下面这条闭环：

页图 -> `gui-tools` 标注 -> 导出 JSON -> importer -> internal workspace -> `Jianzi-Code`

## 接入边界

### 本阶段接受的输入

- 一小批页图
- `gui-tools` 的 jianzipu 标注 JSON
- 对应的图像文件路径

### 本阶段不做

- 多人在线协作
- 任务分发系统
- Web 标注平台
- 从 `gui-tools` 反向回写我们的内部数据

## 交付物

### 1. 运行约定

明确一套统一约定：

- Ubuntu 环境运行 `gui-tools`
- 标注导出文件统一落到约定目录
- 文件命名与图片命名固定

### 2. 导入器

实现一个 `gui-tools -> internal workspace` importer。

它至少要能抽出：

- 图像路径
- box 坐标
- box 类型
- notation 内容
- 顺序信息

### 3. 转换映射

明确三层映射：

- `gui-tools box` -> `PageRecord / GlyphRecord`
- `gui-tools notation_content` -> internal notation object
- internal notation object -> `Jianzi-Code` 候选

### 4. 最小示例集

用 3 到 5 页真实谱面跑通一遍，证明：

- 标得出来
- 导得出来
- 进得了我们的 workspace

## 建议目录约定

建议在 `.data/` 下约定一套简单结构：

```text
.data/
  gui_tools/
    project_a/
      images/
      annotations/
      exports/
  workspace/
    intake/
    normalized/
    alignments/
    jianzi_code/
```

## 实施步骤

### Step 1: 环境试装

目标：

- 在 Ubuntu 上把 `gui-tools` 跑起来
- 验证 jianzipu plugin 能正常打开
- 验证最小导出链路可用

验收：

- 能打开一张图
- 能画框
- 能保存 JSON

### Step 2: 建立最小操作规范

目标：

- 确定文件命名规则
- 确定哪些 box_type 我们先用
- 确定哪些字段在标注时是必填

验收：

- 有一页简明操作说明
- 同一页由两个人标时不会完全失控

### Step 3: 写 importer

目标：

- 把 `gui-tools` JSON 转成我们的内部对象

第一版最少输出：

- `SourceManifest`
- `PageRecord`
- `GlyphRecord`

验收：

- 导入后能看到稳定数量的页、框、谱字记录

### Step 4: 接 `Jianzi-Code`

目标：

- 从导入后的 notation 信息里生成第一版 `Jianzi-Code` 候选

验收：

- 至少能导出一个 document
- 至少能生成若干 note events

## 风险

### 1. 平台依赖重

`gui-tools` 更像 Ubuntu 研究环境工具，不适合直接要求所有参与者都本地装。

应对：

- 先把它定位为“少数人使用的临时标注前端”
- 不把它扩展成团队基础设施

### 2. JSON 结构和我们不一致

这是已知事实，不是意外。

应对：

- 从一开始就坚持 importer 边界
- 不让其它模块直接依赖 `gui-tools` JSON

### 3. 标注习惯不统一

应对：

- 第一阶段先限定少量 box_type 和少量必填项
- 先做一版简单标注规范

## 何时停止使用它

当下面任一条件成立时，就应该考虑淡出：

- 我们自己的数据工作区和 importer 已稳定
- 我们需要多人协作和更稳的任务管理
- `gui-tools` 的平台限制开始拖慢效率

这时它可以退回成：

- 早期标注历史工具
- 兼容导入来源之一

## 一句话策略

`gui-tools` 的正确用法不是“长期依赖”，而是“借它跨过最早的标注门槛”，然后尽快把数据吸进我们自己的体系。
