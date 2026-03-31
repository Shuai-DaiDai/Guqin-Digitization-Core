# dataset-tools

这个模块负责数据清洗、对齐和样本构建，是从古谱影印页走向结构化训练数据的中间处理层。

计划覆盖的能力包括：

- 扫描谱本元数据整理
- OCR 结果与人工校对结果对齐
- 减字部件级标注清洗
- `Jianzi-Code` 样本导出
- 训练集、验证集与评测集切分

当前 `src/pipeline.py` 为占位入口，后续会逐步扩展为可执行的数据处理流水线。

当前已经实现的最小代码能力包括：

- `python -m dataset_tools import-gui-tools`
  读取 `gui-tools` 的 `Jianzipu` JSON，并导入内部工作区目录。

- `python -m dataset_tools import-kuiscima`
  读取 KuiSCIMA 风格的 image-linked JSON，并导入同一套内部工作区目录。

- `python -m dataset_tools import-manual-csv`
  读取人工准备的来源表和粗标注表，并导入同一套内部工作区目录。

- `python -m dataset_tools import-ocr-bundle`
  读取第三部分输出的 OCR bundle，并导入同一套内部工作区目录。

- `python -m dataset_tools inventory-pdf-library`
  扫描一批影印版 PDF，生成可供后续挑选和分批处理的目录清单。

- `python -m dataset_tools render-pdf-pages`
  把单个 PDF 按页渲染成 PNG 页图，作为真实谱面进入后续 OCR 和人工校对流程的入口。

- `python -m dataset_tools validate-manual-csv`
  在导入前检查人工准备的来源表和粗标注表有没有明显问题。

- `python -m dataset_tools summarize-bundle`
  为单个导入 bundle 生成基础统计摘要。

- `python -m dataset_tools project-jianzi-code`
  从导入后的 `Music` 类标注生成第一版 `Jianzi-Code` 候选。

- `python -m dataset_tools normalize-bundle`
  把候选结果整理成更稳定的中间音符记录，供后续人工校对和规则补全。

- `python -m dataset_tools audit-bundle`
  生成基础质量报告，检查缺图、候选缺失和仍需复核的记录数量。

- `python -m dataset_tools enrich-bundle`
  把中间音符记录按规则补全为更接近 `Jianzi-Code` 的事件草稿，并明确列出还缺哪些字段。

- `python -m dataset_tools process-bundle`
  按正确顺序一键生成摘要、候选、中间音符记录、事件草稿和质量报告，避免分步执行时顺序出错。

- `python -m dataset_tools build-review-queue`
  从仍有缺口的事件草稿中生成人工复核队列，明确优先级和建议动作。

- `python -m dataset_tools slice-review-queue`
  把过大的人工复核队列切成更适合分配和分批处理的小批次。

- `python -m dataset_tools export-review-decisions-template`
  根据整包或单个复核批次导出可直接填写的人工回填模板。

- `python -m dataset_tools export-review-site`
  把单个复核批次打包成一个可直接分享的静态校对页面，适合上线给外部校对人员使用。

- `python -m dataset_tools assemble-document`
  把事件草稿拼成整曲级的 `Jianzi-Code` 文档草稿，供后续校对和补全。

- `python -m dataset_tools prepare-review-pack`
  生成一个适合直接交给人工校对人员的交付包，包含摘要、复核表和文档草稿入口。

- `python -m dataset_tools apply-review-decisions`
  把人工确认结果重新回填到事件草稿中。

- `python -m dataset_tools apply-online-review-db`
  把线上校对页面保存回来的 SQLite verdict 正式写回 raw glyph 层，并可顺手重建候选、草稿和复核队列。

- `python -m dataset_tools apply-online-review-json`
  把校对页面导出的 `review-decisions.json` 直接写回 raw glyph 层；适合线上服务临时不可访问、但浏览器里已经导出结果的情况。

- `dataset_tools.pipeline.recommend_next_review_batch`
  基于 raw glyphs、review queue 和线上 verdict 生成下一批高价值页面建议，输出页级排序和具体 `review_id` 清单。

- `dataset_tools.pipeline.evaluate_review_impact`
  离线复盘这批人工复核对 bundle 的影响，统计保留、排除、覆盖率和页级完成情况。

- `python -m dataset_tools evaluate-review-impact`
  为一个 bundle 生成本轮人工复核影响报告。

- `python -m dataset_tools recommend-next-batch`
  为一个 bundle 推荐下一批更值得继续人工处理的页面和条目。

- `python -m dataset_tools materialize-next-batch`
  把推荐结果真正落成一个新的复核批次目录，方便继续生成校对页或交付包。

- `python -m dataset_tools prepare-missing-box-audit`
  为补漏框准备一个轻量页包，自动拷贝页图、汇总当前框数量，并生成一份可直接填写的漏框备注模板。

- `python -m dataset_tools build-workspace-index`
  为一个工作区根目录下的所有 bundle 生成总览索引，方便批量管理。

- `python -m dataset_tools export-manual-templates`
  导出空白模板，方便开始下一批人工整理和回填工作。

- 内部基础对象：
  `SourceManifest`、`PageRecord`、`GlyphRecord`、`ImportLog`

- 中间层对象：
  `JianziCodeCandidate`、`NormalizedNoteRecord`

- 最小样例：
  `apps/dataset-tools/examples/gui_tools_minimal_jianzipu.json`
  `apps/dataset-tools/examples/kuiscima_minimal_jianzipu.json`
  `apps/dataset-tools/examples/manual_metadata_minimal.csv`
  `apps/dataset-tools/examples/manual_annotations_minimal.csv`
  `apps/dataset-tools/examples/manual_review_decisions_minimal.csv`

最小运行示例：

```bash
PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools import-gui-tools \
  --input apps/dataset-tools/examples/gui_tools_minimal_jianzipu.json \
  --output /tmp/guqin_dataset_workspace

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools import-manual-csv \
  --metadata apps/dataset-tools/examples/manual_metadata_minimal.csv \
  --annotations apps/dataset-tools/examples/manual_annotations_minimal.csv \
  --output /tmp/guqin_dataset_workspace

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools import-ocr-bundle \
  --input /path/to/ocr-bundle \
  --output /tmp/guqin_dataset_workspace

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools inventory-pdf-library \
  --input qupu \
  --output /tmp/guqin_pdf_inventory

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools render-pdf-pages \
  --input "qupu/琴曲集成 第1册 (中国艺术研究院音乐研究所，北京古琴研究会编) (z-library.sk, 1lib.sk, z-lib.sk).pdf" \
  --output /tmp/guqin_pdf_pages/volume-01 \
  --start-page 1 \
  --end-page 5

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools validate-manual-csv \
  --metadata apps/dataset-tools/examples/manual_metadata_minimal.csv \
  --annotations apps/dataset-tools/examples/manual_annotations_minimal.csv
```

导入后可继续执行：

```bash
PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools summarize-bundle \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools project-jianzi-code \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools normalize-bundle \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools audit-bundle \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools enrich-bundle \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools process-bundle \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools build-review-queue \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools slice-review-queue \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --batch-size 200 \
  --max-per-page 20

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools export-review-decisions-template \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --batch-id batch_001 \
  --output /tmp/review_decisions_batch_001.csv

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools export-review-site \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --batch-id batch_001 \
  --page-images-root /tmp/guqin_page_images \
  --output /tmp/guqin_review_site_batch_001

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools assemble-document \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools prepare-review-pack \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools apply-review-decisions \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --decisions apps/dataset-tools/examples/manual_review_decisions_minimal.csv

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools apply-online-review-db \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --db /tmp/guqin-review-live.db \
  --site-id source-id::batch_001

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools apply-online-review-json \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --input /tmp/review-decisions.json \
  --site-id source-id::batch_001

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools evaluate-review-impact \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id>

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools recommend-next-batch \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --target-item-count 200

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools materialize-next-batch \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --batch-id batch_002 \
  --max-pages 1

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools prepare-missing-box-audit \
  --bundle /tmp/guqin_dataset_workspace/<bundle-id> \
  --page-images-root /tmp/guqin_page_images \
  --output /tmp/guqin_missing_box_audit \
  --only-reviewed-pages \
  --max-pages 10

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools build-workspace-index \
  --workspace /tmp/guqin_dataset_workspace

PYTHONPATH=apps/dataset-tools/src \
python3 -m dataset_tools export-manual-templates \
  --output /tmp/guqin_manual_templates
```

当前 bundle 的最小目录结构如下：

```text
<bundle-id>/
  raw/
    source_manifest.json
    pages.ndjson
    glyphs.ndjson
  derived/
    jianzi_code_candidates/
      candidates.ndjson
      projection_report.json
    jianzi_code_drafts/
      event_drafts.ndjson
      draft_report.json
      document_draft.json
      document_draft_report.json
    normalized_notes/
      notes.ndjson
      normalization_report.json
    review_queue/
      batches/
        batches_summary.json
        batch_001/
          items.csv
          items.ndjson
          summary.json
      items.csv
      items.ndjson
      review_report.json
  reports/
    summary.json
    quality_report.json
    review_queue_summary.json
  handoff/
    review_pack/
      README.md
      review_pack.json
  logs/
    import_log.json
```

当前 `summary.json` 会给出页数、标注框数量、`Music` 框数量、标注类型分布，以及缺失图片页数量。
当前 `candidates.ndjson` 是第一版低置信度候选，只保留了能从外部标注直接投影出来的视觉信息和部分演奏提示，供后续人工校对和规范化继续使用。
当前 `notes.ndjson` 是第二层中间记录，用于把候选进一步整理成更适合校对和后续转换的稳定输入。
当前 `event_drafts.ndjson` 是规则补全后的事件草稿，已经尽量贴近 `Jianzi-Code` 的 `visual` 和 `physical` 结构，同时会把仍未解决的缺口单独列出来。
当前 `review_queue/items.ndjson` 用于人工处理，把最需要补录的记录单独列出来，并给出建议动作。
当前 `review_queue/items.csv` 适合直接给人工标注或校对人员使用。
当前 `review_queue/batches/` 会把大批量待复核项切成更容易分配和协作的小批次。
当前 `export-review-site` 会把批次数据和页图打包成一套纯静态站点，适合发给外部人员直接在线查看和点选。
当前 `derived/online_review/` 会保存线上校对 verdict 的快照、应用报告和回灌记录。
如果线上服务暂时不可访问，也可以先从页面导出 `review-decisions.json`，再用 `apply-online-review-json` 继续回灌，不必等远程 SQLite。
当前 `derived/next_batch/` 会保存下一批高价值页面建议、页级排序和最终选中的 `review_id` 清单。
当前 `derived/review_impact/` 会保存人工复核离线复盘报告，方便检查覆盖率和误框排除效果。
当前 `document_draft.json` 是整曲级草稿，已经能作为后续生成正式 `Jianzi-Code` 文档的起点。
当前 `handoff/review_pack/` 是对外移交包，方便把这一批待校对数据直接交给音乐专业人员或整理人员。
仓库里的 `scripts/ops/review_impact.sh` 可以把离线复盘直接跑成报告。
做漏框检查时，`--page-images-root` 建议优先指向原始整页图目录，或未过滤的整页训练图目录。不要默认拿已经过滤过的训练集图片目录来做漏框检查，否则某些被完全排空的页可能没有底图。

人工冷启动说明见：

- `apps/dataset-tools/docs/manual-workflow.zh-CN.md`

当前已经形成的设计与研究文档包括：

- `docs/plans/2026-03-25-dataset-tools-design.md`
- `docs/plans/2026-03-25-dataset-source-inventory.md`
- `docs/research/2026-03-26-module-2-3-recommendation.md`
- `docs/plans/2026-03-26-gui-tools-temporary-adoption-plan.md`
- `docs/plans/2026-03-26-dataset-importers-plan.md`
