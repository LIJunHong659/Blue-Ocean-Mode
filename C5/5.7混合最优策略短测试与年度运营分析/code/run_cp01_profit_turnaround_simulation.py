from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]
ANNUAL_DIR = CASE_DIR / "results" / "annual_8760h_online_strategy_extreme"
OUT_DIR = CASE_DIR / "results" / "cp01_profit_turnaround_simulation"

SUMMARY_FILE = ANNUAL_DIR / "c5_annual_online_strategy_summary.csv"
HOURLY_FILE = ANNUAL_DIR / "c5_annual_online_strategy_hourly.csv"

CNY_MILLION = 1_000_000.0
TOTAL_ANNUAL_BURDEN_CNY = 4_054.611 * CNY_MILLION

PIPE_LOSS = 0.01
SHIP_LOSS = 0.02
SEC_KWH_PER_KG = 56.77
H2_LHV_KWH_PER_KG = 33.33
H2_POWER_EFFICIENCY = 0.50
H2_STORAGE_CAP_KG = 72_000.0

SOURCE_OM_CNY_PER_MWH = 20.0
BESS_DEGRADATION_CNY_PER_MWH = 30.0
H2_VARIABLE_CNY_PER_KG = 3.5
H2_PIPE_TRANSPORT_CNY_PER_KG = 1.5
H2_SHIP_TRANSPORT_CNY_PER_KG = 3.0
H2_POWER_VARIABLE_CNY_PER_MWH = 30.0
ELECTROLYZER_START_CNY_PER_MODULE = 20_000.0
ELECTROLYZER_MODULE_MW = 20.0

# Current CP01 document split. It is scaled to the exact annual summary
# revenue so the scenario rows reconcile with the effective evidence package.
CP01_REVENUE_SPLIT_CNY = {
    "power": 290.84 * CNY_MILLION,
    "hydrogen": 128.79 * CNY_MILLION,
    "compute": 80.23 * CNY_MILLION,
    "marine": 47.30 * CNY_MILLION,
}


@dataclass
class ReplayResult:
    electrolyzer_cap_mw: float
    h2_input_mwh: float
    h2_produced_kg: float
    h2_delivered_kg: float
    h2_power_served_mwh: float
    h2_power_shortfall_mwh: float
    ending_inventory_kg: float
    minimum_inventory_kg: float
    maximum_inventory_kg: float
    module_start_count: int
    variable_cost_cny: float


@dataclass
class ScenarioResult:
    scenario_id: str
    scenario_name: str
    dispatch_basis: str
    annualized_burden_cny: float
    burden_retained_fraction: float
    revenue_cny: float
    operating_cost_cny: float
    cash_margin_cny: float
    project_net_cash_cny: float
    coverage_ratio: float
    pass_cash_positive: bool
    pass_cp01_1p2_gate: bool
    e_available_mwh: float
    e_source_used_mwh: float
    renewable_utilization: float
    ens_mwh: float
    h2_input_mwh: float
    h2_delivered_kg: float
    h2_power_shortfall_mwh: float
    terminal_inventory_value_included_cny: float
    reliability_note: str
    assumption_note: str


def read_summary() -> dict[str, float | str]:
    with SUMMARY_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        raise RuntimeError(f"Expected one annual summary row, got {len(rows)}.")
    row = rows[0]
    return {k: parse_value(v) for k, v in row.items()}


def parse_value(value: str) -> float | str:
    try:
        if value == "":
            return math.nan
        return float(value)
    except ValueError:
        return value


def read_hourly_rows() -> list[dict[str, float | str]]:
    with HOURLY_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: parse_value(v) for k, v in row.items()} for row in csv.DictReader(f)]


def fnum(row: dict[str, float | str], key: str) -> float:
    value = row.get(key, 0.0)
    if isinstance(value, str):
        return 0.0 if value == "" else float(value)
    if value != value:
        return 0.0
    return float(value)


def scaled_revenue_split(total_revenue_cny: float) -> dict[str, float]:
    base_total = sum(CP01_REVENUE_SPLIT_CNY.values())
    scale = total_revenue_cny / base_total
    return {name: value * scale for name, value in CP01_REVENUE_SPLIT_CNY.items()}


def replay_hydrogen(hourly_rows: list[dict[str, float | str]], cap_mw: float) -> ReplayResult:
    inventory = 0.0
    h2_input_mwh = 0.0
    h2_produced_kg = 0.0
    h2_delivered_kg = 0.0
    h2_power_served_mwh = 0.0
    h2_power_shortfall_mwh = 0.0
    minimum_inventory_kg = H2_STORAGE_CAP_KG
    maximum_inventory_kg = 0.0
    module_start_count = 0
    previous_modules_online = 0

    for row in hourly_rows:
        p_original_mw = fnum(row, "pElectrolyzerMW")
        p_ely_mw = min(p_original_mw, cap_mw)
        modules_online = int(math.ceil(p_ely_mw / ELECTROLYZER_MODULE_MW - 1e-12))
        module_start_count += max(0, modules_online - previous_modules_online)
        previous_modules_online = modules_online

        produced_kg = p_ely_mw * 1000.0 / SEC_KWH_PER_KG
        h2_input_mwh += p_ely_mw
        h2_produced_kg += produced_kg
        available_kg = inventory + produced_kg

        h2_power_request_mwh = fnum(row, "pH2PowerMW")
        h2_power_request_kg = (
            h2_power_request_mwh * 1000.0 / (H2_LHV_KWH_PER_KG * H2_POWER_EFFICIENCY)
            if h2_power_request_mwh > 0
            else 0.0
        )
        h2_power_used_kg = min(available_kg, h2_power_request_kg)
        h2_power_served = h2_power_used_kg * H2_LHV_KWH_PER_KG * H2_POWER_EFFICIENCY / 1000.0
        h2_power_served_mwh += h2_power_served
        h2_power_shortfall_mwh += max(0.0, h2_power_request_mwh - h2_power_served)
        available_kg -= h2_power_used_kg

        pipe_withdraw_request_kg = (
            fnum(row, "h2PipeDeliveredKg") / (1.0 - PIPE_LOSS)
            if fnum(row, "h2PipeDeliveredKg") > 0
            else 0.0
        )
        ship_withdraw_request_kg = (
            fnum(row, "h2ShipDeliveredKg") / (1.0 - SHIP_LOSS)
            if fnum(row, "h2ShipDeliveredKg") > 0
            else 0.0
        )
        pipe_withdraw_kg = min(available_kg, pipe_withdraw_request_kg)
        available_kg -= pipe_withdraw_kg
        ship_withdraw_kg = min(available_kg, ship_withdraw_request_kg)
        available_kg -= ship_withdraw_kg
        h2_delivered_kg += (
            pipe_withdraw_kg * (1.0 - PIPE_LOSS)
            + ship_withdraw_kg * (1.0 - SHIP_LOSS)
        )

        inventory = min(H2_STORAGE_CAP_KG, available_kg)
        minimum_inventory_kg = min(minimum_inventory_kg, inventory)
        maximum_inventory_kg = max(maximum_inventory_kg, inventory)

    variable_cost_cny = (
        h2_produced_kg * H2_VARIABLE_CNY_PER_KG
        + (h2_delivered_kg / (1.0 - PIPE_LOSS)) * H2_PIPE_TRANSPORT_CNY_PER_KG
        + 0.0 * H2_SHIP_TRANSPORT_CNY_PER_KG
        + h2_power_served_mwh * H2_POWER_VARIABLE_CNY_PER_MWH
        + module_start_count * ELECTROLYZER_START_CNY_PER_MODULE
    )
    return ReplayResult(
        electrolyzer_cap_mw=cap_mw,
        h2_input_mwh=h2_input_mwh,
        h2_produced_kg=h2_produced_kg,
        h2_delivered_kg=h2_delivered_kg,
        h2_power_served_mwh=h2_power_served_mwh,
        h2_power_shortfall_mwh=h2_power_shortfall_mwh,
        ending_inventory_kg=inventory,
        minimum_inventory_kg=minimum_inventory_kg,
        maximum_inventory_kg=maximum_inventory_kg,
        module_start_count=module_start_count,
        variable_cost_cny=variable_cost_cny,
    )


def build_scenarios(summary: dict[str, float | str], hourly_rows: list[dict[str, float | str]]) -> tuple[list[ScenarioResult], list[ReplayResult]]:
    total_revenue = float(summary["outputRevenueCNY"])
    total_cost = float(summary["operatingCostCNY"])
    split = scaled_revenue_split(total_revenue)

    source_cost = float(summary["eSourceUsedMWh"]) * SOURCE_OM_CNY_PER_MWH
    bess_cost = sum(fnum(row, "pBessDischargeMW") for row in hourly_rows) * BESS_DEGRADATION_CNY_PER_MWH
    phase1_operating_cost = source_cost + bess_cost

    current_margin = total_revenue - total_cost
    current_net = current_margin - TOTAL_ANNUAL_BURDEN_CNY

    phase1_floor_revenue = (
        split["power"] * 1.05
        + split["compute"]
        + split["marine"]
        + 40.0 * CNY_MILLION
        + 20.0 * CNY_MILLION
    )
    phase1_target_revenue = (
        split["power"] * 1.15
        + split["compute"]
        + split["marine"]
        + 80.0 * CNY_MILLION
        + 35.0 * CNY_MILLION
    )

    replay_20 = replay_hydrogen(hourly_rows, 20.0)
    replay_30 = replay_hydrogen(hourly_rows, 30.0)
    replay_100 = replay_hydrogen(hourly_rows, 100.0)
    replays = [replay_20, replay_30, replay_100]

    scenarios: list[ScenarioResult] = []
    scenarios.append(
        make_scenario(
            "baseline_full_heavy_asset",
            "现状：全量重资产边界",
            "original 8760h dispatch",
            TOTAL_ANNUAL_BURDEN_CNY,
            1.0,
            total_revenue,
            total_cost,
            float(summary["eAvailableMWh"]),
            float(summary["eSourceUsedMWh"]),
            float(summary["ensMWh"]),
            float(summary["eHydrogenInputMWh"]),
            float(summary["h2DeliveredKg"]),
            0.0,
            0.0,
            "保留原年度 ENS=0 证据。",
            "按当前全量资产 CAPEX、固定 O&M、融资和替换准备金核算。",
        )
    )
    scenarios.append(
        make_scenario(
            "cp01_phase1_floor_80pct_burden_reduction",
            "一期下限：轻资产但只降 80% 年化负担",
            "economic overlay on original 8760h ledger",
            TOTAL_ANNUAL_BURDEN_CNY * 0.20,
            0.20,
            phase1_floor_revenue,
            phase1_operating_cost,
            float(summary["eAvailableMWh"]),
            float(summary["eSourceUsedMWh"]),
            float(summary["ensMWh"]),
            0.0,
            0.0,
            math.nan,
            0.0,
            "不继承原年度 ENS=0 证据；去掉制氢/储氢后，台风过境氢转电 341.34 MWh 需由外部保供或备用合同替代。",
            "电力收入上浮 5%，算力容量费 4000 万元/年，海洋服务费 2000 万元/年；氢库存估值剔除。",
        )
    )
    scenarios.append(
        make_scenario(
            "cp01_phase1_target_88pct_burden_reduction",
            "一期目标边界：降 88% 年化负担",
            "economic overlay on original 8760h ledger",
            TOTAL_ANNUAL_BURDEN_CNY * 0.12,
            0.12,
            phase1_target_revenue,
            phase1_operating_cost,
            float(summary["eAvailableMWh"]),
            float(summary["eSourceUsedMWh"]),
            float(summary["ensMWh"]),
            0.0,
            0.0,
            math.nan,
            0.0,
            "不继承原年度 ENS=0 证据；这是收益边界测试，不是完整保供方案。",
            "电力收入上浮 15%，算力容量费 8000 万元/年，海洋服务费 3500 万元/年；氢业务暂不进入一期现金流。",
        )
    )
    scenarios.append(
        make_scenario(
            "cp01_phase1_target_90pct_burden_reduction",
            "一期转正边界：降 90% 年化负担",
            "economic overlay on original 8760h ledger",
            TOTAL_ANNUAL_BURDEN_CNY * 0.10,
            0.10,
            phase1_target_revenue,
            phase1_operating_cost,
            float(summary["eAvailableMWh"]),
            float(summary["eSourceUsedMWh"]),
            float(summary["ensMWh"]),
            0.0,
            0.0,
            math.nan,
            0.0,
            "不继承原年度 ENS=0 证据；经济上通过 1.2 安全系数门槛，但可靠性需另配备用服务。",
            "同一期目标合同收入；项目实际承担年化负担压到当前 10%。",
        )
    )

    h2_contract_price = 35.0
    phase2_revenue = phase1_target_revenue + replay_30.h2_delivered_kg * h2_contract_price
    phase2_cost = phase1_operating_cost + replay_30.variable_cost_cny
    scenarios.append(
        make_scenario(
            "cp01_phase2_30mw_h2_contract_88pct_burden_reduction",
            "二期：30 MW 模块化制氢 + 35 CNY/kg 承购",
            "hourly hydrogen replay with 30 MW electrolyzer cap",
            TOTAL_ANNUAL_BURDEN_CNY * 0.12,
            0.12,
            phase2_revenue,
            phase2_cost,
            float(summary["eAvailableMWh"]),
            float(summary["eSourceUsedMWh"]),
            float(summary["ensMWh"]) + replay_30.h2_power_shortfall_mwh,
            replay_30.h2_input_mwh,
            replay_30.h2_delivered_kg,
            replay_30.h2_power_shortfall_mwh,
            0.0,
            (
                "30 MW 回放氢转电短缺为 0，当前台风代理事件保供链条可继承。"
                if replay_30.h2_power_shortfall_mwh <= 1e-6
                else "30 MW 回放出现氢转电短缺，需提高 PEM/库存或另配备用。"
            ),
            "一期目标合同收入 + 氢只按实际交付确认收入；不确认期末库存价值。",
        )
    )
    return scenarios, replays


def make_scenario(
    scenario_id: str,
    scenario_name: str,
    dispatch_basis: str,
    annualized_burden_cny: float,
    burden_retained_fraction: float,
    revenue_cny: float,
    operating_cost_cny: float,
    e_available_mwh: float,
    e_source_used_mwh: float,
    ens_mwh: float,
    h2_input_mwh: float,
    h2_delivered_kg: float,
    h2_power_shortfall_mwh: float,
    terminal_inventory_value_included_cny: float,
    reliability_note: str,
    assumption_note: str,
) -> ScenarioResult:
    cash_margin = revenue_cny - operating_cost_cny + terminal_inventory_value_included_cny
    project_net = cash_margin - annualized_burden_cny
    coverage_ratio = cash_margin / annualized_burden_cny if annualized_burden_cny > 0 else math.inf
    return ScenarioResult(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        dispatch_basis=dispatch_basis,
        annualized_burden_cny=annualized_burden_cny,
        burden_retained_fraction=burden_retained_fraction,
        revenue_cny=revenue_cny,
        operating_cost_cny=operating_cost_cny,
        cash_margin_cny=cash_margin,
        project_net_cash_cny=project_net,
        coverage_ratio=coverage_ratio,
        pass_cash_positive=project_net >= 0,
        pass_cp01_1p2_gate=coverage_ratio >= 1.2,
        e_available_mwh=e_available_mwh,
        e_source_used_mwh=e_source_used_mwh,
        renewable_utilization=e_source_used_mwh / e_available_mwh if e_available_mwh > 0 else math.nan,
        ens_mwh=ens_mwh,
        h2_input_mwh=h2_input_mwh,
        h2_delivered_kg=h2_delivered_kg,
        h2_power_shortfall_mwh=h2_power_shortfall_mwh,
        terminal_inventory_value_included_cny=terminal_inventory_value_included_cny,
        reliability_note=reliability_note,
        assumption_note=assumption_note,
    )


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fmt_million(value: float) -> str:
    if value != value:
        return "NA"
    return f"{value / CNY_MILLION:,.3f}"


def write_markdown(scenarios: list[ScenarioResult], replays: list[ReplayResult], path: Path) -> None:
    lines = [
        "# CP01 收益转正方案仿真结果",
        "",
        "> 口径：读取当前有效年度台账 `annual_8760h_online_strategy_extreme`，对 CP01 轻资产、合同化和 30 MW 模块化制氢方案做经济边界与逐小时氢库存回放仿真。结果仍为模型输出和假设参数，不构成可研概算或投资承诺。",
        "",
        "## 方案对比",
        "",
        "| 方案 | 年化负担/百万元 | 收入/百万元 | 成本/百万元 | 现金毛收益/百万元 | 项目净现金/百万元 | 覆盖倍数 | 1.2门槛 |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for s in scenarios:
        lines.append(
            f"| {s.scenario_name} | {fmt_million(s.annualized_burden_cny)} | "
            f"{fmt_million(s.revenue_cny)} | {fmt_million(s.operating_cost_cny)} | "
            f"{fmt_million(s.cash_margin_cny)} | {fmt_million(s.project_net_cash_cny)} | "
            f"{s.coverage_ratio:.3f} | {'PASS' if s.pass_cp01_1p2_gate else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## 30 MW 制氢回放",
            "",
            "| 电解槽上限/MW | 制氢用电/MWh | 产氢/kg | 交付/kg | 氢转电/MWh | 氢转电短缺/MWh | 期末库存/kg | 最大库存/kg |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for r in replays:
        lines.append(
            f"| {r.electrolyzer_cap_mw:.0f} | {r.h2_input_mwh:,.3f} | "
            f"{r.h2_produced_kg:,.3f} | {r.h2_delivered_kg:,.3f} | "
            f"{r.h2_power_served_mwh:,.3f} | {r.h2_power_shortfall_mwh:,.3f} | "
            f"{r.ending_inventory_kg:,.3f} | {r.maximum_inventory_kg:,.3f} |"
        )
    lines.extend(
        [
            "",
            "## 解释",
            "",
            "- 现状全量重资产边界下，年度运行毛收益为正，但项目层净现金仍为大额负值。",
            "- 只做到 80% 年化负担下降仍不能转正；即使一期目标合同收入成立，88% 下降也只接近转正，未达到 1.2 安全系数。",
            "- 当实际承担年化负担压到当前约 10%，一期经济口径通过 1.2 门槛；但若完全去掉制氢/储氢，原年度台风代理事件的 ENS=0 证据不能直接继承。",
            "- 二期加入 30 MW 模块化制氢并按 35 CNY/kg 实际交付确认收入后，在 88% 年化负担下降口径下通过 1.2 门槛；该结果依赖氢承购价、交付需求和当前逐时回放假设。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = read_summary()
    hourly_rows = read_hourly_rows()
    scenarios, replays = build_scenarios(summary, hourly_rows)

    scenario_rows = [s.__dict__ for s in scenarios]
    scenario_fields = list(scenario_rows[0].keys())
    write_csv(OUT_DIR / "cp01_profit_turnaround_scenarios.csv", scenario_rows, scenario_fields)

    replay_rows = [r.__dict__ for r in replays]
    replay_fields = list(replay_rows[0].keys())
    write_csv(OUT_DIR / "cp01_hydrogen_module_replay.csv", replay_rows, replay_fields)
    write_markdown(scenarios, replays, OUT_DIR / "cp01_profit_turnaround_simulation.md")

    print("CP01 profit-turnaround simulation complete.")
    print(f"Results: {OUT_DIR}")
    for s in scenarios:
        print(
            f"{s.scenario_id}: net={s.project_net_cash_cny / CNY_MILLION:.3f} "
            f"million CNY, coverage={s.coverage_ratio:.3f}, "
            f"gate={'PASS' if s.pass_cp01_1p2_gate else 'FAIL'}"
        )


if __name__ == "__main__":
    main()
