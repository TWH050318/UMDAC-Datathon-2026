# UMDAC Datathon 2026 — Swift payments reverse-engineering

目标：只用官方数据，还原生成这份合成跨境支付数据的业务规则。
**数据文件绝对不能上传到 GitHub 或分享给队外的人**（`.gitignore` 已排除 `data/`）。

## 目录
```
data/raw/        官方 CSV（不进 git）
data/interim/    payments_raw/      CSV 转成的 Parquet（含全部原始列 + ROW_ID）
data/processed/  payments_features/ 分析用表（原始短列 + 全队共用的派生字段）
src/             config.py · 01_build_parquet.py · 02_build_features.py · utils.py
notebooks/       00 数据质量 · 01 路由/时长/换汇 · 02 货币/金额/时间/地域 · 03 客户/异常
                 04 未解问题（银行延迟等）· 05 补全分析和 dashboard 用图
                 06 样本外验证（前 2/3 时间学规则，后 1/3 检验）
outputs/charts/  每张图的 PNG（放进 dashboard）
outputs/csv/     每张图背后的聚合表（Power BI 的数据源）
docs/            data_issues_log.md · hypothesis_log.md · methodology.md
                 RULES_AND_SOURCES.txt（每条规则 + 图表和代码来源，做 dashboard 时照这个排）
```

## 第一次使用（VS Code）
1. 用 VS Code 打开这个文件夹，安装 Python 和 Jupyter 两个扩展。
2. 终端里运行：`pip install -r requirements.txt`
3. 如果 `data/interim` 和 `data/processed` 里已经有 Parquet，直接打开 notebook 运行即可。
4. 如果要从头重建：把官方 CSV 解压到 `data/raw/`，然后
   `cd src` → `python 01_build_parquet.py` → `python 02_build_features.py`（共约 2–3 分钟）。
5. 内存不够时把 `src/config.py` 里的 `MEMORY_LIMIT` 调小。
6. 每个 notebook 开头会检查数据是否正好 10,000,000 行；不对会直接报错停下。
   这时检查 `data/` 下的两个文件夹里是否混进了不是 `data_*.parquet` 的文件。

## 工作方式
每条规则都走同一个循环，并记进 `docs/hypothesis_log.md`：
假设 → 全量检验（`rule_check`）→ 排除混杂 → 写成"条件 / 效果 / 幅度 / 范围" → 标注状态（已证实 / 有支持 / 否定 / 未解释）。

## 工具声明
Python、DuckDB、pandas、NumPy、Matplotlib、NetworkX；代码在 Claude（Anthropic 的 AI 助手）协助下编写，由队员复核。
