from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
C5 = ROOT / "C5"
RESULTS = (
    next(p for p in C5.iterdir() if p.is_dir() and p.name.startswith("5.7"))
    / "results"
    / "minimal_sensitivity_5_6"
)
BASE = (
    next(p for p in C5.iterdir() if p.is_dir() and p.name.startswith("5.7"))
    / "results"
    / "annual_8760h_online_strategy_extreme"
)
FIG_DIR = RESULTS / "figures"
PROC_DIR = RESULTS / "processed"


CASE_LABELS = {
    "base_price_anchor": "Base",
    "electricity_minus_10": "Power -10",
    "electricity_plus_10": "Power +10",
    "hydrogen_minus_1": "H2 -1",
    "hydrogen_plus_1": "H2 +1",
    "compute_minus_100": "Compute -100",
    "compute_plus_100": "Compute +100",
    "base_lifecycle_cost": "Base",
    "device_cost_minus20pct": "Device -20%",
    "device_cost_plus20pct": "Device +20%",
    "cable_asset_cost_minus20pct": "Cable -20%",
    "cable_asset_cost_plus20pct": "Cable +20%",
    "distance_100km_capex_only": "100 km",
    "distance_200km_capex_only": "200 km",
    "distance_300km_capex_only": "300 km",
    "model_online_prior_posterior_event_aware": "Base",
    "c5_56_flex_ratio_0p50": "Flex 50%",
    "c5_56_distance_loss_proxy_0p12": "Cable loss 12%",
}



CASE_DISPLAY_LABELS = {
    "Base": "基准",
    "Power -10": "电价 -10",
    "Power +10": "电价 +10",
    "H2 -1": "氢价 -1",
    "H2 +1": "氢价 +1",
    "Compute -100": "算力价 -100",
    "Compute +100": "算力价 +100",
    "Device -20%": "设备成本 -20%",
    "Device +20%": "设备成本 +20%",
    "Cable -20%": "海缆成本 -20%",
    "Cable +20%": "海缆成本 +20%",
    "100 km": "100 km",
    "200 km": "200 km",
    "300 km": "300 km",
    "Flex 50%": "柔性算力 50%",
    "Cable loss 12%": "海缆损耗 12%",
}

EVENT_DISPLAY_LABELS = {
    "NORMAL": "正常",
    "TYPHOON_WARNING": "台风预警",
    "TYPHOON_PASSAGE": "台风过境",
    "TYPHOON_RECOVERY": "恢复",
}


def configure_chinese_font() -> None:
    candidates = [
        ("Microsoft YaHei", Path("C:/Windows/Fonts/msyh.ttc")),
        ("SimHei", Path("C:/Windows/Fonts/simhei.ttf")),
        ("SimSun", Path("C:/Windows/Fonts/simsun.ttc")),
        ("Noto Sans CJK SC", None),
        ("Source Han Sans SC", None),
        ("Arial Unicode MS", None),
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for family, path in candidates:
        if family not in available and path is not None and path.exists():
            font_manager.fontManager.addfont(str(path))
            available = {f.name for f in font_manager.fontManager.ttflist}
        if family in available:
            plt.rcParams["font.sans-serif"] = [family, "DejaVu Sans"]
            break
    plt.rcParams["axes.unicode_minus"] = False


def display_case(label: str) -> str:
    return CASE_DISPLAY_LABELS.get(label, label)


def display_event(label: str) -> str:
    return EVENT_DISPLAY_LABELS.get(label, label)

def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def m_cny(series: pd.Series) -> pd.Series:
    return series / 1_000_000.0


def kt_co2e(series: pd.Series) -> pd.Series:
    return series / 1_000_000.0


def savefig(name: str) -> None:
    plt.tight_layout(rect=(0, 0, 1, 0.96))
    plt.savefig(FIG_DIR / name, dpi=180, bbox_inches="tight")
    plt.close()


def label_cases(df: pd.DataFrame, source_col: str = "caseId") -> pd.DataFrame:
    df = df.copy()
    df["caseLabel"] = df[source_col].map(CASE_LABELS).fillna(df[source_col])
    return df


def build_price_outputs() -> pd.DataFrame:
    price = label_cases(read_csv(RESULTS / "c5_56_fixed_dispatch_price_sensitivity.csv"))
    price["outputRevenueMCNY"] = m_cny(price["outputRevenueCNY"])
    price["cashOperatingMarginMCNY"] = m_cny(price["cashOperatingMarginCNY"])
    price["revenueDeltaMCNY"] = m_cny(price["revenueDeltaCNY"])
    price["netOperatingValueMCNY"] = m_cny(price["netOperatingValueCNY"])
    price["curtailmentPct"] = price["curtailmentRate"] * 100
    price["renewableUtilizationPct"] = price["renewableUtilization"] * 100
    keep = [
        "caseId",
        "caseLabel",
        "changedParameter",
        "electricityPriceCNYPerMWh",
        "hydrogenPriceCNYPerKg",
        "computePriceCNYPerMWhCS",
        "outputRevenueMCNY",
        "cashOperatingMarginMCNY",
        "revenueDeltaMCNY",
        "netOperatingValueMCNY",
        "renewableUtilizationPct",
        "curtailmentPct",
        "ensMWh",
    ]
    out = price[keep]
    out.to_csv(PROC_DIR / "c5_56_processed_price_cases.csv", index=False)
    return out


def plot_price(price: pd.DataFrame) -> None:
    order = [
        "Power -10",
        "Base",
        "Power +10",
        "H2 -1",
        "H2 +1",
        "Compute -100",
        "Compute +100",
    ]
    plot_df = price.set_index("caseLabel").loc[order].reset_index()
    plot_df["displayLabel"] = plot_df["caseLabel"].map(display_case)

    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    ax.plot(plot_df["displayLabel"], plot_df["outputRevenueMCNY"], marker="o", linewidth=2.2, label="输出收入")
    ax.plot(
        plot_df["displayLabel"],
        plot_df["cashOperatingMarginMCNY"],
        marker="s",
        linewidth=2.2,
        label="现金运行毛收益",
    )
    ax.axhline(
        price.loc[price["caseLabel"] == "Base", "outputRevenueMCNY"].iloc[0],
        color="#8a8a8a",
        linewidth=1,
        linestyle="--",
        label="基准输出收入",
    )
    ax.set_title("固定调度重定价敏感性")
    ax.set_ylabel("年度金额（百万元）")
    ax.set_xlabel("重定价场景")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(ncol=3, loc="upper left")
    ax.tick_params(axis="x", rotation=20)
    savefig("c5_56_price_sensitivity_line.png")

    slope = price[price["caseLabel"].isin(["Power +10", "H2 +1", "Compute +100"])].copy()
    slope["deltaAbsMCNY"] = slope["revenueDeltaMCNY"].abs()
    slope["displayLabel"] = slope["caseLabel"].map(display_case)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.bar(slope["displayLabel"], slope["deltaAbsMCNY"], color=["#4878a8", "#59a14f", "#e15759"])
    ax.set_title("单位价格步长的年度收入斜率")
    ax.set_ylabel("年度收入变化（百万元）")
    ax.grid(True, axis="y", alpha=0.25)
    for idx, value in enumerate(slope["deltaAbsMCNY"]):
        ax.text(idx, value + 0.3, f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    savefig("c5_56_price_slope_bar.png")


def build_cost_outputs() -> pd.DataFrame:
    cost = label_cases(read_csv(RESULTS / "c5_56_fixed_dispatch_cost_sensitivity.csv"))
    cost["annualizedInvestmentBurdenMCNY"] = m_cny(cost["annualizedInvestmentBurdenCNY"])
    cost["cashOperatingMarginMCNY"] = m_cny(cost["cashOperatingMarginCNY"])
    cost["projectAnnualNetCashMCNY"] = m_cny(cost["projectAnnualNetCashCNY"])
    cost["deltaProjectAnnualNetCashMCNY"] = m_cny(cost["deltaProjectAnnualNetCashCNY"])
    cost["grossCapexBCNY"] = cost["grossCapexCNY"] / 1_000_000_000.0
    keep = [
        "caseId",
        "caseLabel",
        "parameterGroup",
        "distanceToShoreKm",
        "costMultiplier",
        "grossCapexBCNY",
        "annualizedInvestmentBurdenMCNY",
        "cashOperatingMarginMCNY",
        "projectAnnualNetCashMCNY",
        "deltaProjectAnnualNetCashMCNY",
    ]
    out = cost[keep]
    out.to_csv(PROC_DIR / "c5_56_processed_cost_cases.csv", index=False)
    return out


def plot_cost(cost: pd.DataFrame) -> None:
    groups = [
        "Device -20%",
        "Device +20%",
        "Cable -20%",
        "Cable +20%",
        "100 km",
        "200 km",
        "300 km",
    ]
    plot_df = cost.set_index("caseLabel").loc[groups].reset_index()
    plot_df["displayLabel"] = plot_df["caseLabel"].map(display_case)
    colors = ["#59a14f" if x >= 0 else "#e15759" for x in plot_df["deltaProjectAnnualNetCashMCNY"]]
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.bar(plot_df["displayLabel"], plot_df["deltaProjectAnnualNetCashMCNY"], color=colors)
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_title("生命周期后处理净现金变化")
    ax.set_ylabel("相对基准净现金变化（百万元/年）")
    ax.grid(True, axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=20)
    savefig("c5_56_cost_delta_bar.png")

    dist = cost[cost["parameterGroup"] == "distance_cable_capex"].sort_values("distanceToShoreKm")
    fig, ax1 = plt.subplots(figsize=(8.8, 5.2))
    ax1.plot(
        dist["distanceToShoreKm"],
        dist["annualizedInvestmentBurdenMCNY"],
        marker="o",
        linewidth=2.2,
        color="#4878a8",
        label="年化投资负担",
    )
    ax1.set_xlabel("离岸距离（km）")
    ax1.set_ylabel("年化投资负担（百万元）")
    ax1.grid(True, alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(
        dist["distanceToShoreKm"],
        dist["projectAnnualNetCashMCNY"],
        marker="s",
        linewidth=2.2,
        color="#e15759",
        label="项目年度净现金",
    )
    ax2.set_ylabel("项目年度净现金（百万元）")
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="best")
    ax1.set_title("离岸距离 CAPEX 代理敏感性")
    savefig("c5_56_distance_capex_line.png")


def read_boundary_summary() -> pd.DataFrame:
    base = read_csv(BASE / "c5_annual_online_strategy_summary_with_ghg.csv")
    flex = read_csv(RESULTS / "annual_dispatch_boundary_cases" / "flex_ratio_0p50" / "c5_56_boundary_summary.csv")
    loss = read_csv(RESULTS / "annual_dispatch_boundary_cases" / "distance_loss_proxy_0p12" / "c5_56_boundary_summary.csv")
    out = pd.concat([base, flex, loss], ignore_index=True, sort=False)
    out = label_cases(out, source_col="strategyId")
    out["cashOperatingMarginCNY"] = out["outputRevenueCNY"] - out["operatingCostCNY"]
    for col in ["outputRevenueCNY", "operatingCostCNY", "cashOperatingMarginCNY"]:
        out[col.replace("CNY", "MCNY")] = m_cny(out[col])
    out["criticalServiceRatePct"] = out["criticalServiceRate"] * 100
    out["renewableUtilizationPct"] = out["eSourceUsedMWh"] / out["eAvailableMWh"] * 100
    out["curtailmentRatePct"] = out["eCurtailmentMWh"] / out["eAvailableMWh"] * 100
    out["proxyNetGHGKtCO2e"] = kt_co2e(out["proxyNetGHGKgCO2e"])

    base_row = out[out["caseLabel"] == "Base"].iloc[0]
    delta_cols = [
        "eSourceUsedMWh",
        "eCurtailmentMWh",
        "eCableReceivedMWh",
        "eHydrogenInputMWh",
        "eComputeServiceMWhCS",
        "ensMWh",
        "outputRevenueMCNY",
        "operatingCostMCNY",
        "cashOperatingMarginMCNY",
        "planFallbackHours",
        "reserveConstraintRelaxationHours",
        "reliabilityRelaxationHours",
        "criticalServiceRatePct",
        "proxyNetGHGKtCO2e",
    ]
    for col in delta_cols:
        out[f"delta_{col}"] = out[col] - base_row[col]
        denom = base_row[col]
        if isinstance(denom, (int, float)) and not math.isclose(float(denom), 0.0):
            out[f"deltaPct_{col}"] = out[f"delta_{col}"] / denom * 100
        else:
            out[f"deltaPct_{col}"] = pd.NA

    keep = [
        "strategyId",
        "caseLabel",
        "sensitivityCaseId",
        "eSourceUsedMWh",
        "eCurtailmentMWh",
        "eCableReceivedMWh",
        "eHydrogenInputMWh",
        "eComputeServiceMWhCS",
        "ensMWh",
        "outputRevenueMCNY",
        "operatingCostMCNY",
        "cashOperatingMarginMCNY",
        "planFallbackHours",
        "reserveConstraintRelaxationHours",
        "reliabilityRelaxationHours",
        "criticalServiceRatePct",
        "renewableUtilizationPct",
        "curtailmentRatePct",
        "proxyNetGHGKtCO2e",
    ] + [c for c in out.columns if c.startswith("delta_") or c.startswith("deltaPct_")]
    out[keep].to_csv(PROC_DIR / "c5_56_processed_boundary_kpi_delta.csv", index=False)
    return out


def plot_boundary(summary: pd.DataFrame) -> None:
    order = ["Base", "Flex 50%", "Cable loss 12%"]
    s = summary.set_index("caseLabel").loc[order].reset_index()
    s["displayLabel"] = s["caseLabel"].map(display_case)

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0))
    metrics = [
        ("ensMWh", "ENS（MWh）"),
        ("cashOperatingMarginMCNY", "现金运行毛收益（百万元）"),
        ("eCableReceivedMWh", "海缆受端电量（MWh）"),
        ("eComputeServiceMWhCS", "算力服务量（MWh-CS）"),
    ]
    for ax, (col, title) in zip(axes.ravel(), metrics):
        ax.plot(s["displayLabel"], s[col], marker="o", linewidth=2.2)
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.25)
        ax.tick_params(axis="x", rotation=15)
    fig.suptitle("年度边界重跑关键指标对比", y=1.02, fontsize=14)
    savefig("c5_56_boundary_kpi_line_grid.png")

    relax = s[[
        "displayLabel",
        "planFallbackHours",
        "reserveConstraintRelaxationHours",
        "reliabilityRelaxationHours",
    ]].set_index("displayLabel")
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    relax.plot(kind="bar", ax=ax, color=["#4878a8", "#f28e2b", "#e15759"])
    ax.set_title("计划回退与约束松弛小时数")
    ax.set_ylabel("年度小时数")
    ax.grid(True, axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=0)
    ax.legend(["计划回退", "储备松弛", "可靠性松弛"])
    savefig("c5_56_boundary_relaxation_bar.png")

    ghg = s[["displayLabel", "proxyNetGHGKtCO2e"]]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.bar(ghg["displayLabel"], ghg["proxyNetGHGKtCO2e"], color=["#4878a8", "#59a14f", "#e15759"])
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_title("净碳代理对比")
    ax.set_ylabel("ktCO2e/年")
    ax.grid(True, axis="y", alpha=0.25)
    savefig("c5_56_boundary_proxy_ghg_bar.png")


def read_event_summary() -> pd.DataFrame:
    base = read_csv(BASE / "c5_annual_online_strategy_event_summary.csv")
    flex = read_csv(RESULTS / "annual_dispatch_boundary_cases" / "flex_ratio_0p50" / "c5_56_boundary_event_summary.csv")
    loss = read_csv(RESULTS / "annual_dispatch_boundary_cases" / "distance_loss_proxy_0p12" / "c5_56_boundary_event_summary.csv")
    out = pd.concat([base, flex, loss], ignore_index=True, sort=False)
    out = label_cases(out, source_col="strategyId")
    out["outputRevenueMCNY"] = m_cny(out["outputRevenueCNY"])
    out["operatingCostMCNY"] = m_cny(out["operatingCostCNY"])
    out["netGHGKtCO2e"] = kt_co2e(out["netGHGKgCO2e"])
    out["criticalServiceRatePct"] = out["criticalServiceRate"] * 100
    out.to_csv(PROC_DIR / "c5_56_processed_event_summary.csv", index=False)
    return out


def plot_events(events: pd.DataFrame) -> None:
    order = ["NORMAL", "TYPHOON_WARNING", "TYPHOON_PASSAGE", "TYPHOON_RECOVERY"]
    pivot = (
        events.pivot_table(index="eventCode", columns="caseLabel", values="ensMWh", aggfunc="sum")
        .reindex(order)
        .reset_index()
    )
    pivot["displayEvent"] = pivot["eventCode"].map(display_event)
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    for label in ["Base", "Flex 50%", "Cable loss 12%"]:
        ax.plot(pivot["displayEvent"], pivot[label], marker="o", linewidth=2.2, label=display_case(label))
    ax.set_title("分事件阶段 ENS")
    ax.set_ylabel("ENS（MWh）")
    ax.set_xlabel("事件阶段")
    ax.grid(True, axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=15)
    ax.legend()
    savefig("c5_56_event_ens_line.png")

    rate = (
        events.pivot_table(index="eventCode", columns="caseLabel", values="criticalServiceRatePct", aggfunc="mean")
        .reindex(order)
        .reset_index()
    )
    rate["displayEvent"] = rate["eventCode"].map(display_event)
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    for label in ["Base", "Flex 50%", "Cable loss 12%"]:
        ax.plot(rate["displayEvent"], rate[label], marker="o", linewidth=2.2, label=display_case(label))
    ax.set_title("分事件阶段关键负荷服务率")
    ax.set_ylabel("关键负荷服务率（%）")
    ax.set_xlabel("事件阶段")
    ax.grid(True, axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=15)
    ax.legend()
    savefig("c5_56_event_service_rate_line.png")


def read_hourly() -> pd.DataFrame:
    base = read_csv(BASE / "c5_annual_online_strategy_hourly_with_ghg.csv")
    flex = read_csv(RESULTS / "annual_dispatch_boundary_cases" / "flex_ratio_0p50" / "c5_56_boundary_hourly.csv")
    loss = read_csv(RESULTS / "annual_dispatch_boundary_cases" / "distance_loss_proxy_0p12" / "c5_56_boundary_hourly.csv")
    out = pd.concat([base, flex, loss], ignore_index=True, sort=False)
    out = label_cases(out, source_col="strategyId")
    if "hour" not in out.columns:
        out["hour"] = out.groupby("caseLabel").cumcount() + 1
    out["cashMarginCNY"] = out["outputRevenueCNY"] - out["operatingCostCNY"]
    out["cashMarginMCNY"] = out["cashMarginCNY"] / 1_000_000.0
    out["cumCashMarginMCNY"] = out.groupby("caseLabel")["cashMarginMCNY"].cumsum()
    out["cumENSMWh"] = out.groupby("caseLabel")["ensMWh"].cumsum()
    compact_cols = [
        "caseLabel",
        "strategyId",
        "hour",
        "eventCode",
        "eSourceUsedMWh",
        "eCableReceivedMWh",
        "eHydrogenInputMWh",
        "eFlexibleComputeInputMWh",
        "eCurtailmentMWh",
        "ensMWh",
        "cashMarginMCNY",
        "cumCashMarginMCNY",
        "cumENSMWh",
    ]
    out[compact_cols].to_csv(PROC_DIR / "c5_56_processed_hourly_compact.csv", index=False)
    return out


def plot_hourly(hourly: pd.DataFrame) -> None:
    order = ["Base", "Flex 50%", "Cable loss 12%"]
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    for label in order:
        part = hourly[hourly["caseLabel"] == label].sort_values("hour")
        ax.plot(part["hour"], part["cumCashMarginMCNY"], linewidth=2.0, label=display_case(label))
    ax.set_title("全年累计现金运行毛收益")
    ax.set_xlabel("小时")
    ax.set_ylabel("累计现金运行毛收益（百万元）")
    ax.grid(True, alpha=0.25)
    ax.legend()
    savefig("c5_56_hourly_cumulative_cash_margin_line.png")

    event_hours = hourly.loc[hourly["eventCode"] != "NORMAL", "hour"]
    if not event_hours.empty:
        start = max(int(event_hours.min()) - 24, 1)
        end = min(int(event_hours.max()) + 24, int(hourly["hour"].max()))
    else:
        start, end = 1, 168
    window = hourly[(hourly["hour"] >= start) & (hourly["hour"] <= end)].copy()

    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    for label in order:
        part = window[window["caseLabel"] == label].sort_values("hour")
        ax.plot(part["hour"], part["ensMWh"], linewidth=2.0, label=display_case(label))
    ax.set_title("极端事件窗口逐时 ENS")
    ax.set_xlabel("小时")
    ax.set_ylabel("ENS（MWh）")
    ax.grid(True, alpha=0.25)
    ax.legend()
    savefig("c5_56_hourly_typhoon_ens_line.png")

    base_window = window[window["caseLabel"] == "Base"].sort_values("hour")
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    for col, label in [
        ("eCableReceivedMWh", "海缆受端"),
        ("eHydrogenInputMWh", "制氢投入"),
        ("eFlexibleComputeInputMWh", "算力投入"),
        ("eCurtailmentMWh", "弃能"),
    ]:
        ax.plot(base_window["hour"], base_window[col], linewidth=1.9, label=label)
    ax.set_title("基准场景极端事件窗口调度通道")
    ax.set_xlabel("小时")
    ax.set_ylabel("每小时电量（MWh）")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=2)
    savefig("c5_56_hourly_base_event_dispatch_line.png")


def main() -> None:
    ensure_dirs()
    configure_chinese_font()
    price = build_price_outputs()
    plot_price(price)
    cost = build_cost_outputs()
    plot_cost(cost)
    summary = read_boundary_summary()
    plot_boundary(summary)
    events = read_event_summary()
    plot_events(events)
    hourly = read_hourly()
    plot_hourly(hourly)
    print(f"Figures written to: {FIG_DIR}")
    print(f"Processed CSV written to: {PROC_DIR}")


if __name__ == "__main__":
    main()
