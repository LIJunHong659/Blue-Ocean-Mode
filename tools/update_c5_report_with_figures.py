from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
C5 = ROOT / "C5"
REPORT = next(p for p in C5.iterdir() if p.is_file() and p.name == "第五章报告.md")


FIG_BASE = "5.7混合最优策略短测试与年度运营分析/results/minimal_sensitivity_5_6"
FIG = lambda name: f"{FIG_BASE}/figures/{name}"


INSERT_MARKER = "### 5.6.4 敏感性结论"


INSERT_BLOCK = f"""
### 5.6.4 图表化展示

为便于对照，本节把已处理的敏感性结果单独可视化。`processed/` 下输出统一口径的汇总表：金额统一换算为百万元，碳代理统一换算为 ktCO2e，边界场景补出相对基准的 delta 和百分比变化，逐时台账也生成了 compact 版本，便于后续继续做二次处理。

![Price sensitivity line]({FIG('c5_56_price_sensitivity_line.png')})

![Cost delta bar]({FIG('c5_56_cost_delta_bar.png')})

![Boundary KPI grid]({FIG('c5_56_boundary_kpi_line_grid.png')})

![Hourly cumulative cash margin]({FIG('c5_56_hourly_cumulative_cash_margin_line.png')})

![Event ENS line]({FIG('c5_56_event_ens_line.png')})

### 5.6.5 敏感性结论
"""


def main() -> None:
    text = REPORT.read_text(encoding="utf-8")
    if INSERT_MARKER in text and "### 5.6.4 图表化展示" not in text:
        text = text.replace(INSERT_MARKER, INSERT_BLOCK, 1)

    archive_block = f"""
## 结果归档

- 敏感性分析的处理表、边界重跑结果和图表统一归档在 `{FIG_BASE}/`。
- 如需复核，优先查看该目录下的 `processed/`、`figures/` 和 `annual_dispatch_boundary_cases/` 子目录。
"""
    archive_pattern = r"(?s)## (?:证据文件|结果归档)\s*.*\Z"
    if re.search(archive_pattern, text):
        text = re.sub(archive_pattern, archive_block, text, count=1)
    else:
        text = text.rstrip() + "\n" + archive_block

    REPORT.write_text(text, encoding="utf-8", newline="\r\n")


if __name__ == "__main__":
    main()
