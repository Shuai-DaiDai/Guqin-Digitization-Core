# OCR Examples

这组样例只用于第三部分 `ocr-engine` 的冷启动和验证。

## 文件说明

- `minimal_ocr_input.json`
  OCR 主命令的最小输入清单，列出页面图像和基本上下文。

- `minimal_expected_layout.json`
  预期的页级布局和谱字候选位置，用于后续回归验证。

- `minimal_page_001.png`
  合成的第一页示意图，包含页边、正文区域和几个谱字样式块。

- `minimal_page_002.png`
  合成的第二页示意图，布局与第一页略有不同，方便测试多页处理。

## 使用方式

未来主命令可以直接读取 `minimal_ocr_input.json`，按其中的 `image_file` 加载页面图像，再对照 `minimal_expected_layout.json` 做验证。

当前这些文件的目标不是模拟真实古琴谱的全部复杂性，而是提供一个稳定、可重复的最小样例入口。

当前推荐的验证命令：

```bash
PYTHONPATH=apps/ocr-engine/src \
python3 -m ocr_engine detect \
  --input apps/ocr-engine/examples/minimal_ocr_input.json \
  --expected-layout apps/ocr-engine/examples/minimal_expected_layout.json \
  --output /tmp/guqin_ocr_demo
```

跑完后可以重点看：

- `reports/summary.json`
- `reports/validation.json`
- `raw/crops/`
