# C5 5.6 Minimal-Rerun Sensitivity Pack

This pack separates fixed-dispatch post-processing from slow annual dispatch reruns.

## Price Slopes

| Parameter | Unit step | Annual revenue change / million CNY |
|---|---:|---:|
| electricity_price | +10 CNY/MWh received | 7.377 |
| hydrogen_price | +1 CNY/kg delivered | 4.404 |
| compute_price | +100 CNY/MWh-CS | 18.740 |

## Fixed Dispatch Price Cases

| Case | Revenue / million CNY | Cash margin / million CNY | ENS / MWh |
|---|---:|---:|---:|
| base_price_anchor | 1404.611 | 1312.468 | 2248.455 |
| electricity_minus_10 | 1397.234 | 1305.092 | 2248.455 |
| electricity_plus_10 | 1411.987 | 1319.845 | 2248.455 |
| hydrogen_minus_1 | 1400.207 | 1308.064 | 2248.455 |
| hydrogen_plus_1 | 1409.015 | 1316.872 | 2248.455 |
| compute_minus_100 | 1385.871 | 1293.728 | 2248.455 |
| compute_plus_100 | 1423.350 | 1331.208 | 2248.455 |

## Fixed Dispatch Cost Cases

| Case | Method | Annualized investment burden / million CNY | Project annual net cash / million CNY |
|---|---|---:|---:|
| base_lifecycle_cost | FIXED_DISPATCH_LIFECYCLE_POSTPROCESS | 3670.660 | -2358.192 |
| device_cost_minus20pct | FIXED_DISPATCH_ANNUALIZED_BURDEN_REPRICE | 3022.526 | -1710.058 |
| device_cost_plus20pct | FIXED_DISPATCH_ANNUALIZED_BURDEN_REPRICE | 4318.794 | -3006.326 |
| cable_asset_cost_minus20pct | FIXED_DISPATCH_ANNUALIZED_BURDEN_REPRICE | 3584.662 | -2272.194 |
| cable_asset_cost_plus20pct | FIXED_DISPATCH_ANNUALIZED_BURDEN_REPRICE | 3756.658 | -2444.190 |
| distance_100km_capex_only | FIXED_DISPATCH_DISTANCE_CAPEX_ONLY | 3596.987 | -2284.518 |
| distance_200km_capex_only | FIXED_DISPATCH_DISTANCE_CAPEX_ONLY | 3670.660 | -2358.192 |
| distance_300km_capex_only | FIXED_DISPATCH_DISTANCE_CAPEX_ONLY | 3744.333 | -2431.865 |

## Dispatch Rerun Manifest

| Case | Parameter group | Status | Note |
|---|---|---|---|
| flex_ratio_0p50 | compute_flexible_ratio | NOT_RUN_DEFAULT | Rebuilds compute load as 50% flexible and 50% rigid. |
| flex_ratio_0p80 | compute_flexible_ratio | NOT_RUN_DEFAULT | Rebuilds compute load as 80% flexible and 20% rigid. |
| distance_loss_proxy_0p05 | cable_loss_fraction | NOT_RUN_DEFAULT | Nearshore loss proxy; does not change cable CAPEX unless paired with cost table. |
| distance_loss_proxy_0p12 | cable_loss_fraction | NOT_RUN_DEFAULT | Farshore loss proxy; does not change cable CAPEX unless paired with cost table. |

Default output intentionally does not claim rerun evidence for dispatch-changing parameters.
