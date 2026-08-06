function [priceSensitivity,costSensitivity,rerunManifest] = ...
    run_c5_56_minimal_sensitivity(runDispatchBoundaryCases,horizonH,caseIds)
%RUN_C5_56_MINIMAL_SENSITIVITY Minimal-rerun pack for C5 section 5.6.
%
% Default behavior is fast post-processing only:
%   - price sensitivity uses the existing 8760 h dispatch ledger;
%   - capital/cable cost sensitivity uses the lifecycle ledger only;
%   - dispatch-changing boundary cases are listed but not run.
%
% Set runDispatchBoundaryCases=true to run selected slow 8760 h cases.

if nargin<1 || isempty(runDispatchBoundaryCases)
    runDispatchBoundaryCases=false;
end
if nargin<2 || isempty(horizonH)
    horizonH=8760;
end
if nargin<3
    caseIds=strings(0,1);
elseif ischar(caseIds)
    caseIds=string({caseIds});
elseif iscell(caseIds)
    caseIds=string(caseIds(:));
else
    caseIds=string(caseIds(:));
end
assert(isscalar(horizonH) && horizonH==round(horizonH) && ...
    horizonH>=1 && horizonH<=8760,'horizonH must be in [1,8760].');

thisDir=fileparts(mfilename('fullpath'));
c5Root=fileparts(fileparts(thisDir));
scenarioCodeDir=fullfile(c5Root,'5.1场景设计','code');
addpath(scenarioCodeDir,thisDir);
paths=c5_add_v5_model_paths();
addpath(fullfile(paths.v5Root,'foundation','modules','4.8_objectives','model'));
addpath(fullfile(paths.v5Root,'foundation','library','4.2变量与接口'));
addpath(fullfile(paths.v5Root,'foundation','integration','common'));

resultRoot=fullfile(c5Root, ...
    '5.7混合最优策略短测试与年度运营分析','results');
baseDir=fullfile(resultRoot,'annual_8760h_online_strategy_extreme');
outputDir=fullfile(resultRoot,'minimal_sensitivity_5_6');
if ~isfolder(outputDir), mkdir(outputDir); end

summaryPath=fullfile(baseDir,'c5_annual_online_strategy_summary.csv');
assert(isfile(summaryPath), ...
    ['Missing annual summary. Run run_c5_annual_causal_hourly first: ' ...
     summaryPath]);
annualSummary=readtable(summaryPath,'TextType','string');
baseRow=select_base_row(annualSummary);

[priceSensitivity,priceSlope]=build_price_sensitivity(baseRow);
[costSensitivity,assetLedger]=build_cost_sensitivity(baseRow);
rerunManifest=build_rerun_manifest();

if runDispatchBoundaryCases
    selected=select_rerun_cases(rerunManifest,caseIds);
    for i=find(selected).'
        caseId=char(rerunManifest.caseId(i));
        caseOutDir=fullfile(outputDir,'annual_dispatch_boundary_cases',caseId);
        fprintf('C5 5.6 boundary rerun %d/%d: %s\n', ...
            nnz(selected(1:i)),nnz(selected),caseId);
        [caseSummary,caseEventSummary,caseHourlyLedger]= ...
            run_boundary_case(rerunManifest(i,:),caseOutDir,horizonH);
        rerunManifest.dispatchStatus(i)="RUN_COMPLETE";
        rerunManifest.summaryFile(i)=string(fullfile( ...
            caseOutDir,'c5_56_boundary_summary.csv'));
        rerunManifest.hourlyFile(i)=string(fullfile( ...
            caseOutDir,'c5_56_boundary_hourly.csv'));
        rerunManifest.eventSummaryFile(i)=string(fullfile( ...
            caseOutDir,'c5_56_boundary_event_summary.csv'));
        clear caseSummary caseEventSummary caseHourlyLedger
    end
end

writetable(priceSlope,fullfile(outputDir,'c5_56_price_slope.csv'));
writetable(priceSensitivity,fullfile( ...
    outputDir,'c5_56_fixed_dispatch_price_sensitivity.csv'));
writetable(costSensitivity,fullfile( ...
    outputDir,'c5_56_fixed_dispatch_cost_sensitivity.csv'));
writetable(assetLedger,fullfile(outputDir,'c5_56_lifecycle_asset_ledger.csv'));
writetable(rerunManifest,fullfile(outputDir,'c5_56_boundary_rerun_manifest.csv'));
write_markdown_report(outputDir,priceSlope,priceSensitivity, ...
    costSensitivity,rerunManifest);

fprintf('C5 5.6 minimal sensitivity outputs written to:\n%s\n',outputDir);
end

function baseRow=select_base_row(summary)
required={ ...
    'eCableReceivedMWh','h2DeliveredKg','eComputeServiceMWhCS', ...
    'outputRevenueCNY','operatingCostCNY','economicNetCostCNY', ...
    'eAvailableMWh','eSourceUsedMWh','eCurtailmentMWh','ensMWh'};
for k=1:numel(required)
    assert(ismember(required{k},summary.Properties.VariableNames), ...
        'Annual summary is missing column %s.',required{k});
end
idx=[];
if ismember('strategyId',summary.Properties.VariableNames)
    idx=find(summary.strategyId=="model_online_prior_posterior_event_aware",1);
end
if isempty(idx)
    idx=1;
end
baseRow=summary(idx,:);
end

function [priceSensitivity,priceSlope]=build_price_sensitivity(baseRow)
[~,meta]=c5_market_price_profile('electricity_annual_base',1);
anchors=meta.anchors;
baseElec=anchors.electricityAnnualAverageCNYPerMWh;
baseH2=anchors.hydrogenGreenIndexCNYPerKg;
baseCompute=anchors.computeBlendedCNYPerMWhIT;

eCable=scalar(baseRow,'eCableReceivedMWh');
h2=scalar(baseRow,'h2DeliveredKg');
compute=scalar(baseRow,'eComputeServiceMWhCS');
baseOutputRevenue=scalar(baseRow,'outputRevenueCNY');
baseOperatingCost=scalar(baseRow,'operatingCostCNY');
baseEconomicNetCost=scalar(baseRow,'economicNetCostCNY');
terminalAdjustment=baseEconomicNetCost-baseOperatingCost+baseOutputRevenue;
productRevenue=eCable*baseElec+h2*baseH2+compute*baseCompute;
otherRevenue=baseOutputRevenue-productRevenue;

slopeParameter=["electricity_price";"hydrogen_price";"compute_price"];
slopeUnit=["+10 CNY/MWh received";"+1 CNY/kg delivered"; ...
    "+100 CNY/MWh-CS"];
slopeQuantity=[eCable;h2;compute];
slopeRevenueChangeCNY=[10*eCable;h2;100*compute];
slopeRevenueChangeMillionCNY=slopeRevenueChangeCNY/1e6;
priceSlope=table(slopeParameter,slopeUnit,slopeQuantity, ...
    slopeRevenueChangeCNY,slopeRevenueChangeMillionCNY, ...
    'VariableNames',{'parameter','unitStep','baselineQuantity', ...
    'annualRevenueChangeCNY','annualRevenueChangeMillionCNY'});

caseId=["base_price_anchor";"electricity_minus_10"; ...
    "electricity_plus_10";"hydrogen_minus_1";"hydrogen_plus_1"; ...
    "compute_minus_100";"compute_plus_100"];
changedParameter=["base";"electricity_price";"electricity_price"; ...
    "hydrogen_price";"hydrogen_price";"compute_price";"compute_price"];
electricityPriceCNYPerMWh=[baseElec;baseElec-10;baseElec+10; ...
    baseElec;baseElec;baseElec;baseElec];
hydrogenPriceCNYPerKg=[baseH2;baseH2;baseH2;baseH2-1;baseH2+1; ...
    baseH2;baseH2];
computePriceCNYPerMWhCS=[baseCompute;baseCompute;baseCompute; ...
    baseCompute;baseCompute;baseCompute-100;baseCompute+100];
n=numel(caseId);
method=repmat("FIXED_DISPATCH_REPRICE_NO_MATLAB_RERUN",n,1);
outputRevenueCNY=zeros(n,1);
revenueDeltaCNY=zeros(n,1);
operatingCostCNY=repmat(baseOperatingCost,n,1);
cashOperatingMarginCNY=zeros(n,1);
economicNetCostCNY=zeros(n,1);
netOperatingValueCNY=zeros(n,1);
for i=1:n
    outputRevenueCNY(i)= ...
        eCable*electricityPriceCNYPerMWh(i)+ ...
        h2*hydrogenPriceCNYPerKg(i)+ ...
        compute*computePriceCNYPerMWhCS(i)+otherRevenue;
    revenueDeltaCNY(i)=outputRevenueCNY(i)-baseOutputRevenue;
    cashOperatingMarginCNY(i)=outputRevenueCNY(i)-baseOperatingCost;
    economicNetCostCNY(i)=baseOperatingCost-outputRevenueCNY(i)+ ...
        terminalAdjustment;
    netOperatingValueCNY(i)=-economicNetCostCNY(i);
end

eAvailableMWh=repmat(scalar(baseRow,'eAvailableMWh'),n,1);
eSourceUsedMWh=repmat(scalar(baseRow,'eSourceUsedMWh'),n,1);
renewableUtilization=eSourceUsedMWh./eAvailableMWh;
eCurtailmentMWh=repmat(scalar(baseRow,'eCurtailmentMWh'),n,1);
curtailmentRate=eCurtailmentMWh./eAvailableMWh;
ensMWh=repmat(scalar(baseRow,'ensMWh'),n,1);
planFallbackHours=repmat(scalar(baseRow,'planFallbackHours',NaN),n,1);
reserveConstraintRelaxationHours=repmat( ...
    scalar(baseRow,'reserveConstraintRelaxationHours',NaN),n,1);
reliabilityRelaxationHours=repmat( ...
    scalar(baseRow,'reliabilityRelaxationHours',NaN),n,1);
netGHGKgCO2e=repmat(scalar(baseRow,'netGHGKgCO2e',NaN),n,1);
note=repmat("Only revenue is repriced; dispatch, ENS and GHG are reused.",n,1);

priceSensitivity=table(caseId,changedParameter,method, ...
    electricityPriceCNYPerMWh,hydrogenPriceCNYPerKg, ...
    computePriceCNYPerMWhCS,outputRevenueCNY,revenueDeltaCNY, ...
    operatingCostCNY,cashOperatingMarginCNY,economicNetCostCNY, ...
    netOperatingValueCNY,eAvailableMWh,renewableUtilization, ...
    eCurtailmentMWh,curtailmentRate,ensMWh,planFallbackHours, ...
    reserveConstraintRelaxationHours,reliabilityRelaxationHours, ...
    netGHGKgCO2e,note);
end

function [costSensitivity,assetLedger]=build_cost_sensitivity(baseRow)
cfg=common_config_4_2('engineering_base');
cfg=v4_apply_unified_capacity_case_4_2(cfg,'M');
if ismember('h2PowerRatedMW',baseRow.Properties.VariableNames)
    cfg.hydrogen.electrolyzerRatedMW=scalar(baseRow,'h2PowerRatedMW', ...
        cfg.hydrogen.electrolyzerRatedMW);
    cfg.capacity.installed.electrolyzerMW=cfg.hydrogen.electrolyzerRatedMW;
end
cfg=normalize_cable_distance(cfg,[]);
p=v4_objective_parameters_4_8();
[lifecycle,assetLedger]=v4_lifecycle_economics_4_8( ...
    cfg,p,scalar(baseRow,'operatingCostCNY'), ...
    scalar(baseRow,'outputRevenueCNY'),0, ...
    scalar(baseRow,'horizonH',8760),struct());

assetLedger.annualCapitalRecoveryCNY= ...
    assetLedger.annualDepreciationCNY+assetLedger.annualFinancingCNY+ ...
    assetLedger.annualReplacementRecoveryCNY;
assetLedger.annualizedBurdenCNY= ...
    assetLedger.annualCapitalRecoveryCNY+assetLedger.fixedOMAnnualCNY;

cashMargin=scalar(baseRow,'outputRevenueCNY')- ...
    scalar(baseRow,'operatingCostCNY');
baseBurden=sum(assetLedger.annualizedBurdenCNY);
baseProjectNet=cashMargin-baseBurden;
baseDistance=distance_from_cfg(cfg);

caseRows=cell(0,1);
caseRows{end+1}=cost_row("base_lifecycle_cost", ...
    "base","FIXED_DISPATCH_LIFECYCLE_POSTPROCESS",baseDistance,1, ...
    lifecycle.grossCapexCNY,baseBurden,cashMargin,baseProjectNet, ...
    baseProjectNet,"Base lifecycle cost computed from existing dispatch.");

assetName=string(assetLedger.assetName);
cableAssets=["powerExportCable","converterAndSubstation","fiberCable"];
cableMask=ismember(assetName,cableAssets);
deviceMask=~cableMask;
for group=["device_cost","cable_asset_cost"]
    if group=="device_cost"
        mask=deviceMask;
        groupNote="Scaled annualized burden for non-cable assets.";
    else
        mask=cableMask;
        groupNote="Scaled annualized burden for export cable, converter/substation and fiber cable.";
    end
    affectedBurden=sum(assetLedger.annualizedBurdenCNY(mask));
    for factor=[0.80 1.20]
        newBurden=baseBurden+(factor-1)*affectedBurden;
        newProjectNet=cashMargin-newBurden;
        caseRows{end+1}=cost_row( ...
            sprintf('%s_%s20pct',char(group),ternary(factor<1,'minus','plus')), ...
            group,"FIXED_DISPATCH_ANNUALIZED_BURDEN_REPRICE", ...
            baseDistance,factor,NaN,newBurden,cashMargin,newProjectNet, ...
            baseProjectNet,groupNote); %#ok<AGROW>
    end
end

distanceCases=unique(round([0.5*baseDistance;baseDistance;1.5*baseDistance]));
for i=1:numel(distanceCases)
    d=distanceCases(i);
    cfgD=normalize_cable_distance(cfg,d);
    [lifeD,ledgerD]=v4_lifecycle_economics_4_8( ...
        cfgD,p,scalar(baseRow,'operatingCostCNY'), ...
        scalar(baseRow,'outputRevenueCNY'),0, ...
        scalar(baseRow,'horizonH',8760),struct());
    annualBurdenD=lifeD.annualFixedOMCNY+lifeD.annualDepreciationCNY+ ...
        lifeD.annualFinancingCostCNY+lifeD.annualReplacementReserveCNY;
    projectNetD=cashMargin-annualBurdenD;
    caseRows{end+1}=cost_row( ...
        sprintf('distance_%03.0fkm_capex_only',d), ...
        "distance_cable_capex","FIXED_DISPATCH_DISTANCE_CAPEX_ONLY", ...
        d,NaN,lifeD.grossCapexCNY,annualBurdenD,cashMargin, ...
        projectNetD,baseProjectNet, ...
        "Distance changes cable/fiber CAPEX only; dispatch loss and availability are unchanged.");
    clear ledgerD
end
costSensitivity=vertcat(caseRows{:});
end

function T=cost_row(caseId,parameterGroup,method,distanceKm,costMultiplier, ...
    grossCapexCNY,annualizedInvestmentBurdenCNY,cashOperatingMarginCNY, ...
    projectAnnualNetCashCNY,baseProjectAnnualNetCashCNY,note)
deltaProjectAnnualNetCashCNY= ...
    projectAnnualNetCashCNY-baseProjectAnnualNetCashCNY;
T=table(string(caseId),string(parameterGroup),string(method), ...
    distanceKm,costMultiplier,grossCapexCNY, ...
    annualizedInvestmentBurdenCNY,cashOperatingMarginCNY, ...
    projectAnnualNetCashCNY,deltaProjectAnnualNetCashCNY, ...
    string(note), ...
    'VariableNames',{'caseId','parameterGroup','method', ...
    'distanceToShoreKm','costMultiplier','grossCapexCNY', ...
    'annualizedInvestmentBurdenCNY','cashOperatingMarginCNY', ...
    'projectAnnualNetCashCNY','deltaProjectAnnualNetCashCNY','note'});
end

function rerunManifest=build_rerun_manifest()
caseId=["flex_ratio_0p50";"flex_ratio_0p80"; ...
    "distance_loss_proxy_0p05";"distance_loss_proxy_0p12"];
parameterGroup=["compute_flexible_ratio";"compute_flexible_ratio"; ...
    "cable_loss_fraction";"cable_loss_fraction"];
method=repmat("ANNUAL_DISPATCH_RERUN_REQUIRED",4,1);
flexibleComputeRatio=[0.50;0.80;NaN;NaN];
cableLossFraction=[NaN;NaN;0.05;0.12];
dispatchStatus=repmat("NOT_RUN_DEFAULT",4,1);
summaryFile=repmat("",4,1);
hourlyFile=repmat("",4,1);
eventSummaryFile=repmat("",4,1);
note=[ ...
    "Rebuilds compute load as 50% flexible and 50% rigid."; ...
    "Rebuilds compute load as 80% flexible and 20% rigid."; ...
    "Nearshore loss proxy; does not change cable CAPEX unless paired with cost table."; ...
    "Farshore loss proxy; does not change cable CAPEX unless paired with cost table."];
rerunManifest=table(caseId,parameterGroup,method,flexibleComputeRatio, ...
    cableLossFraction,dispatchStatus,summaryFile,hourlyFile, ...
    eventSummaryFile,note);
end

function selected=select_rerun_cases(rerunManifest,caseIds)
if isempty(caseIds)
    selected=true(height(rerunManifest),1);
else
    selected=ismember(rerunManifest.caseId,caseIds);
    missing=caseIds(~ismember(caseIds,rerunManifest.caseId));
    assert(isempty(missing),'Unknown rerun caseIds: %s',strjoin(missing,', '));
end
end

function [summary,eventSummary,hourlyLedger]=run_boundary_case( ...
    caseRow,outputDir,horizonH)
scenario=c5_build_annual_2025_multisource_scenario();
cfg=scenario.config;
cfg.h2Power.enabled=true;
cfg.h2Power.ratedMW=30;
in=scenario.input;
caseId=string(caseRow.caseId);
if isfinite(caseRow.flexibleComputeRatio)
    in=apply_compute_flexible_ratio(in,cfg,caseRow.flexibleComputeRatio);
end
if isfinite(caseRow.cableLossFraction)
    cfg.output.cableLossFraction=caseRow.cableLossFraction;
end
cfg.meta.parameterVersion=char("c5_56_"+caseId);
[sourceInput,sourceDetail]=v5_source_adapter(cfg,in.sourceCase);
base=rmfield(in,'sourceCase');
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
ids=string(cellfun(@(s)s.id,strategies,'UniformOutput',false));
idx=find(ids=="model_online_prior_posterior_event_aware",1);
assert(~isempty(idx),'Missing online strategy.');
strategy=strategies{idx};
strategy.id=char("c5_56_"+caseId);
strategy.strategyClass='C5_56_BOUNDARY_RERUN';
[summary,hourlyLedger]=c5_run_sequential_hourly( ...
    base,cfg,strategy,eventCode,false);
summary.sensitivityCaseId=repmat(caseId,height(summary),1);
summary.sensitivityParameterGroup=repmat( ...
    string(caseRow.parameterGroup),height(summary),1);
summary.sensitivityMethod=repmat( ...
    "ANNUAL_DISPATCH_RERUN",height(summary),1);
summary.scenarioId=repmat(char("C5_56_"+upper(caseId)),height(summary),1);
summary.extremeEventIncluded=repmat(any(eventCode~="NORMAL"), ...
    height(summary),1);
summary.stateCarryRule=repmat( ...
    "PREVIOUS_HOUR_TERMINAL_STATE; NO_EVENT_RESET_OR_INJECTION", ...
    height(summary),1);
summary.h2InventoryMinimumPolicy=repmat( ...
    "PHYSICAL_NONNEGATIVITY_ONLY; NO_OPERATIONAL_FLOOR",height(summary),1);
summary.h2PowerRatedMW=repmat(cfg.h2Power.ratedMW,height(summary),1);
summary.initialBessEnergyMWh=repmat( ...
    initialStateAudit.bessEnergyMWh,height(summary),1);
summary.initialH2InventoryKg=repmat( ...
    initialStateAudit.h2InventoryKg,height(summary),1);
baseForDemandAudit=v5_validate_and_normalize_input(cfg,base);
demandAudit=summarize_demand_by_event(baseForDemandAudit,eventCode);
totalCriticalDemandMWh=sum(demandAudit.totalCriticalDemandMWh);
summary.totalCriticalDemandMWh=repmat(totalCriticalDemandMWh, ...
    height(summary),1);
summary.criticalServiceRate=1-summary.ensMWh/totalCriticalDemandMWh;
eventSummary=summarize_by_event(hourlyLedger);
eventSummary=attach_critical_service_rate(eventSummary,demandAudit);

if ~isfolder(outputDir), mkdir(outputDir); end
writetable(summary,fullfile(outputDir,'c5_56_boundary_summary.csv'));
writetable(eventSummary,fullfile(outputDir,'c5_56_boundary_event_summary.csv'));
writetable(demandAudit,fullfile(outputDir,'c5_56_boundary_demand_audit.csv'));
writetable(hourlyLedger,fullfile(outputDir,'c5_56_boundary_hourly.csv'));
save(fullfile(outputDir,'c5_56_boundary_results.mat'), ...
    'summary','eventSummary','demandAudit','hourlyLedger','strategy', ...
    'caseRow','horizonH','-v7.3');
end

function in=apply_compute_flexible_ratio(in,cfg,flexRatio)
assert(flexRatio>=0 && flexRatio<=1,'flexRatio must be in [0,1].');
totalComputeMW=double(in.pComputeBaseDemandMW(:))+ ...
    double(in.pComputeFlexibleMaxMW(:));
totalComputeMW=min(totalComputeMW,cfg.compute.facilityMaxMW);
in.pComputeFlexibleMaxMW=flexRatio*totalComputeMW;
in.pComputeBaseDemandMW=(1-flexRatio)*totalComputeMW;
end

function eventSummary=summarize_by_event(hourlyLedger)
strategies=unique(hourlyLedger.strategyId,'stable');
rows=cell(0,1);
for i=1:numel(strategies)
    strategyIdx=hourlyLedger.strategyId==strategies(i);
    events=unique(hourlyLedger.eventCode(strategyIdx),'stable');
    for j=1:numel(events)
        idx=strategyIdx & hourlyLedger.eventCode==events(j);
        rows{end+1}=table(strategies(i),events(j),nnz(idx), ... %#ok<AGROW>
            sum(hourlyLedger.eAvailableMWh(idx)), ...
            sum(hourlyLedger.eSourceUsedMWh(idx)), ...
            sum(hourlyLedger.eCurtailmentMWh(idx)), ...
            sum(hourlyLedger.ensMWh(idx)), ...
            sum(hourlyLedger.outputRevenueCNY(idx)), ...
            sum(hourlyLedger.operatingCostCNY(idx)), ...
            sum(hourlyLedger.netGHGKgCO2e(idx)), ...
            nnz(hourlyLedger.planFallbackUsed(idx)), ...
            nnz(hourlyLedger.reserveConstraintRelaxationUsed(idx)), ...
            nnz(hourlyLedger.reliabilityRelaxationUsed(idx)), ...
            'VariableNames',{'strategyId','eventCode','hours', ...
            'eAvailableMWh','eSourceUsedMWh','eCurtailmentMWh', ...
            'ensMWh','outputRevenueCNY','operatingCostCNY', ...
            'netGHGKgCO2e','planFallbackHours', ...
            'reserveConstraintRelaxationHours', ...
            'reliabilityRelaxationHours'});
    end
end
eventSummary=vertcat(rows{:});
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

function out=merge_input(a,b)
out=a;
names=fieldnames(b);
for i=1:numel(names)
    out.(names{i})=b.(names{i});
end
end

function cfg=normalize_cable_distance(cfg,distanceKm)
if nargin<2 || isempty(distanceKm)
    distanceKm=NaN;
    if isfield(cfg,'output') && isfield(cfg.output,'cableDistanceKm') && ...
            isfinite(cfg.output.cableDistanceKm)
        distanceKm=cfg.output.cableDistanceKm;
    elseif isfield(cfg,'site') && isfield(cfg.site,'distanceToShoreKm') && ...
            isfinite(cfg.site.distanceToShoreKm)
        distanceKm=cfg.site.distanceToShoreKm;
    end
end
if ~isfinite(distanceKm)
    distanceKm=200;
end
cfg.output.cableDistanceKm=distanceKm;
cfg.site.distanceToShoreKm=distanceKm;
if isfield(cfg,'capacity') && isfield(cfg.capacity,'installed')
    if isfield(cfg.capacity.installed,'powerCableDistanceKm')
        cfg.capacity.installed.powerCableDistanceKm=distanceKm;
    end
    if isfield(cfg.capacity.installed,'fiberCableDistanceKm')
        cfg.capacity.installed.fiberCableDistanceKm=distanceKm;
    end
end
end

function value=distance_from_cfg(cfg)
if isfield(cfg,'output') && isfield(cfg.output,'cableDistanceKm') && ...
        isfinite(cfg.output.cableDistanceKm)
    value=cfg.output.cableDistanceKm;
else
    value=cfg.site.distanceToShoreKm;
end
end

function value=scalar(T,name,defaultValue)
if nargin<3
    defaultValue=NaN;
end
if ismember(name,T.Properties.VariableNames)
    value=double(T.(name)(1));
else
    value=defaultValue;
end
end

function out=ternary(condition,ifTrue,ifFalse)
if condition
    out=ifTrue;
else
    out=ifFalse;
end
end

function write_markdown_report(outputDir,priceSlope,priceSensitivity, ...
    costSensitivity,rerunManifest)
path=fullfile(outputDir,'c5_56_minimal_sensitivity_report.md');
fid=fopen(path,'w');
assert(fid>0,'Cannot write %s.',path);
cleanup=onCleanup(@() fclose(fid));
fprintf(fid,'# C5 5.6 Minimal-Rerun Sensitivity Pack\n\n');
fprintf(fid,['This pack separates fixed-dispatch post-processing from ', ...
    'slow annual dispatch reruns.\n\n']);
fprintf(fid,'## Price Slopes\n\n');
fprintf(fid,'| Parameter | Unit step | Annual revenue change / million CNY |\n');
fprintf(fid,'|---|---:|---:|\n');
for i=1:height(priceSlope)
    fprintf(fid,'| %s | %s | %.3f |\n',priceSlope.parameter(i), ...
        priceSlope.unitStep(i),priceSlope.annualRevenueChangeMillionCNY(i));
end
fprintf(fid,'\n## Fixed Dispatch Price Cases\n\n');
fprintf(fid,'| Case | Revenue / million CNY | Cash margin / million CNY | ENS / MWh |\n');
fprintf(fid,'|---|---:|---:|---:|\n');
for i=1:height(priceSensitivity)
    fprintf(fid,'| %s | %.3f | %.3f | %.3f |\n', ...
        priceSensitivity.caseId(i), ...
        priceSensitivity.outputRevenueCNY(i)/1e6, ...
        priceSensitivity.cashOperatingMarginCNY(i)/1e6, ...
        priceSensitivity.ensMWh(i));
end
fprintf(fid,'\n## Fixed Dispatch Cost Cases\n\n');
fprintf(fid,['| Case | Method | Annualized investment burden / million CNY ', ...
    '| Project annual net cash / million CNY |\n']);
fprintf(fid,'|---|---|---:|---:|\n');
for i=1:height(costSensitivity)
    fprintf(fid,'| %s | %s | %.3f | %.3f |\n', ...
        costSensitivity.caseId(i),costSensitivity.method(i), ...
        costSensitivity.annualizedInvestmentBurdenCNY(i)/1e6, ...
        costSensitivity.projectAnnualNetCashCNY(i)/1e6);
end
fprintf(fid,'\n## Dispatch Rerun Manifest\n\n');
fprintf(fid,'| Case | Parameter group | Status | Note |\n');
fprintf(fid,'|---|---|---|---|\n');
for i=1:height(rerunManifest)
    fprintf(fid,'| %s | %s | %s | %s |\n', ...
        rerunManifest.caseId(i),rerunManifest.parameterGroup(i), ...
        rerunManifest.dispatchStatus(i),rerunManifest.note(i));
end
fprintf(fid,['\nDefault output intentionally does not claim rerun evidence for ', ...
    'dispatch-changing parameters.\n']);
end
