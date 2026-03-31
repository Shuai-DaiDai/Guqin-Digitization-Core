# 真假框过滤训练

这份说明对应 `scripts/ops/run_reviewed_filter_training.sh`。
它的目标很直接：把你已经确认过的正负裁切样本，变成一轮可以在远程 GPU 机上直接跑的分类训练任务。

## 它适合做什么

- 训练一个“这个框是不是一个真正减字框”的过滤器
- 降低后续 OCR 流程里的误框率
- 给下一轮检测模型提供更干净的输入

## 输入数据

脚本默认使用 `export-reviewed-crops` 导出的目录。
目录里至少要有：

- `manifest.csv`
- `export_report.json`
- `train/correct/*.pgm`
- `train/wrong/*.pgm`
- `val/correct/*.pgm`
- `val/wrong/*.pgm`

## 远程机器上的推荐目录

建议把仓库放在：

- `/root/autodl-tmp/Guqin-Digitization-Core`

建议把运行产物放在：

- `/root/autodl-tmp/guqin-runs/reviewed_filter_runs`

这样和现有 OCR / dataset 流程的目录风格保持一致。

## 先做的检查

脚本会先检查：

- 数据集目录是否存在
- `manifest.csv` 是否存在
- `export_report.json` 是否存在
- `torch` 是否可导入
- `ultralytics` 是否可导入
- GPU 是否可用

如果环境里还没有装好 `ultralytics`，脚本会停在 dry-run 风格的状态，不会假装训练成功。

## 执行方式

在远程 GPU 机上执行：

```bash
./scripts/ops/run_reviewed_filter_training.sh \
  /root/autodl-tmp/guqin-runs/reviewed_crop_datasets/<dataset-id> \
  50 \
  32 \
  224 \
  0
```

如果只是想先看命令和环境检查，不真正开训，可以再加一个 `1` 作为最后参数。

## 输出约定

训练结果默认写到：

- `/root/autodl-tmp/guqin-runs/reviewed_filter_runs/<run-id>`

每次运行至少会留下：

- `run_request.json`
- `run_status.json`
- 训练日志

如果真正跑起来并且 `ultralytics` 可用，目录里还会出现模型权重文件。

