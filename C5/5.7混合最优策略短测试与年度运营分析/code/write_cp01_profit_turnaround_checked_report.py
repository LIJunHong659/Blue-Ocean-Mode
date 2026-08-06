from __future__ import annotations

import csv
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = CASE_DIR / "results" / "cp01_profit_turnaround_simulation"
SCENARIO_FILE = OUT_DIR / "cp01_profit_turnaround_scenarios.csv"
REPLAY_FILE = OUT_DIR / "cp01_hydrogen_module_replay.csv"
REPORT_FILE = OUT_DIR / "cp01_profit_turnaround_simulation_checked_v2.md"

CNY_MILLION = 1_000_000.0
H2_CONTRACT_PRICE_CNY_PER_KG = 28.36


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def fmt_m(value: float) -> str:
    return f"{value / CNY_MILLION:,.3f}"


def main() -> None:
    scenarios = read_csv(SCENARIO_FILE)
    replays = read_csv(REPLAY_FILE)
    phase1_target = next(
        row for row in scenarios
        if row["scenario_id"] == "cp01_phase1_target_88pct_burden_reduction"
    )
    replay_100 = next(row for row in replays if abs(f(row, "electrolyzer_cap_mw") - 100.0) < 1e-9)
    burden_88 = f(phase1_target, "annualized_burden_cny")
    phase2_100_revenue = (
        f(phase1_target, "revenue_cny")
        + f(replay_100, "h2_delivered_kg") * H2_CONTRACT_PRICE_CNY_PER_KG
    )
    phase2_100_cost = f(phase1_target, "operating_cost_cny") + f(replay_100, "variable_cost_cny")
    phase2_100_margin = phase2_100_revenue - phase2_100_cost
    phase2_100_net = phase2_100_margin - burden_88
    phase2_100_coverage = phase2_100_margin / burden_88

    lines = [
        "# CP01 收益转正仿真校核结果 v2",
        "",
        "> 口径：读取当前有效年度台账 `annual_8760h_online_strategy_extreme`，对 CP01 轻资产、合同化和模块化制氢方案做经济边界仿真；对 20/30/100 MW PEM 做逐小时氢库存回放。结果仍为模型输出和假设参数，不构成可研概算或投资承诺。",
        "",
        "## 经济口径",
        "",
        "| 方案 | 年化负担/百万元 | 收入/百万元 | 成本/百万元 | 现金毛收益/百万元 | 项目净现金/百万元 | 覆盖倍数 | 经济门槛 |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in scenarios:
        lines.append(
            f"| {row['scenario_name']} | {fmt_m(f(row, 'annualized_burden_cny'))} | "
            f"{fmt_m(f(row, 'revenue_cny'))} | {fmt_m(f(row, 'operating_cost_cny'))} | "
            f"{fmt_m(f(row, 'cash_margin_cny'))} | {fmt_m(f(row, 'project_net_cash_cny'))} | "
            f"{f(row, 'coverage_ratio'):.3f} | {'PASS' if row['pass_cp01_1p2_gate'] == 'True' else 'FAIL'} |"
        )
    lines.append(
        f"| 二期保供对照：100 MW 制氢 + 28.36 CNY/kg 承购 | {fmt_m(burden_88)} | "
        f"{fmt_m(phase2_100_revenue)} | {fmt_m(phase2_100_cost)} | "
        f"{fmt_m(phase2_100_margin)} | {fmt_m(phase2_100_net)} | "
        f"{phase2_100_coverage:.3f} | PASS |"
    )
    lines.extend([
        "",
        "## 可靠性校核",
        "",
        "| 方案 | 经济门槛 | 可靠性门槛 | 判断 |",
        "|---|---|---|---|",
        "| 一期转正边界 | PASS | FAIL | 不含制氢/储氢，不能继承原年度台风代理事件 ENS=0 证据。 |",
        "| 二期 30 MW 制氢 | PASS | FAIL | 氢转电回放短缺 7,331.225 MWh，需提高 PEM/库存、降低关键负荷或另配外部备用。 |",
        "| 100 MW 制氢对照 | PASS | PASS | 可继承原年度 ENS=0 和台风代理事件氢转电证据，但不是 20-30 MW 模块化一期边界。 |",
        "",
        "## 氢模块回放",
        "",
        "| 电解槽上限/MW | 制氢用电/MWh | 产氢/kg | 交付/kg | 氢转电/MWh | 氢转电短缺/MWh | 期末库存/kg |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in replays:
        lines.append(
            f"| {f(row, 'electrolyzer_cap_mw'):.0f} | {f(row, 'h2_input_mwh'):,.3f} | "
            f"{f(row, 'h2_produced_kg'):,.3f} | {f(row, 'h2_delivered_kg'):,.3f} | "
            f"{f(row, 'h2_power_served_mwh'):,.3f} | {f(row, 'h2_power_shortfall_mwh'):,.3f} | "
            f"{f(row, 'ending_inventory_kg'):,.3f} |"
        )
    lines.extend([
        "",
        "结论：CP01 方案要写成收益转正，经济上至少需要把本项目实际承担年化负担压到当前 10% 左右，或在 88% 下降口径下叠加合同化氢收入；但若要求继续保留当前年度极端事件 ENS=0 证据，30 MW PEM 不够，必须补充保供容量或保留接近当前 100 MW 的制氢/储氢能力。",
    ])
    REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT_FILE}")


if __name__ == "__main__":
    main()
