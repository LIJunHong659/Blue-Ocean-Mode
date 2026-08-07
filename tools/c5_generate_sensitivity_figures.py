from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
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
    plt.tight_layout()
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

    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    ax.plot(plot_df["caseLabel"], plot_df["outputRevenueMCNY"], marker="o", linewidth=2.2, label="Output revenue")
    ax.plot(
        plot_df["caseLabel"],
        plot_df["cashOperatingMarginMCNY"],
        marker="s",
        linewidth=2.2,
        label="Cash margin",
    )
    ax.axhline(
        price.loc[price["caseLabel"] == "Base", "outputRevenueMCNY"].iloc[0],
        color="#8a8a8a",
        linewidth=1,
        linestyle="--",
        label="Base revenue",
    )
    ax.set_title("Fixed-dispatch price sensitivity")
    ax.set_ylabel("Million CNY per year")
    ax.set_xlabel("Repriced case")
    ax.grid(True, axis="y", alpha=0.28)
    ax.legend(ncol=3, loc="upper left")
    ax.tick_params(axis="x", rotation=20)
    savefig("c5_56_price_sensitivity_line.png")

    slope = price[price["caseLabel"].isin(["Power +10", "H2 +1", "Compute +100"])].copy()
    slope["deltaAbsMCNY"] = slope["revenueDeltaMCNY"].abs()
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.bar(slope["caseLabel"], slope["deltaAbsMCNY"], color=["#4878a8", "#59a14f", "#e15759"])
    ax.set_title("Annual revenue slope by unit price step")
    ax.set_ylabel("Revenue change, million CNY")
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
    colors = ["#59a14f" if x >= 0 else "#e15759" for x in plot_df["deltaProjectAnnualNetCashMCNY"]]
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.bar(plot_df["caseLabel"], plot_df["deltaProjectAnnualNetCashMCNY"], color=colors)
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_title("Lifecycle post-process net cash delta")
    ax.set_ylabel("Delta vs base, million CNY per year")
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
        label="Annualized burden",
    )
    ax1.set_xlabel("Distance to shore, km")
    ax1.set_ylabel("Annualized burden, million CNY")
    ax1.grid(True, alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(
        dist["distanceToShoreKm"],
        dist["projectAnnualNetCashMCNY"],
        marker="s",
        linewidth=2.2,
        color="#e15759",
        label="Project net cash",
    )
    ax2.set_ylabel("Project net cash, million CNY")
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="best")
    ax1.set_title("Distance CAPEX-only sensitivity")
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

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.0))
    metrics = [
        ("ensMWh", "ENS, MWh"),
        ("cashOperatingMarginMCNY", "Cash margin, million CNY"),
        ("eCableReceivedMWh", "Cable received, MWh"),
        ("eComputeServiceMWhCS", "Compute service, MWh-CS"),
    ]
    for ax, (col, title) in zip(axes.ravel(), metrics):
        ax.plot(s["caseLabel"], s[col], marker="o", linewidth=2.2)
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.25)
        ax.tick_params(axis="x", rotation=15)
    fig.suptitle("Annual boundary rerun KPI comparison", y=1.02, fontsize=14)
    savefig("c5_56_boundary_kpi_line_grid.png")

    relax = s[
        [
            "caseLabel",
            "planFallbackHours",
            "reserveConstraintRelaxationHours",
            "reliabilityRelaxationHours",
        ]
    ].set_index("caseLabel")
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    relax.plot(kind="bar", ax=ax, color=["#4878a8", "#f28e2b", "#e15759"])
    ax.set_title("Fallback and relaxation hours")
    ax.set_ylabel("Hours per year")
    ax.grid(True, axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=0)
    ax.legend(["Plan fallback", "Reserve relax", "Reliability relax"])
    savefig("c5_56_boundary_relaxation_bar.png")

    ghg = s[["caseLabel", "proxyNetGHGKtCO2e"]]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.bar(ghg["caseLabel"], ghg["proxyNetGHGKtCO2e"], color=["#4878a8", "#59a14f", "#e15759"])
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_title("Proxy net GHG")
    ax.set_ylabel("ktCO2e per year")
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
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    for label in ["Base", "Flex 50%", "Cable loss 12%"]:
        ax.plot(pivot["eventCode"], pivot[label], marker="o", linewidth=2.2, label=label)
    ax.set_title("ENS by event phase")
    ax.set_ylabel("ENS, MWh")
    ax.set_xlabel("Event phase")
    ax.grid(True, axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=15)
    ax.legend()
    savefig("c5_56_event_ens_line.png")

    rate = (
        events.pivot_table(index="eventCode", columns="caseLabel", values="criticalServiceRatePct", aggfunc="mean")
        .reindex(order)
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    for label in ["Base", "Flex 50%", "Cable loss 12%"]:
        ax.plot(rate["eventCode"], rate[label], marker="o", linewidth=2.2, label=label)
    ax.set_title("Critical service rate by event phase")
    ax.set_ylabel("Critical service rate, %")
    ax.set_xlabel("Event phase")
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
        ax.plot(part["hour"], part["cumCashMarginMCNY"], linewidth=2.0, label=label)
    ax.set_title("Annual cumulative cash margin")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Cumulative cash margin, million CNY")
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
        ax.plot(part["hour"], part["ensMWh"], linewidth=2.0, label=label)
    ax.set_title("Hourly ENS around extreme event")
    ax.set_xlabel("Hour")
    ax.set_ylabel("ENS, MWh")
    ax.grid(True, alpha=0.25)
    ax.legend()
    savefig("c5_56_hourly_typhoon_ens_line.png")

    base_window = window[window["caseLabel"] == "Base"].sort_values("hour")
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    for col, label in [
        ("eCableReceivedMWh", "Cable received"),
        ("eHydrogenInputMWh", "Hydrogen input"),
        ("eFlexibleComputeInputMWh", "Compute input"),
        ("eCurtailmentMWh", "Curtailment"),
    ]:
        ax.plot(base_window["hour"], base_window[col], linewidth=1.9, label=label)
    ax.set_title("Base dispatch channels around extreme event")
    ax.set_xlabel("Hour")
    ax.set_ylabel("MWh per hour")
    ax.grid(True, alpha=0.25)
    ax.legend(ncol=2)
    savefig("c5_56_hourly_base_event_dispatch_line.png")


def main() -> None:
    ensure_dirs()
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
