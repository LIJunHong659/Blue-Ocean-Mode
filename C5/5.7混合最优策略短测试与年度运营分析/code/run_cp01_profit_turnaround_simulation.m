function result = run_cp01_profit_turnaround_simulation(refreshAnnual)
%RUN_CP01_PROFIT_TURNAROUND_SIMULATION CP01 profit-turnaround entry point.
%
% This wrapper reuses the existing annual C5 ledger, then runs the CP01
% post-processing scripts that generate the scenario and checked-report
% files. If the annual ledger is missing, it can regenerate it first.

thisDir = fileparts(mfilename('fullpath'));
addpath(thisDir);
caseDir = fileparts(thisDir);
annualDir = fullfile(caseDir, 'results', 'annual_8760h_online_strategy_extreme');
cp01Dir = fullfile(caseDir, 'results', 'cp01_profit_turnaround_simulation');

if nargin < 1 || isempty(refreshAnnual)
    refreshAnnual = false;
end

summaryFile = fullfile(annualDir, 'c5_annual_online_strategy_summary.csv');
hourlyFile = fullfile(annualDir, 'c5_annual_online_strategy_hourly.csv');

didRefreshAnnual = false;
if refreshAnnual || ~isfile(summaryFile) || ~isfile(hourlyFile)
    run_c5_annual_causal_hourly(annualDir, 8760, 1, "model_online_prior_posterior_event_aware");
    didRefreshAnnual = true;
end

pythonExe = resolve_python_executable();
run_python_script(pythonExe, fullfile(thisDir, 'run_cp01_profit_turnaround_simulation.py'));
run_python_script(pythonExe, fullfile(thisDir, 'write_cp01_profit_turnaround_checked_report.py'));

result = struct( ...
    'annualDir', annualDir, ...
    'outputDir', cp01Dir, ...
    'summaryFile', fullfile(cp01Dir, 'cp01_profit_turnaround_scenarios.csv'), ...
    'replayFile', fullfile(cp01Dir, 'cp01_hydrogen_module_replay.csv'), ...
    'reportFile', fullfile(cp01Dir, 'cp01_profit_turnaround_simulation_checked_v2.md'), ...
    'annualSummaryFile', summaryFile, ...
    'annualHourlyFile', hourlyFile, ...
    'refreshedAnnualLedger', didRefreshAnnual);
end

function run_python_script(pythonExe, scriptPath)
cmd = strjoin({pythonExe, quote_arg(scriptPath)}, ' ');
[status, output] = system(cmd);
assert(status == 0, 'CP01 helper failed: %s', strtrim(output));
end

function pythonExe = resolve_python_executable()
candidates = {'python', 'py -3'};
for i = 1:numel(candidates)
    [status, ~] = system(sprintf('%s --version', candidates{i}));
    if status == 0
        pythonExe = candidates{i};
        return;
    end
end
error('Unable to locate a Python executable on PATH.');
end

function quoted = quote_arg(value)
quoted = ['"', char(string(value)), '"'];
end