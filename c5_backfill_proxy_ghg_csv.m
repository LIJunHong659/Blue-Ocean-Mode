function writtenFiles = c5_backfill_proxy_ghg_csv(overwriteOriginal)
%C5_BACKFILL_PROXY_GHG_CSV Re-export C5 CSVs with proxy GHG columns.
%
% This script does not rerun the solver. It loads existing MAT result
% bundles, computes the proxy GHG columns used in Chapter 5.5.3, and
% writes new CSV files with a "_with_ghg" suffix by default.
%
% Usage:
%   c5_backfill_proxy_ghg_csv
%   c5_backfill_proxy_ghg_csv(true)   % overwrite original CSV names

if nargin < 1
    overwriteOriginal = false;
end

repoRoot = fileparts(mfilename('fullpath'));
addpath(fullfile(repoRoot, 'C5', '5.1场景设计', 'code'));
addpath(fullfile(repoRoot, 'C5', '5.2三大基准方案', 'code'));
addpath(fullfile(repoRoot, 'C5', '5.3对比方案与模型最优策略', 'code'));
addpath(fullfile(repoRoot, 'C5', '5.7混合最优策略短测试与年度运营分析', 'code'));

jobs = struct( ...
    'matPath', { ...
        fullfile(repoRoot, 'C5', '5.7混合最优策略短测试与年度运营分析', ...
            'results', 'annual_8760h_online_strategy_extreme', ...
            'c5_annual_online_strategy_results.mat'), ...
        fullfile(repoRoot, 'C5', '5.7混合最优策略短测试与年度运营分析', ...
            'results', 'annual_8760h_old_strategy_new_price_rerun', ...
            'c5_annual_online_strategy_results.mat'), ...
        fullfile(repoRoot, 'C5', '5.7混合最优策略短测试与年度运营分析', ...
            'results', 'cp01_annual_8760h_true_simulation', ...
            'cp01_annual_true_strategy_results.mat'), ...
        fullfile(repoRoot, 'C5', '5.2三大基准方案', 'results', ...
            'annual_asset_baselines_causal', ...
            'c5_annual_four_strategy_results.mat'), ...
        fullfile(repoRoot, 'C5', '5.3对比方案与模型最优策略', 'results', ...
            'typical_normal_48h_four_strategy', ...
            'c5_typical48_four_strategy_results.mat'), ...
        fullfile(repoRoot, 'C5', '5.7混合最优策略短测试与年度运营分析', ...
            'results', 'extreme_event_causal_v2', ...
            'c5_extreme_event_causal_results.mat'), ...
        fullfile(repoRoot, 'C5', '5.3对比方案与模型最优策略', 'results', ...
            'all_channel_48h_validation', ...
            'v5_all_channel_weather_task_48h.mat') ...
    }, ...
    'summaryCsv', { ...
        'c5_annual_online_strategy_summary.csv', ...
        'c5_annual_online_strategy_summary.csv', ...
        'cp01_annual_true_strategy_summary.csv', ...
        'c5_annual_four_strategy_summary.csv', ...
        'c5_typical48_four_strategy_summary.csv', ...
        'c5_extreme_event_causal_summary.csv', ...
        'summary.csv' ...
    }, ...
    'hourlyCsv', { ...
        'c5_annual_online_strategy_hourly.csv', ...
        'c5_annual_online_strategy_hourly.csv', ...
        'cp01_annual_true_strategy_hourly.csv', ...
        'c5_annual_four_strategy_hourly.csv', ...
        'c5_typical48_four_strategy_hourly.csv', ...
        'c5_extreme_event_hourly_ledger.csv', ...
        '' ...
    });

writtenFiles = strings(0, 1);

for i = 1:numel(jobs)
    job = jobs(i);
    matPath = as_text(job.matPath);
    summaryCsv = as_text(job.summaryCsv);
    hourlyCsv = as_text(job.hourlyCsv);

    if ~isfile(matPath)
        fprintf('Skip missing MAT: %s\n', matPath);
        continue;
    end

    S = load(matPath);

    if isfield(S, 'hourlyLedger') && isfield(S, 'summary')
        hourlyLedger = add_proxy_columns_to_hourly(S.hourlyLedger);
        summary = add_proxy_columns_to_summary(S.summary, hourlyLedger);

        summaryOut = output_path(matPath, summaryCsv, overwriteOriginal);
        hourlyOut = output_path(matPath, hourlyCsv, overwriteOriginal);
        write_table(summary, summaryOut);
        write_table(hourlyLedger, hourlyOut);
        writtenFiles(end+1, 1) = string(summaryOut); %#ok<AGROW>
        writtenFiles(end+1, 1) = string(hourlyOut); %#ok<AGROW>
        fprintf('Wrote %s\n', summaryOut);
        fprintf('Wrote %s\n', hourlyOut);
        continue;
    end

    if isfield(S, 'result') && isfield(S, 'summary')
        summary = add_proxy_columns_to_result_summary(S.summary, S.result);
        summaryOut = output_path(matPath, summaryCsv, overwriteOriginal);
        write_table(summary, summaryOut);
        writtenFiles(end+1, 1) = string(summaryOut); %#ok<AGROW>
        fprintf('Wrote %s\n', summaryOut);
        continue;
    end

    fprintf('Skip unsupported MAT bundle: %s\n', matPath);
end
end

function summary = add_proxy_columns_to_result_summary(summary, result)
dt = 1;
charge = safe_lookup(summary, {'BessChargeMWh', 'bessChargeMWh'}, 0);
discharge = safe_lookup(summary, {'BessDischargeMWh', 'bessDischargeMWh'}, 0);
throughput = charge + discharge;
sourceUsed = safe_lookup(summary, {'SourceUsedMWh', 'eSourceUsedMWh'}, 0);
cableReceived = safe_lookup(summary, {'CableReceivedMWh', 'eCableReceivedMWh'}, 0);
h2Delivered = safe_lookup(summary, {'H2DeliveredKg', 'h2DeliveredKg'}, 0);
computeService = safe_lookup(summary, {'ComputeServiceMWhCS', 'eComputeServiceMWhCS'}, 0);

proxyProject = 15 * sourceUsed + 5 * throughput * dt;
proxyAvoided = 500 * cableReceived + 10 * h2Delivered + 500 * computeService;
proxyNet = proxyProject - proxyAvoided;

summary = assign_column(summary, 'BessThroughputMWh', throughput);
summary = assign_column(summary, 'proxyProjectGHGKgCO2e', proxyProject);
summary = assign_column(summary, 'proxyAvoidedGHGKgCO2e', proxyAvoided);
summary = assign_column(summary, 'proxyNetGHGKgCO2e', proxyNet);

if isfield(result, 'kpi')
    if isfield(result.kpi, 'projectGHGKgCO2e')
        summary = assign_column(summary, 'projectGHGKgCO2e', result.kpi.projectGHGKgCO2e);
    end
    if isfield(result.kpi, 'avoidedBaselineGHGKgCO2e')
        summary = assign_column(summary, 'avoidedBaselineGHGKgCO2e', result.kpi.avoidedBaselineGHGKgCO2e);
    end
    if isfield(result.kpi, 'netGHGKgCO2e')
        summary = assign_column(summary, 'netGHGKgCO2e', result.kpi.netGHGKgCO2e);
    end
end
end

function summary = add_proxy_columns_to_summary(summary, hourlyLedger)
ids = [];
if ismember('strategyId', hourlyLedger.Properties.VariableNames)
    ids = string(hourlyLedger.strategyId);
end

summaryIds = [];
if ismember('strategyId', summary.Properties.VariableNames)
    summaryIds = string(summary.strategyId);
end

hasMultipleRows = height(summary) > 1;

charge = zeros(height(summary), 1);
discharge = zeros(height(summary), 1);
throughput = zeros(height(summary), 1);
proxyProject = zeros(height(summary), 1);
proxyAvoided = zeros(height(summary), 1);
proxyNet = zeros(height(summary), 1);

for r = 1:height(summary)
    if hasMultipleRows && ~isempty(summaryIds) && ~isempty(ids)
        idx = ids == summaryIds(r);
    else
        idx = true(height(hourlyLedger), 1);
    end

    charge(r) = sum(col(hourlyLedger, 'bessChargeMWh', idx));
    discharge(r) = sum(col(hourlyLedger, 'bessDischargeMWh', idx));
    throughput(r) = charge(r) + discharge(r);
    sourceUsed = sum(col(hourlyLedger, 'eSourceUsedMWh', idx));
    cableReceived = sum(col(hourlyLedger, 'eCableReceivedMWh', idx));
    h2Delivered = sum(col(hourlyLedger, 'h2DeliveredKg', idx));
    computeService = sum(col(hourlyLedger, 'eComputeServiceMWhCS', idx));

    proxyProject(r) = 15 * sourceUsed + 5 * throughput(r);
    proxyAvoided(r) = 500 * cableReceived + 10 * h2Delivered + 500 * computeService;
    proxyNet(r) = proxyProject(r) - proxyAvoided(r);
end

summary = assign_column(summary, 'bessChargeMWh', charge);
summary = assign_column(summary, 'bessDischargeMWh', discharge);
summary = assign_column(summary, 'bessThroughputMWh', throughput);
summary = assign_column(summary, 'proxyProjectGHGKgCO2e', proxyProject);
summary = assign_column(summary, 'proxyAvoidedGHGKgCO2e', proxyAvoided);
summary = assign_column(summary, 'proxyNetGHGKgCO2e', proxyNet);
end

function hourlyLedger = add_proxy_columns_to_hourly(hourlyLedger)
dt = 1;
if ismember('timeH', hourlyLedger.Properties.VariableNames) && height(hourlyLedger) > 1
    t = hourlyLedger.timeH;
    if isnumeric(t)
        d = diff(double(t));
        d = d(isfinite(d) & d > 0);
        if ~isempty(d)
            dt = median(d);
        end
    end
end

charge = col(hourlyLedger, 'pBessChargeMW', true(height(hourlyLedger), 1)) * dt;
discharge = col(hourlyLedger, 'pBessDischargeMW', true(height(hourlyLedger), 1)) * dt;
throughput = charge + discharge;
sourceUsed = col(hourlyLedger, 'eSourceUsedMWh', true(height(hourlyLedger), 1));
cableReceived = col(hourlyLedger, 'eCableReceivedMWh', true(height(hourlyLedger), 1));
h2Delivered = col(hourlyLedger, 'h2DeliveredKg', true(height(hourlyLedger), 1));
computeService = col(hourlyLedger, 'eComputeServiceMWhCS', true(height(hourlyLedger), 1));

proxyProject = 15 * sourceUsed + 5 * throughput;
proxyAvoided = 500 * cableReceived + 10 * h2Delivered + 500 * computeService;
proxyNet = proxyProject - proxyAvoided;

hourlyLedger = assign_column(hourlyLedger, 'bessChargeMWh', charge);
hourlyLedger = assign_column(hourlyLedger, 'bessDischargeMWh', discharge);
hourlyLedger = assign_column(hourlyLedger, 'bessThroughputMWh', throughput);
hourlyLedger = assign_column(hourlyLedger, 'proxyProjectGHGKgCO2e', proxyProject);
hourlyLedger = assign_column(hourlyLedger, 'proxyAvoidedGHGKgCO2e', proxyAvoided);
hourlyLedger = assign_column(hourlyLedger, 'proxyNetGHGKgCO2e', proxyNet);
end

function values = col(T, name, mask)
if ismember(name, T.Properties.VariableNames)
    values = T.(name);
else
    values = zeros(height(T), 1);
end
values = values(mask);
values = double(values);
end

function value = safe_lookup(S, candidates, defaultValue)
value = defaultValue;
for i = 1:numel(candidates)
    name = candidates{i};
    if istable(S)
        if ismember(name, S.Properties.VariableNames)
            value = S.(name);
            return;
        end
    elseif isstruct(S)
        if isfield(S, name)
            value = S.(name);
            return;
        end
    end
end
end

function T = assign_column(T, name, value)
if isrow(value) && height(T) > 1
    value = value(:);
end
T.(name) = value;
end

function outPath = output_path(matPath, csvName, overwriteOriginal)
folder = fileparts(matPath);
if overwriteOriginal
    outPath = fullfile(folder, csvName);
else
    if endsWith(csvName, '.csv')
        stem = csvName(1:end-4);
        outPath = fullfile(folder, [stem '_with_ghg.csv']);
    else
        outPath = fullfile(folder, [csvName '_with_ghg']);
    end
end
end

function text = as_text(value)
if iscell(value)
    value = value{1};
end
text = char(string(value));
end
function write_table(T, outPath)
outDir = fileparts(outPath);
if ~isfolder(outDir)
    mkdir(outDir);
end
writetable(T, outPath);
end
