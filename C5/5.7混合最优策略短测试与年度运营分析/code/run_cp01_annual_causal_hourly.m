function [summary,eventSummary,hourlyLedger,results] = ...
    run_cp01_annual_causal_hourly(outputDir,horizonH,phaseId)
%RUN_CP01_ANNUAL_CAUSAL_HOURLY True CP01 annual dispatch simulation.
%
% This entry point runs a fresh sequential 8760 h dispatch with CP01
% operating/economic overlays. It does not reuse the old annual result as a
% ledger for post-processing.

thisDir=fileparts(mfilename('fullpath'));
c5Root=fileparts(fileparts(thisDir));
addpath(fullfile(c5Root,'5.1场景设计','code'),thisDir);
c5_add_v5_model_paths();

if nargin<1 || strlength(string(outputDir))==0
    outputDir=fullfile(c5Root, ...
        '5.7混合最优策略短测试与年度运营分析', ...
        'results','cp01_annual_8760h_true_simulation');
end
if nargin<2 || isempty(horizonH), horizonH=8760; end
if nargin<3 || strlength(string(phaseId))==0
    phaseId="cp01_phase2_30mw_h2_contract";
end
phaseId=string(phaseId);
assert(isscalar(horizonH) && horizonH==round(horizonH) && ...
    horizonH>=1 && horizonH<=8760,'horizonH must be in [1,8760].');

scenario=c5_build_annual_2025_multisource_scenario();
[scenario,burdenCNY,phaseNote]=apply_cp01_phase_overlay(scenario,phaseId);
cfg=scenario.config;

[sourceInput,sourceDetail]=v5_source_adapter(cfg,scenario.input.sourceCase);
base=rmfield(scenario.input,'sourceCase');
base=merge_input(base,sourceInput);
base.pWindAvailableMW=sourceDetail.availableBySourceMW(:,1);
base.pPVAvailableMW=sourceDetail.availableBySourceMW(:,2);
base.pTidalAvailableMW=sourceDetail.availableBySourceMW(:,3);
base.availability.h2Power=ones(numel(base.timeH),1);
initialStateAudit=base.initial;
if horizonH<8760
    base=c5_slice_input_horizon(base,1:horizonH);
end
eventCode=scenario.hourly.eventCode(1:horizonH);

strategies=c5_four_strategy_specs();
onlineIdx=find(strcmp(string(cellfun(@(s)s.id,strategies, ...
    'UniformOutput',false)),"model_online_prior_posterior_event_aware"),1);
assert(~isempty(onlineIdx),'Missing online prior-posterior strategy.');
strategy=strategies{onlineIdx};
strategy.id=char(phaseId);
strategy.strategyClass='CP01_TRUE_ANNUAL_DISPATCH';

[summary,hourlyLedger,results]=c5_run_sequential_hourly( ...
    base,cfg,strategy,eventCode,false);
summary=attach_cp01_economics(summary,burdenCNY,phaseId,phaseNote);
summary.comparisonSet=repmat("CP01_TRUE_ANNUAL_DISPATCH_ONLY", ...
    height(summary),1);
summary.scenarioId=repmat(string(scenario.meta.scenarioId), ...
    height(summary),1);
summary.extremeEventIncluded=repmat(any(eventCode~="NORMAL"), ...
    height(summary),1);
summary.stateCarryRule=repmat( ...
    "PREVIOUS_HOUR_TERMINAL_STATE; NO_EVENT_RESET_OR_INJECTION", ...
    height(summary),1);
summary.h2InventoryMinimumPolicy=repmat( ...
    "PHYSICAL_NONNEGATIVITY_ONLY; NO_OPERATIONAL_FLOOR",height(summary),1);
summary.h2PowerRatedMW=repmat(cfg.h2Power.ratedMW,height(summary),1);
summary.initialBessEnergyMWh=repmat(initialStateAudit.bessEnergyMWh, ...
    height(summary),1);
summary.initialH2InventoryKg=repmat(initialStateAudit.h2InventoryKg, ...
    height(summary),1);

demandAudit=summarize_demand_by_event( ...
    v5_validate_and_normalize_input(cfg,base),eventCode);
totalCriticalDemandMWh=sum(demandAudit.totalCriticalDemandMWh);
summary.totalCriticalDemandMWh=repmat(totalCriticalDemandMWh, ...
    height(summary),1);
summary.criticalServiceRate=1-summary.ensMWh/totalCriticalDemandMWh;
eventSummary=summarize_by_event(hourlyLedger);
eventSummary=attach_critical_service_rate(eventSummary,demandAudit);

if ~isfolder(outputDir), mkdir(outputDir); end
stem='cp01_annual_true_strategy';
writetable(summary,fullfile(outputDir,[stem '_summary.csv']));
writetable(eventSummary,fullfile(outputDir,[stem '_event_summary.csv']));
writetable(demandAudit,fullfile(outputDir,[stem '_demand_audit.csv']));
writetable(hourlyLedger,fullfile(outputDir,[stem '_hourly.csv']));
scenarioMeta=scenario.meta;
scenarioEvidence=scenario.evidence;
sourceAudit=rmfield(sourceDetail,'raw');
save(fullfile(outputDir,[stem '_results.mat']), ...
    'summary','eventSummary','demandAudit','hourlyLedger','strategy', ...
    'scenarioMeta','scenarioEvidence','sourceAudit', ...
    'initialStateAudit','horizonH','phaseId','burdenCNY','phaseNote', ...
    '-v7.3');
end

function [scenario,burdenCNY,phaseNote]=apply_cp01_phase_overlay( ...
    scenario,phaseId)
cfg=scenario.config;
in=scenario.input;
totalAnnualBurdenCNY=4054.611e6;
switch char(phaseId)
    case 'cp01_phase2_30mw_h2_contract'
        cfg.hydrogen.electrolyzerRatedMW=30;
        cfg.hydrogen.moduleCount=3;
        cfg.hydrogen.moduleRatedMW=10;
        cfg.hydrogen.moduleMinMW=2;
        cfg.hydrogen.rampUpMWPerH=7992;
        cfg.hydrogen.rampDownMWPerH=7992;
        cfg.h2Power.enabled=true;
        cfg.h2Power.ratedMW=30;
        in.hydrogenPriceCNYPerKg=35*ones(numel(scenario.hourly.eventCode),1);
        burdenCNY=0.12*totalAnnualBurdenCNY;
        phaseNote="30 MW PEM; 35 CNY/kg H2 offtake; retained burden 12%";
    case 'cp01_phase2_100mw_reliability_reference'
        cfg.h2Power.enabled=true;
        cfg.h2Power.ratedMW=30;
        in.hydrogenPriceCNYPerKg=35*ones(numel(scenario.hourly.eventCode),1);
        burdenCNY=0.12*totalAnnualBurdenCNY;
        phaseNote="100 MW PEM reliability reference; 35 CNY/kg H2 offtake; retained burden 12%";
    case 'cp01_phase1_light_asset_no_h2'
        cfg.h2Power.enabled=false;
        cfg.h2Power.ratedMW=0;
        in.availability.electrolyzer=zeros(numel(scenario.hourly.eventCode),1);
        in.availability.h2Storage=zeros(numel(scenario.hourly.eventCode),1);
        in.availability.h2Pipe=zeros(numel(scenario.hourly.eventCode),1);
        in.availability.h2Ship=zeros(numel(scenario.hourly.eventCode),1);
        in.availability.h2Power=zeros(numel(scenario.hourly.eventCode),1);
        burdenCNY=0.10*totalAnnualBurdenCNY;
        phaseNote="Phase-1 light asset; no hydrogen chain; retained burden 10%";
    otherwise
        error('Unknown CP01 phaseId: %s',char(phaseId));
end
cfg.meta.parameterVersion=char("cp01_true_annual_"+phaseId);
scenario.input=in;
scenario.config=cfg;
scenario.meta.scenarioId=char("CP01_TRUE_ANNUAL_2025_"+upper(phaseId));
scenario.meta.cp01PhaseId=char(phaseId);
scenario.meta.cp01PhaseNote=char(phaseNote);
end

function summary=attach_cp01_economics(summary,burdenCNY,phaseId,phaseNote)
cashMargin=summary.outputRevenueCNY-summary.operatingCostCNY;
netOperatingValue=-summary.economicNetCostCNY;
summary.cp01PhaseId=repmat(phaseId,height(summary),1);
summary.cp01PhaseNote=repmat(phaseNote,height(summary),1);
summary.cp01AnnualizedBurdenCNY=repmat(burdenCNY,height(summary),1);
summary.cp01CashMarginCNY=cashMargin;
summary.cp01ProjectNetCashCNY=cashMargin-burdenCNY;
summary.cp01NetOperatingValueCNY=netOperatingValue;
summary.cp01ProjectNetValueCNY=netOperatingValue-burdenCNY;
summary.cp01CoverageRatio=cashMargin/burdenCNY;
summary.cp01PassCashPositive=summary.cp01ProjectNetCashCNY>=0;
summary.cp01Pass1p2Gate=summary.cp01CoverageRatio>=1.2;
end

function demandAudit=summarize_demand_by_event(base,eventCode)
events=unique(eventCode,'stable');
rows=cell(numel(events),1);
for i=1:numel(events)
    idx=eventCode==events(i);
    rows{i}=table(events(i),nnz(idx), ...
        sum(base.pInternalDemandMW(idx)), ...
        sum(base.pMarineDemandMW(idx)), ...
        sum(base.pComputeBaseDemandMW(idx)), ...
        'VariableNames',{'eventCode','hours','internalDemandMWh', ...
        'marineDemandMWh','computeBaseDemandMWh'});
end
demandAudit=vertcat(rows{:});
demandAudit.totalCriticalDemandMWh=demandAudit.internalDemandMWh+ ...
    demandAudit.marineDemandMWh+demandAudit.computeBaseDemandMWh;
end

function eventSummary=attach_critical_service_rate(eventSummary,demandAudit)
eventSummary.totalCriticalDemandMWh=zeros(height(eventSummary),1);
eventSummary.criticalServiceRate=zeros(height(eventSummary),1);
for i=1:height(eventSummary)
    idx=find(demandAudit.eventCode==eventSummary.eventCode(i),1);
    assert(~isempty(idx),'Missing demand audit row for event %s.', ...
        eventSummary.eventCode(i));
    demand=demandAudit.totalCriticalDemandMWh(idx);
    eventSummary.totalCriticalDemandMWh(i)=demand;
    if demand>0
        eventSummary.criticalServiceRate(i)= ...
            1-eventSummary.ensMWh(i)/demand;
    else
        eventSummary.criticalServiceRate(i)=1;
    end
end
end

function eventSummary=summarize_by_event(hourlyLedger)
strategies=unique(hourlyLedger.strategyId,'stable');
rows=cell(0,1);
for i=1:numel(strategies)
    strategyIdx=hourlyLedger.strategyId==strategies(i);
    events=unique(hourlyLedger.eventCode(strategyIdx),'stable');
    for j=1:numel(events)
        idx=strategyIdx & hourlyLedger.eventCode==events(j);
        rows{end+1,1}=table(strategies(i),events(j),nnz(idx), ...
            sum(hourlyLedger.eAvailableMWh(idx)), ...
            sum(hourlyLedger.eSourceUsedMWh(idx)), ...
            sum(hourlyLedger.eCurtailmentMWh(idx)), ...
            sum(hourlyLedger.ensMWh(idx)), ...
            sum(hourlyLedger.eElectricityInputMWh(idx)), ...
            sum(hourlyLedger.eHydrogenInputMWh(idx)), ...
            sum(hourlyLedger.eFlexibleComputeInputMWh(idx)), ...
            min(hourlyLedger.bessSOC(idx)), ...
            min(hourlyLedger.h2InventoryKg(idx)), ...
            nnz(hourlyLedger.planFallbackUsed(idx)), ...
            nnz(hourlyLedger.reserveConstraintRelaxationUsed(idx)), ...
            nnz(hourlyLedger.reliabilityRelaxationUsed(idx)), ...
            'VariableNames',{'strategyId','eventCode','hours', ...
            'eAvailableMWh','eSourceUsedMWh','eCurtailmentMWh','ensMWh', ...
            'eElectricityInputMWh','eHydrogenInputMWh', ...
            'eFlexibleComputeInputMWh','minimumBessSOC', ...
            'minimumH2InventoryKg','planFallbackHours', ...
            'reserveConstraintRelaxationHours', ...
            'reliabilityRelaxationHours'}); %#ok<AGROW>
    end
end
eventSummary=vertcat(rows{:});
end

function out=merge_input(out,addition)
names=fieldnames(addition);
for k=1:numel(names), out.(names{k})=addition.(names{k}); end
end


