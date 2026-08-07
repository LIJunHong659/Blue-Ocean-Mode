from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
C5 = ROOT / "C5"
REPORT = next(p for p in C5.iterdir() if p.is_file() and p.name == "第五章报告.md")


FIG_BASE = "5.7混合最优策略短测试与年度运营分析/results/minimal_sensitivity_5_6"
FIG = lambda name: f"{FIG_BASE}/figures/{name}"
PROC = lambda name: f"{FIG_BASE}/processed/{name}"


INSERT_MARKER = "### 5.6.4 敏感性结论"
REPLACEMENT_MARKER = "### 5.6.5 敏感性结论"


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
    if INSERT_MARKER not in text:
        raise RuntimeError("target heading not found")
    text = text.replace(INSERT_MARKER, INSERT_BLOCK, 1)
    text = text.replace(
        "8. 敏感性分析已拆分为固定调度重定价、生命周期台账重算和少量边界全年重跑三层；当前已完成 `flex_ratio_0p50` 和 `distance_loss_proxy_0p12`，前者显著抬升 ENS 与储备松弛，后者主要压缩受端电量和收入，其余边界场景继续保留为待办。",
        "8. 敏感性分析已拆分为固定调度重定价、生命周期台账重算和少量边界全年重跑三层；当前已完成 `flex_ratio_0p50` 和 `distance_loss_proxy_0p12`，前者显著抬升 ENS 与储备松弛，后者主要压缩受端电量和收入，并同步生成处理后 CSV 与图像，其余边界场景继续保留为待办。",
        1,
    )
    insert_at = text.index("## 证据文件")
    evidence_block = f"""

- `{PROC('c5_56_processed_price_cases.csv')}`
- `{PROC('c5_56_processed_cost_cases.csv')}`
- `{PROC('c5_56_processed_boundary_kpi_delta.csv')}`
- `{PROC('c5_56_processed_event_summary.csv')}`
- `{PROC('c5_56_processed_hourly_compact.csv')}`
- `{FIG('c5_56_price_sensitivity_line.png')}`
- `{FIG('c5_56_cost_delta_bar.png')}`
- `{FIG('c5_56_boundary_kpi_line_grid.png')}`
- `{FIG('c5_56_hourly_cumulative_cash_margin_line.png')}`
- `{FIG('c5_56_event_ens_line.png')}`
"""
    text = text[:insert_at] + evidence_block + text[insert_at:]
    REPORT.write_text(text, encoding="utf-8", newline="\r\n")


if __name__ == "__main__":
    main()
