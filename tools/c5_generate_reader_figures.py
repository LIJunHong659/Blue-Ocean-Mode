from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
C5 = ROOT / "C5"
FIG_DIR = C5 / "figures"

TYPICAL_DIR = (
    C5
    / "5.3对比方案与模型最优策略"
    / "results"
    / "typical_normal_48h_four_strategy"
)
ANNUAL_BASELINE_DIR = (
    C5 / "5.2三大基准方案" / "results" / "annual_asset_baselines_causal"
)
ANNUAL_ONLINE_DIR = (
    C5
    / "5.7混合最优策略短测试与年度运营分析"
    / "results"
    / "annual_8760h_online_strategy_extreme"
)


STRATEGY_LABELS = {
    "baseline_E_asset_only": "纯电基准",
    "baseline_H_asset_only": "纯氢基准",
    "baseline_C_asset_only": "纯算基准",
    "model_online_prior_posterior_event_aware": "在线混合策略",
}

EVENT_LABELS = {
    "NORMAL": "正常运行",
    "TYPHOON_WARNING": "台风预警",
    "TYPHOON_PASSAGE": "台风过境",
    "TYPHOON_RECOVERY": "恢复阶段",
}


def configure_chinese_font() -> None:
    candidates = [
        ("Microsoft YaHei", Path("C:/Windows/Fonts/msyh.ttc")),
        ("SimHei", Path("C:/Windows/Fonts/simhei.ttf")),
        ("SimSun", Path("C:/Windows/Fonts/simsun.ttc")),
        ("Noto Sans CJK SC", None),
        ("Source Han Sans SC", None),
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


def savefig(name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIG_DIR / name, dpi=180, bbox_inches="tight")
    plt.close()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def label_strategies(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["strategyLabel"] = out["strategyId"].map(STRATEGY_LABELS).fillna(out["strategyId"])
    return out


def plot_48h_scenario_inputs() -> None:
    inputs = read_csv(TYPICAL_DIR / "c5_typical48_selected_scenario_input.csv")
    hourly = read_csv(TYPICAL_DIR / "c5_typical48_four_strategy_hourly.csv")
    online = hourly[hourly["strategyId"] == "model_online_prior_posterior_event_aware"].copy()
    inputs["hour"] = range(1, len(inputs) + 1)
    online["hour"] = online["timeH"] + 1

    fig, axes = plt.subplots(3, 1, figsize=(11.5, 9.0), sharex=True)

    axes[0].plot(inputs["hour"], inputs["windSpeedMean10mMS"], label="场景平均风速", linewidth=2.0)
    axes[0].plot(inputs["hour"], inputs["nasaWind50mMS"], label="公开数据50 m风速", linewidth=1.6)
    axes[0].set_ylabel("风速（m/s）")
    axes[0].set_title("正常典型48 h场景输入")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(loc="upper left", ncol=2)

    axes[1].stackplot(
        online["hour"],
        online["pWindAvailableMW"],
        online["pPVAvailableMW"],
        online["pTidalAvailableMW"],
        labels=["风电可用", "光伏可用", "潮流可用"],
        colors=["#4e79a7", "#f2c14e", "#59a14f"],
        alpha=0.85,
    )
    axes[1].set_ylabel("可用功率（MW）")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(loc="upper left", ncol=3)

    axes[2].plot(inputs["hour"], inputs["flexComputeArrivalMWIT"], label="柔性算力到达量", linewidth=2.0, color="#e15759")
    axes[2].plot(inputs["hour"], inputs["rigidComputeArrivalMWIT"], label="基础算力到达量", linewidth=1.8, color="#b07aa1")
    axes[2].plot(inputs["hour"], inputs["tidalSpeedProxyMS"], label="潮流速度代理", linewidth=1.8, color="#76b7b2")
    axes[2].set_xlabel("小时")
    axes[2].set_ylabel("MW 或 m/s")
    axes[2].grid(True, alpha=0.25)
    axes[2].legend(loc="upper left", ncol=3)

    savefig("c5_51_48h_scenario_inputs.png")


def plot_48h_results() -> None:
    hourly = read_csv(TYPICAL_DIR / "c5_typical48_four_strategy_hourly.csv")
    summary = label_strategies(read_csv(TYPICAL_DIR / "c5_typical48_four_strategy_summary_with_ghg.csv"))
    online = hourly[hourly["strategyId"] == "model_online_prior_posterior_event_aware"].copy()
    online["hour"] = online["timeH"] + 1

    fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.4), sharex=True)
    axes[0].plot(online["hour"], online["pSourceAvailableMW"], label="可用新能源", linewidth=2.0)
    axes[0].plot(online["hour"], online["pSourceUsedMW"], label="已利用新能源", linewidth=2.0)
    axes[0].plot(online["hour"], online["pCurtailmentMW"], label="弃能", linewidth=1.8)
    axes[0].set_title("在线混合策略48 h逐小时表现")
    axes[0].set_ylabel("功率（MW）")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(loc="upper left", ncol=3)

    axes[1].stackplot(
        online["hour"],
        online["pCableSendMW"],
        online["pElectrolyzerMW"],
        online["pComputeFacilityMW"],
        labels=["电力外送", "制氢", "柔性算力"],
        colors=["#4e79a7", "#59a14f", "#e15759"],
        alpha=0.85,
    )
    axes[1].plot(online["hour"], online["bessSOC"] * 100, label="储能电量状态（%）", color="#7f7f7f", linewidth=1.6)
    axes[1].set_xlabel("小时")
    axes[1].set_ylabel("功率（MW）或状态（%）")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(loc="upper left", ncol=4)
    savefig("c5_54_48h_hourly_dispatch.png")

    summary["utilizationPct"] = summary["eSourceUsedMWh"] / summary["eAvailableMWh"] * 100
    summary["curtailmentRatePct"] = summary["eCurtailmentMWh"] / summary["eAvailableMWh"] * 100
    summary["cashMarginMCNY"] = (summary["outputRevenueCNY"] - summary["operatingCostCNY"]) / 1_000_000

    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.4))
    metrics = [
        ("utilizationPct", "新能源消纳率（%）"),
        ("curtailmentRatePct", "弃电率（%）"),
        ("cashMarginMCNY", "现金运行毛收益（百万元）"),
    ]
    colors = ["#4e79a7", "#59a14f", "#f28e2b", "#e15759"]
    for ax, (col, title) in zip(axes, metrics):
        ax.bar(summary["strategyLabel"], summary[col], color=colors)
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.25)
        ax.tick_params(axis="x", rotation=20)
        for idx, value in enumerate(summary[col]):
            ax.text(idx, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)
    savefig("c5_54_48h_strategy_bars.png")


def plot_annual_results() -> None:
    online = read_csv(ANNUAL_ONLINE_DIR / "c5_annual_online_strategy_hourly.csv")
    online["hour"] = online["timeH"] + 1
    event_hours = online.loc[online["eventCode"] != "NORMAL", "hour"]

    fig, axes = plt.subplots(2, 1, figsize=(12.5, 7.6), sharex=True)
    for col, label, color in [
        ("pSourceAvailableMW", "可用新能源", "#4e79a7"),
        ("pSourceUsedMW", "已利用新能源", "#59a14f"),
        ("pCurtailmentMW", "弃能", "#e15759"),
    ]:
        smooth = online[col].rolling(24, min_periods=1).mean()
        axes[0].plot(online["hour"], smooth, label=label, linewidth=1.7, color=color)
    if not event_hours.empty:
        axes[0].axvspan(event_hours.min(), event_hours.max(), color="#f28e2b", alpha=0.16, label="台风代理事件")
    axes[0].set_title("年度8760 h逐小时运行表现（24 h平滑）")
    axes[0].set_ylabel("功率（MW）")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(loc="upper left", ncol=4)

    for col, label in [
        ("pCableSendMW", "电力外送"),
        ("pElectrolyzerMW", "制氢"),
        ("pComputeFacilityMW", "柔性算力"),
    ]:
        smooth = online[col].rolling(24, min_periods=1).mean()
        axes[1].plot(online["hour"], smooth, label=label, linewidth=1.7)
    if not event_hours.empty:
        axes[1].axvspan(event_hours.min(), event_hours.max(), color="#f28e2b", alpha=0.16)
    axes[1].set_xlabel("小时")
    axes[1].set_ylabel("功率（MW）")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(loc="upper left", ncol=3)
    savefig("c5_54_8760_hourly_profile.png")

    if not event_hours.empty:
        start = max(int(event_hours.min()) - 24, 1)
        end = min(int(event_hours.max()) + 24, int(online["hour"].max()))
    else:
        start, end = 1, 168
    window = online[(online["hour"] >= start) & (online["hour"] <= end)].copy()
    window["eventLabel"] = window["eventCode"].map(EVENT_LABELS).fillna(window["eventCode"])

    fig, axes = plt.subplots(2, 1, figsize=(12.0, 7.2), sharex=True)
    for col, label in [
        ("pSourceAvailableMW", "可用新能源"),
        ("pSourceUsedMW", "已利用新能源"),
        ("pCurtailmentMW", "弃能"),
        ("ensMWh", "缺供电量"),
    ]:
        axes[0].plot(window["hour"], window[col], label=label, linewidth=1.9)
    axes[0].set_title("台风代理事件窗口逐小时表现")
    axes[0].set_ylabel("MW 或 MWh")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(loc="upper left", ncol=4)

    for col, label in [
        ("pCableSendMW", "电力外送"),
        ("pElectrolyzerMW", "制氢"),
        ("pComputeFacilityMW", "柔性算力"),
        ("bessSOC", "储能电量状态"),
    ]:
        series = window[col] * 100 if col == "bessSOC" else window[col]
        axes[1].plot(window["hour"], series, label=label, linewidth=1.9)
    axes[1].set_xlabel("小时")
    axes[1].set_ylabel("MW 或 %")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(loc="upper left", ncol=4)
    savefig("c5_54_8760_event_window.png")


def plot_55_kpis() -> None:
    s48 = label_strategies(read_csv(TYPICAL_DIR / "c5_typical48_four_strategy_summary_with_ghg.csv"))
    annual_base = read_csv(ANNUAL_BASELINE_DIR / "c5_annual_four_strategy_summary_with_ghg.csv")
    annual_online = read_csv(ANNUAL_ONLINE_DIR / "c5_annual_online_strategy_summary_with_ghg.csv")
    annual = label_strategies(pd.concat([annual_base, annual_online], ignore_index=True, sort=False))

    for df in (s48, annual):
        df["curtailmentRatePct"] = df["eCurtailmentMWh"] / df["eAvailableMWh"] * 100
        df["cashMarginMCNY"] = (df["outputRevenueCNY"] - df["operatingCostCNY"]) / 1_000_000
        df["proxyNetGHGTCO2e"] = df["proxyNetGHGKgCO2e"] / 1_000

    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.0))
    panels = [
        (s48, "cashMarginMCNY", "48 h现金运行毛收益（百万元）"),
        (s48, "curtailmentRatePct", "48 h弃电率（%）"),
        (annual, "cashMarginMCNY", "年度现金运行毛收益（百万元）"),
        (annual, "curtailmentRatePct", "年度弃电率（%）"),
    ]
    for ax, (df, col, title) in zip(axes.ravel(), panels):
        ax.bar(df["strategyLabel"], df[col], color=["#4e79a7", "#59a14f", "#f28e2b", "#e15759"][: len(df)])
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.25)
        ax.tick_params(axis="x", rotation=18)
        for idx, value in enumerate(df[col]):
            ax.text(idx, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)
    savefig("c5_55_economy_curtailment_bars.png")

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.4))
    for ax, df, title in [
        (axes[0], s48, "48 h净碳代理（tCO2e）"),
        (axes[1], annual, "年度净碳代理（tCO2e）"),
    ]:
        values = df["proxyNetGHGTCO2e"]
        colors = ["#59a14f" if value < 0 else "#e15759" for value in values]
        ax.bar(df["strategyLabel"], values, color=colors)
        ax.axhline(0, color="#333333", linewidth=1)
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.25)
        ax.tick_params(axis="x", rotation=18)
    savefig("c5_55_carbon_proxy_bars.png")


def write_summary_csv() -> None:
    s48 = label_strategies(read_csv(TYPICAL_DIR / "c5_typical48_four_strategy_summary_with_ghg.csv"))
    annual_base = read_csv(ANNUAL_BASELINE_DIR / "c5_annual_four_strategy_summary_with_ghg.csv")
    annual_online = read_csv(ANNUAL_ONLINE_DIR / "c5_annual_online_strategy_summary_with_ghg.csv")
    annual = label_strategies(pd.concat([annual_base, annual_online], ignore_index=True, sort=False))
    s48["horizon"] = "48h"
    annual["horizon"] = "8760h"
    out = pd.concat([s48, annual], ignore_index=True, sort=False)
    out["curtailmentRatePct"] = out["eCurtailmentMWh"] / out["eAvailableMWh"] * 100
    out["cashMarginMCNY"] = (out["outputRevenueCNY"] - out["operatingCostCNY"]) / 1_000_000
    out["proxyNetGHGTCO2e"] = out["proxyNetGHGKgCO2e"] / 1_000
    cols = [
        "horizon",
        "strategyLabel",
        "eAvailableMWh",
        "eSourceUsedMWh",
        "eCurtailmentMWh",
        "curtailmentRatePct",
        "ensMWh",
        "cashMarginMCNY",
        "proxyNetGHGTCO2e",
    ]
    out[cols].to_csv(FIG_DIR / "c5_reader_kpi_summary.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    configure_chinese_font()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plot_48h_scenario_inputs()
    plot_48h_results()
    plot_annual_results()
    plot_55_kpis()
    write_summary_csv()
    print(f"reader figures written to: {FIG_DIR}")


if __name__ == "__main__":
    main()
