# ocr-engine

这个模块承载减字谱视觉识别相关能力，目标是把古琴谱影印图像中的谱字、部件和版面信息稳定抽取出来。

计划覆盖的能力包括：

- 谱字检测与切块
- 复杂减字部件识别
- 多阶段识别与后处理
- 版面结构分析
- 与 `Jianzi-Code` 协议对接的模型输出格式

当前 `src/detector.py` 为占位入口，后续会在这里接入检测模型、识别模型和推理流程。

当前推荐架构已经形成，见：

- `docs/plans/2026-03-26-ocr-engine-design.md`
- `docs/adrs/2026-03-26-ocr-engine-architecture.md`

当前第三部分的推荐路线不是直接端到端整页识别，而是：

1. 页级预处理
2. 谱字 / 版面对象检测
3. 单字候选识别
4. 部件 / radical 识别
5. 结构解码
6. 置信度校准
7. 输出给 `dataset-tools` 进入人工闭环

当前已经实现的最小代码能力包括：

- `python -m ocr_engine detect`
  读取单张图片、图片目录或输入清单 JSON，运行首版启发式检测 baseline，并写出 OCR bundle。

- `python -m ocr_engine summarize`
  读取一个 OCR bundle 的摘要报告。

- `python -m ocr_engine export-yolo-detect`
  把第二部分产出的一个内部 bundle 直接导出成检测训练常用的数据目录。

- `python -m ocr_engine export-reviewed-crops`
  把人工已经判成“真减字 / 误框”的条目直接导出成正负裁切数据，适合训练框后过滤器或二分类器。

- `python -m ocr_engine train-yolo-detect`
  为检测模型训练写出一份可直接执行的训练任务；如果环境已经装好 `ultralytics`，也可以直接开训。

- `python -m ocr_engine train-yolo-classify`
  为真假框过滤模型写出一份可直接执行的分类训练任务，直接使用人工确认过的正负裁切样本。

- `python -m ocr_engine evaluate-yolo-classify`
  为真假框过滤模型写出一份分类评估任务，固定验证集和指标出口，方便比较不同轮次。

- `python -m ocr_engine filter-yolo-bundle`
  为“先检测再过滤误框”的流程写出一份可直接执行的过滤任务，把分类器接回 OCR bundle。

- `python -m ocr_engine build-experiment-report`
  汇总检测训练、分类训练、分类评估和过滤运行记录，形成一份统一实验报告。

- `python -m ocr_engine detect-yolo`
  为已训练检测模型写出一份可直接执行的推理任务；如果环境已经装好 `ultralytics`，也可以直接产出 OCR bundle。

- 当前 baseline：
  使用纯 Python 标准库完成 PNG / PGM 读取、简单预处理和连通域检测，不依赖运行时图像库。

- 当前输出 bundle：
  `manifest.json`
  `raw/pages.ndjson`
  `raw/detections.ndjson`
  `raw/glyph_candidates.ndjson`
  `raw/component_candidates.ndjson`
  `raw/crops/.../*.pgm`
  `reports/summary.json`
  `reports/validation.json`（如果提供了 `--expected-layout`）
  `logs/run_log.json`

- 最小样例：
  `apps/ocr-engine/examples/minimal_ocr_input.json`
  `apps/ocr-engine/examples/minimal_expected_layout.json`
  `apps/ocr-engine/examples/minimal_page_001.png`
  `apps/ocr-engine/examples/minimal_page_002.png`

最小运行示例：

```bash
PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine detect \
  --input apps/ocr-engine/examples/minimal_ocr_input.json \
  --expected-layout apps/ocr-engine/examples/minimal_expected_layout.json \
  --output /tmp/guqin_ocr_bundles

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine summarize \
  --bundle /tmp/guqin_ocr_bundles/<bundle-id>

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine export-yolo-detect \
  --bundle /path/to/dataset-tools-bundle \
  --page-images-root /path/to/local/page-images \
  --output /tmp/guqin_yolo_datasets

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine export-reviewed-crops \
  --bundle /path/to/dataset-tools-bundle \
  --page-images-root /path/to/local/page-images \
  --output /tmp/guqin_reviewed_crops

# 导出的裁切分类集采用 `train/<verdict>/*.png` 和 `val/<verdict>/*.png`
# 目录结构，便于直接给 Ultralytics 分类训练使用。

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine train-yolo-detect \
  --dataset /tmp/guqin_yolo_datasets/<dataset-id> \
  --output /tmp/guqin_train_runs \
  --dry-run

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine train-yolo-classify \
  --dataset /tmp/guqin_reviewed_crops/<dataset-id> \
  --output /tmp/guqin_filter_runs \
  --dry-run

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine evaluate-yolo-classify \
  --dataset /tmp/guqin_reviewed_crops/<dataset-id> \
  --model /path/to/filter-best.pt \
  --output /tmp/guqin_filter_eval_runs \
  --dry-run

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine filter-yolo-bundle \
  --bundle /path/to/ocr-bundle \
  --model /path/to/filter-best.pt \
  --output /tmp/guqin_filtered_bundles \
  --dry-run

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine build-experiment-report \
  --output /tmp/guqin_experiment_report \
  --root /tmp/guqin_train_runs \
  --root /tmp/guqin_filter_runs \
  --root /tmp/guqin_filter_eval_runs

PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine detect-yolo \
  --input apps/ocr-engine/examples/minimal_ocr_input.json \
  --model /path/to/best.pt \
  --output /tmp/guqin_yolo_predict_runs \
  --dry-run
```

当前 bundle 的最小目录结构如下：

```text
<bundle-id>/
  manifest.json
  raw/
    pages.ndjson
    detections.ndjson
    glyph_candidates.ndjson
    component_candidates.ndjson
    crops/
      <page-id>/
        <detection-id>.pgm
  reports/
    summary.json
    validation.json
  logs/
    run_log.json
```

当前推荐的联调用法是：

1. 先在 `ocr-engine` 中运行 `detect`
2. 再在 `dataset-tools` 中运行 `import-ocr-bundle`
3. 再继续走 `process-bundle`
4. 如果要开始训练检测器，再运行 `export-yolo-detect`
5. 如果要先降低误框率，可运行 `export-reviewed-crops`
6. 用这批正负样本运行 `train-yolo-classify`
7. 数据集导出后，也可继续运行 `train-yolo-detect`
8. 训练出权重后，可运行 `detect-yolo`

这样第三部分的结果会自动进入第二部分的规范化、草稿生成和人工复核流程。

当前这版 baseline 已经具备这些实用边界：

- 能生成真正存在的谱字裁切图，而不是只给空路径
- 能输出检测框、字候选、部件候选和简单的页级回归报告
- 能和第二部分稳定联调
- 能把第二部分 bundle 导出成检测训练集目录
- 能把线上人工确认过的框导出成正负裁切样本
- 能把真假框分类任务、评估任务和过滤任务固定成标准运行记录
- 能把多轮实验结果汇总成统一报告，便于后续版本对比
- 能把训练和推理任务先固化成可执行请求，即使机器还没准备好也能先把流程接通

当前仍然明确受限于这些地方：

- 还不是训练后的正式模型，核心检测仍然是启发式 baseline
- 识别结果目前仍以占位候选为主，不是最终减字识别
- 页级验证现在主要还是数量级检查，不是严格 IoU 评测
- 本地如果没有安装 `ultralytics`，训练和模型推理会退化成 dry-run，只写任务请求和状态文件

运行环境准备说明见：

- `apps/ocr-engine/docs/runtime-environment.zh-CN.md`
- `apps/ocr-engine/docs/reviewed-filter-training.zh-CN.md`

和第一部分的桥接说明见：

- `packages/jianzi-code-spec/docs/ocr-to-jianzi-code-bridge.zh-CN.md`
