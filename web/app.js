const state = {
  busy: false,
  status: null,
  analysis: { datasets: [] },
  activeDataset: null,
  config: null,
  settingsRestored: false,
};

const fields = {
  lammps_bin: document.querySelector("#lammpsBin"),
  mpi_command: document.querySelector("#mpiCommand"),
  slurm_account: document.querySelector("#slurmAccount"),
  slurm_mail_user: document.querySelector("#slurmMailUser"),
  queue: document.querySelector("#queue"),
  nodes: document.querySelector("#nodes"),
  cores: document.querySelector("#cores"),
  start_data: document.querySelector("#startData"),
  final_data: document.querySelector("#finalData"),
  dry_run: document.querySelector("#dryRun"),
  submit: document.querySelector("#submitJobs"),
  run_dir: document.querySelector("#runDir"),
  run_name: document.querySelector("#runName"),
  show_advanced: document.querySelector("#showAdvanced"),
  target_density: document.querySelector("#targetDensity"),
  densify_temp: document.querySelector("#densifyTemp"),
  densify_pressure: document.querySelector("#densifyPressure"),
  densify_velocity_seed: document.querySelector("#densifyVelocitySeed"),
  densify_nvt_steps: document.querySelector("#densifyNvtSteps"),
  densify_npt_loops: document.querySelector("#densifyNptLoops"),
  densify_npt_steps: document.querySelector("#densifyNptSteps"),
  densify_rate: document.querySelector("#densifyRate"),
  densify_thermo_freq: document.querySelector("#densifyThermoFreq"),
  timestep: document.querySelector("#timestep"),
  anneal_heat_start: document.querySelector("#annealHeatStart"),
  anneal_heat_end: document.querySelector("#annealHeatEnd"),
  anneal_heat_steps: document.querySelector("#annealHeatSteps"),
  anneal_cool_low: document.querySelector("#annealCoolLow"),
  anneal_cool_step: document.querySelector("#annealCoolStep"),
  anneal_cool_steps: document.querySelector("#annealCoolSteps"),
  first_eq_temp: document.querySelector("#firstEqTemp"),
  first_eq_steps: document.querySelector("#firstEqSteps"),
  first_eq_loop_time: document.querySelector("#firstEqLoopTime"),
  final_eq_temp: document.querySelector("#finalEqTemp"),
  final_eq_steps: document.querySelector("#finalEqSteps"),
  final_eq_loop_time: document.querySelector("#finalEqLoopTime"),
  poly_same_settings: document.querySelector("#polySameSettings"),
  seed_mode_auto: document.querySelector("#seedModeAuto"),
  poly1_monomers: document.querySelector("#poly1Monomers"),
  poly1_xlinkd: document.querySelector("#poly1Xlinkd"),
  poly1_temp: document.querySelector("#poly1Temp"),
  poly1_prob: document.querySelector("#poly1Prob"),
  poly1_totaltime: document.querySelector("#poly1Totaltime"),
  poly1_loop_time: document.querySelector("#poly1LoopTime"),
  poly1_seed: document.querySelector("#poly1Seed"),
  poly2_monomers: document.querySelector("#poly2Monomers"),
  poly2_xlinkd: document.querySelector("#poly2Xlinkd"),
  poly2_temp: document.querySelector("#poly2Temp"),
  poly2_prob: document.querySelector("#poly2Prob"),
  poly2_totaltime: document.querySelector("#poly2Totaltime"),
  poly2_loop_time: document.querySelector("#poly2LoopTime"),
  poly2_seed: document.querySelector("#poly2Seed"),
  poly2_cool_start: document.querySelector("#poly2CoolStart"),
  poly2_cool_end: document.querySelector("#poly2CoolEnd"),
  poly2_cool_steps: document.querySelector("#poly2CoolSteps"),
};

const els = {
  readiness: document.querySelector("#readiness"),
  root: document.querySelector("#projectRoot"),
  missingBand: document.querySelector("#missingBand"),
  missingList: document.querySelector("#missingList"),
  pipeline: document.querySelector("#pipeline"),
  stageSummary: document.querySelector("#stageSummary"),
  artifactList: document.querySelector("#artifactList"),
  artifactSummary: document.querySelector("#artifactSummary"),
  runLog: document.querySelector("#runLog"),
  lastCommand: document.querySelector("#lastCommand"),
  buttons: Array.from(document.querySelectorAll("button")),
  prepareView: document.querySelector("#prepareView"),
  workflowView: document.querySelector("#workflowView"),
  analysisView: document.querySelector("#analysisView"),
  prepareTabBtn: document.querySelector("#prepareTabBtn"),
  workflowTabBtn: document.querySelector("#workflowTabBtn"),
  analysisTabBtn: document.querySelector("#analysisTabBtn"),
  datasetSelect: document.querySelector("#datasetSelect"),
  xColumn: document.querySelector("#xColumn"),
  yColumn: document.querySelector("#yColumn"),
  groupColumn: document.querySelector("#groupColumn"),
  chartType: document.querySelector("#chartType"),
  statsStrip: document.querySelector("#statsStrip"),
  canvas: document.querySelector("#analysisCanvas"),
  datasetTable: document.querySelector("#datasetTable"),
  polyStage2Fieldset: document.querySelector("#polyStage2Fieldset"),
  advancedFields: Array.from(document.querySelectorAll(".advanced-field")),
};

function saveSettings() {
  const payload = {};
  Object.entries(fields).forEach(([key, input]) => {
    if (input.type === "checkbox") {
      payload[key] = input.checked;
    } else {
      payload[key] = input.value;
    }
  });
  payload.seed_mode = fields.seed_mode_auto.checked ? "auto" : "keep";
  localStorage.setItem("polymerWorkflowSettings", JSON.stringify(payload));
}

function restoreSettings() {
  const raw = localStorage.getItem("polymerWorkflowSettings");
  if (!raw) return;
  try {
    const payload = JSON.parse(raw);
    Object.entries(fields).forEach(([key, input]) => {
      if (!(key in payload)) return;
      if (input.type === "checkbox") {
        input.checked = Boolean(payload[key]);
      } else {
        input.value = payload[key] ?? "";
      }
    });
    if (payload.seed_mode) {
      fields.seed_mode_auto.checked = payload.seed_mode !== "keep";
    }
    state.settingsRestored = true;
  } catch {
    localStorage.removeItem("polymerWorkflowSettings");
  }
}

function applyConfigDefaults(config) {
  if (!config || state.settingsRestored) return;
  state.config = config;
  const environment = config.environment || {};
  const workflow = config.workflow || {};
  const defaults = {
    lammps_bin: environment.lammps_bin,
    mpi_command: environment.mpi_command,
    slurm_account: environment.slurm_account,
    slurm_mail_user: environment.slurm_mail_user,
    queue: workflow.queue,
    nodes: workflow.nodes,
    cores: workflow.cores,
    start_data: workflow.start_data,
    final_data: workflow.final_data,
    dry_run: workflow.dry_run,
    submit: workflow.submit,
    run_dir: workflow.run_dir,
    run_name: workflow.run_name,
    poly_same_settings: workflow.poly_same_settings,
    show_advanced: workflow.show_advanced,
    target_density: workflow.target_density,
    densify_temp: workflow.densify_temp,
    densify_pressure: workflow.densify_pressure,
    densify_velocity_seed: workflow.densify_velocity_seed,
    densify_nvt_steps: workflow.densify_nvt_steps,
    densify_npt_loops: workflow.densify_npt_loops,
    densify_npt_steps: workflow.densify_npt_steps,
    densify_rate: workflow.densify_rate,
    densify_thermo_freq: workflow.densify_thermo_freq,
    timestep: workflow.timestep,
    anneal_heat_start: workflow.anneal_heat_start,
    anneal_heat_end: workflow.anneal_heat_end,
    anneal_heat_steps: workflow.anneal_heat_steps,
    anneal_cool_low: workflow.anneal_cool_low,
    anneal_cool_step: workflow.anneal_cool_step,
    anneal_cool_steps: workflow.anneal_cool_steps,
    first_eq_temp: workflow.first_eq_temp,
    first_eq_steps: workflow.first_eq_steps,
    first_eq_loop_time: workflow.first_eq_loop_time,
    final_eq_temp: workflow.final_eq_temp,
    final_eq_steps: workflow.final_eq_steps,
    final_eq_loop_time: workflow.final_eq_loop_time,
    seed_mode_auto: workflow.seed_mode !== "keep",
    poly1_monomers: workflow.poly1_monomers,
    poly1_xlinkd: workflow.poly1_xlinkd,
    poly1_temp: workflow.poly1_temp,
    poly1_prob: workflow.poly1_prob,
    poly1_totaltime: workflow.poly1_totaltime,
    poly1_loop_time: workflow.poly1_loop_time,
    poly1_seed: workflow.poly1_seed,
    poly2_monomers: workflow.poly2_monomers,
    poly2_xlinkd: workflow.poly2_xlinkd,
    poly2_temp: workflow.poly2_temp,
    poly2_prob: workflow.poly2_prob,
    poly2_totaltime: workflow.poly2_totaltime,
    poly2_loop_time: workflow.poly2_loop_time,
    poly2_seed: workflow.poly2_seed,
    poly2_cool_start: workflow.poly2_cool_start,
    poly2_cool_end: workflow.poly2_cool_end,
    poly2_cool_steps: workflow.poly2_cool_steps,
  };

  Object.entries(defaults).forEach(([key, value]) => {
    const input = fields[key];
    if (!input || value === undefined || value === null) return;
    if (input.type === "checkbox") {
      input.checked = Boolean(value);
    } else {
      input.value = value;
    }
  });
}

function options() {
  saveSettings();
  return {
    lammps_bin: fields.lammps_bin.value.trim(),
    mpi_command: fields.mpi_command.value.trim(),
    slurm_account: fields.slurm_account.value.trim(),
    slurm_mail_user: fields.slurm_mail_user.value.trim(),
    queue: fields.queue.value.trim(),
    nodes: fields.nodes.value,
    cores: fields.cores.value,
    start_data: fields.start_data.value.trim(),
    final_data: fields.final_data.value,
    dry_run: fields.dry_run.checked,
    submit: fields.submit.checked,
    run_dir: fields.run_dir.value.trim(),
    run_name: fields.run_name.value.trim(),
    target_density: fields.target_density.value,
    densify_temp: fields.densify_temp.value,
    densify_pressure: fields.densify_pressure.value,
    densify_velocity_seed: fields.densify_velocity_seed.value,
    densify_nvt_steps: fields.densify_nvt_steps.value,
    densify_npt_loops: fields.densify_npt_loops.value,
    densify_npt_steps: fields.densify_npt_steps.value,
    densify_rate: fields.densify_rate.value,
    densify_thermo_freq: fields.densify_thermo_freq.value,
    timestep: fields.timestep.value,
    anneal_heat_start: fields.anneal_heat_start.value,
    anneal_heat_end: fields.anneal_heat_end.value,
    anneal_heat_steps: fields.anneal_heat_steps.value,
    anneal_cool_low: fields.anneal_cool_low.value,
    anneal_cool_step: fields.anneal_cool_step.value,
    anneal_cool_steps: fields.anneal_cool_steps.value,
    first_eq_temp: fields.first_eq_temp.value,
    first_eq_steps: fields.first_eq_steps.value,
    first_eq_loop_time: fields.first_eq_loop_time.value,
    final_eq_temp: fields.final_eq_temp.value,
    final_eq_steps: fields.final_eq_steps.value,
    final_eq_loop_time: fields.final_eq_loop_time.value,
    poly_same_settings: fields.poly_same_settings.checked,
    show_advanced: fields.show_advanced.checked,
    seed_mode: fields.seed_mode_auto.checked ? "auto" : "keep",
    poly1_monomers: fields.poly1_monomers.value,
    poly1_xlinkd: fields.poly1_xlinkd.value,
    poly1_temp: fields.poly1_temp.value,
    poly1_prob: fields.poly1_prob.value,
    poly1_totaltime: fields.poly1_totaltime.value,
    poly1_loop_time: fields.poly1_loop_time.value,
    poly1_seed: fields.poly1_seed.value,
    poly2_monomers: fields.poly2_monomers.value,
    poly2_xlinkd: fields.poly2_xlinkd.value,
    poly2_temp: fields.poly2_temp.value,
    poly2_prob: fields.poly2_prob.value,
    poly2_totaltime: fields.poly2_totaltime.value,
    poly2_loop_time: fields.poly2_loop_time.value,
    poly2_seed: fields.poly2_seed.value,
    poly2_cool_start: fields.poly2_cool_start.value,
    poly2_cool_end: fields.poly2_cool_end.value,
    poly2_cool_steps: fields.poly2_cool_steps.value,
  };
}

function syncPolymerizationControls() {
  const same = fields.poly_same_settings.checked;
  const advanced = fields.show_advanced.checked;
  if (same) {
    fields.poly2_monomers.value = fields.poly1_monomers.value;
    fields.poly2_xlinkd.value = fields.poly1_xlinkd.value;
    fields.poly2_temp.value = fields.poly1_temp.value;
    fields.poly2_prob.value = fields.poly1_prob.value;
    fields.poly2_totaltime.value = fields.poly1_totaltime.value;
    fields.poly2_loop_time.value = fields.poly1_loop_time.value;
  }
  [fields.poly2_monomers, fields.poly2_xlinkd, fields.poly2_temp, fields.poly2_prob, fields.poly2_totaltime, fields.poly2_loop_time].forEach((input) => {
    input.disabled = same;
  });
  els.polyStage2Fieldset.classList.toggle("mirrored", same);
  els.advancedFields.forEach((el) => {
    el.classList.toggle("hidden", !advanced);
  });
}


function setBusy(next) {
  state.busy = next;
  els.buttons.forEach((button) => {
    button.disabled = next;
  });
}

function statusText(stage) {
  if (stage.outputExists) return "complete";
  if (stage.jobScriptExists) return "generated";
  if (stage.inputExists) return "ready";
  return "missing";
}

function dotClass(value) {
  if (value) return "dot on";
  return "dot warn";
}

function renderReadiness(status) {
  els.root.textContent = status.root;
  els.readiness.className = `readiness ${status.ready ? "ready" : "blocked"}`;
  els.readiness.textContent = status.ready ? "Ready" : "Needs input";

  els.missingList.innerHTML = "";
  if (status.missing.length === 0) {
    const pill = document.createElement("span");
    pill.className = "pill ready";
    pill.textContent = "All required inputs are present";
    els.missingList.append(pill);
    return;
  }

  status.missing.forEach((item) => {
    const pill = document.createElement("span");
    pill.className = "pill missing";
    pill.textContent = item;
    els.missingList.append(pill);
  });
}

function renderFinalDataSelect(status) {
  const configured = state.config?.workflow?.final_data || "";
  const previous = fields.final_data.value || configured;
  fields.final_data.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Auto-detect";
  fields.final_data.append(placeholder);

  status.dataCandidates.forEach((candidate) => {
    const option = document.createElement("option");
    option.value = candidate.name;
    option.textContent = candidate.name;
    fields.final_data.append(option);
  });

  if (previous) {
    fields.final_data.value = previous;
  }
}

function renderPipeline(status) {
  els.pipeline.innerHTML = "";
  const complete = status.stages.filter((stage) => stage.outputExists).length;
  const generated = status.stages.filter((stage) => stage.jobScriptExists).length;
  els.stageSummary.textContent = `${complete} complete, ${generated} job files`;

  status.stages.forEach((stage) => {
    const article = document.createElement("article");
    article.className = `stage ${statusText(stage)}`;
    article.innerHTML = `
      <h3>${stage.label}</h3>
      <div class="stage-meta">
        <div>${stage.input}</div>
        <div>${stage.walltime}</div>
        <div class="state-line"><span>Input</span><span class="${dotClass(stage.inputExists)}"></span></div>
        <div class="state-line"><span>Job file</span><span class="${stage.jobScriptExists ? "dot on" : "dot"}"></span></div>
        <div class="state-line"><span>Output</span><span class="${stage.outputExists ? "dot on" : "dot"}"></span></div>
      </div>
    `;
    els.pipeline.append(article);
  });
}

function renderArtifacts(status) {
  const artifacts = status.artifacts;
  const total = Object.values(artifacts).reduce((sum, items) => sum + items.length, 0);
  els.artifactSummary.textContent = `${total} files`;
  els.artifactList.innerHTML = "";

  Object.entries(artifacts).forEach(([label, items]) => {
    const group = document.createElement("div");
    group.className = "artifact-group";
    const title = document.createElement("strong");
    title.textContent = `${label} (${items.length})`;
    group.append(title);

    if (items.length === 0) {
      const empty = document.createElement("span");
      empty.textContent = "None";
      group.append(empty);
    } else {
      items.slice(0, 10).forEach((item) => {
        const span = document.createElement("span");
        span.textContent = item;
        group.append(span);
      });
      if (items.length > 10) {
        const more = document.createElement("span");
        more.textContent = `${items.length - 10} more`;
        group.append(more);
      }
    }
    els.artifactList.append(group);
  });
}

function hydrateEnvironment(status) {
  if (!fields.lammps_bin.value && status.environment.LAMMPS_BIN) {
    fields.lammps_bin.value = status.environment.LAMMPS_BIN;
  }
  if (!fields.slurm_account.value && status.environment.SLURM_ACCOUNT) {
    fields.slurm_account.value = status.environment.SLURM_ACCOUNT;
  }
  if (!fields.slurm_mail_user.value && status.environment.SLURM_MAIL_USER) {
    fields.slurm_mail_user.value = status.environment.SLURM_MAIL_USER;
  }
  if (!fields.mpi_command.value && status.environment.MPI_COMMAND) {
    fields.mpi_command.value = status.environment.MPI_COMMAND;
  }
}

function renderStatus(status) {
  state.status = status;
  state.config = status.config || state.config;
  applyConfigDefaults(status.config);
  hydrateEnvironment(status);
  renderReadiness(status);
  renderFinalDataSelect(status);
  renderPipeline(status);
  renderArtifacts(status);
  syncPolymerizationControls();
}

function setView(view) {
  const isPrepare = view === "prepare";
  const isWorkflow = view === "workflow";
  const isAnalysis = view === "analysis";
  els.prepareView.classList.toggle("active", isPrepare);
  els.workflowView.classList.toggle("active", isWorkflow);
  els.analysisView.classList.toggle("active", isAnalysis);
  els.prepareTabBtn.classList.toggle("active", isPrepare);
  els.workflowTabBtn.classList.toggle("active", isWorkflow);
  els.analysisTabBtn.classList.toggle("active", isAnalysis);
  if (isAnalysis) {
    drawAnalysis();
  }
}


async function refreshStatus() {
  const params = new URLSearchParams();
  if (fields.start_data.value.trim()) {
    params.set("start_data", fields.start_data.value.trim());
  }
  if (fields.run_dir.value.trim()) {
    params.set("run_dir", fields.run_dir.value.trim());
  }
  const url = params.toString() ? `/api/status?${params}` : "/api/status";
  const response = await fetch(url);
  const payload = await response.json();
  if (!response.ok || payload.error) {
    throw new Error(payload.error || "Status request failed");
  }
  renderStatus(payload);
}

async function refreshAnalysis() {
  const response = await fetch("/api/analysis");
  const payload = await response.json();
  if (!response.ok || payload.error) {
    throw new Error(payload.error || "Analysis request failed");
  }
  state.analysis = payload;
  state.config = payload.config || state.config;
  renderAnalysisControls();
}



async function runAction(action) {
  setBusy(true);
  els.runLog.textContent = "Running...";
  els.lastCommand.textContent = action;

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, options: options() }),
    });
    const payload = await response.json();
    if (!response.ok || payload.error) {
      throw new Error(payload.error || "Workflow action failed");
    }
    renderStatus(payload.status);
    if (payload.analysis) {
      state.analysis = payload.analysis;
      state.config = payload.analysis.config || state.config;
      renderAnalysisControls();
    } else {
      await refreshAnalysis();
    }
    els.lastCommand.textContent = payload.command;
    els.runLog.textContent = payload.output || "Completed with no output.";
    if (!payload.ok) {
      els.runLog.textContent = `${els.runLog.textContent}\n\nExit code: ${payload.returncode}`;
    }
  } catch (error) {
    els.runLog.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function makeDummyData() {
  setBusy(true);
  els.runLog.textContent = "Creating dummy data...";
  els.lastCommand.textContent = "POST /api/dummy-data";

  try {
    const response = await fetch("/api/dummy-data", { method: "POST" });
    const payload = await response.json();
    if (!response.ok || payload.error) {
      throw new Error(payload.error || "Dummy data generation failed");
    }
    renderStatus(payload.status);
    state.analysis = payload.analysis;
    state.config = payload.analysis?.config || payload.status?.config || state.config;
    renderAnalysisControls();
    els.runLog.textContent = payload.output || "Dummy data created.";
    setView("analysis");
  } catch (error) {
    els.runLog.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

function optionList(select, values, selectedValue = "") {
  select.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value || "None";
    select.append(option);
  });
  if (selectedValue && values.includes(selectedValue)) {
    select.value = selectedValue;
  }
}

function chooseDefaults(dataset) {
  const columns = dataset.numericColumns || [];
  const name = dataset.id || "";
  let x = columns[0] || "";
  let y = columns[1] || columns[0] || "";
  let group = "";

  if (name.includes("mechanics")) {
    x = "strain";
    y = "stress_MPa";
    group = "direction";
  } else if (name.includes("thermal")) {
    x = "position_A";
    y = "temperature_K";
  } else if (name.includes("thermo")) {
    x = "step";
    y = "density_gcc";
  }
  return { x, y, group };
}

function renderAnalysisControls() {
  const datasets = state.analysis.datasets || [];
  const analysisConfig = state.config?.analysis || {};
  const currentId = els.datasetSelect.value || analysisConfig.dataset || datasets[0]?.id || "";
  els.datasetSelect.innerHTML = "";

  if (datasets.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No datasets yet";
    els.datasetSelect.append(option);
    state.activeDataset = null;
    renderEmptyAnalysis();
    return;
  }

  datasets.forEach((dataset) => {
    const option = document.createElement("option");
    option.value = dataset.id;
    option.textContent = `${dataset.name} (${dataset.rowCount})`;
    els.datasetSelect.append(option);
  });

  if (datasets.some((dataset) => dataset.id === currentId)) {
    els.datasetSelect.value = currentId;
  }

  state.activeDataset = datasets.find((dataset) => dataset.id === els.datasetSelect.value) || datasets[0];
  const defaults = chooseDefaults(state.activeDataset);
  optionList(els.xColumn, state.activeDataset.numericColumns, els.xColumn.value || analysisConfig.x_column || defaults.x);
  optionList(els.yColumn, state.activeDataset.numericColumns, els.yColumn.value || analysisConfig.y_column || defaults.y);
  optionList(els.groupColumn, ["", ...state.activeDataset.columns], els.groupColumn.value || analysisConfig.group_column || defaults.group);
  if (analysisConfig.chart_type) {
    els.chartType.value = analysisConfig.chart_type;
  }
  drawAnalysis();
}

function renderEmptyAnalysis() {
  els.statsStrip.innerHTML = '<div class="stat-card"><span>Status</span><strong>No analysis CSV files</strong></div>';
  const context = els.canvas.getContext("2d");
  context.clearRect(0, 0, els.canvas.width, els.canvas.height);
  els.datasetTable.innerHTML = "";
}

function statsFor(values) {
  const numeric = values.filter((value) => Number.isFinite(value));
  if (!numeric.length) return { min: 0, max: 0, avg: 0 };
  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  const avg = numeric.reduce((sum, value) => sum + value, 0) / numeric.length;
  return { min, max, avg };
}

function formatNumber(value) {
  if (!Number.isFinite(value)) return "n/a";
  if (Math.abs(value) >= 100000) return value.toExponential(2);
  return Number(value.toFixed(4)).toString();
}

function groupedRows(rows, groupColumn) {
  if (!groupColumn) return new Map([["Series", rows]]);
  const groups = new Map();
  rows.forEach((row) => {
    const key = String(row[groupColumn] ?? "Unknown");
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  });
  return groups;
}

function drawAnalysis() {
  const dataset = state.activeDataset;
  if (!dataset) {
    renderEmptyAnalysis();
    return;
  }

  const xKey = els.xColumn.value;
  const yKey = els.yColumn.value;
  const groupKey = els.groupColumn.value;
  const rows = dataset.rows.filter((row) => Number.isFinite(row[xKey]) && Number.isFinite(row[yKey]));
  const xValues = rows.map((row) => row[xKey]);
  const yValues = rows.map((row) => row[yKey]);
  const xStats = statsFor(xValues);
  const yStats = statsFor(yValues);
  renderStats(dataset, rows, xKey, yKey, xStats, yStats);
  renderTable(dataset);
  drawCanvas(rows, xKey, yKey, groupKey, xStats, yStats);
}

function renderStats(dataset, rows, xKey, yKey, xStats, yStats) {
  els.statsStrip.innerHTML = "";
  [
    ["Dataset", dataset.file],
    ["Rows plotted", rows.length],
    [`${xKey} range`, `${formatNumber(xStats.min)} to ${formatNumber(xStats.max)}`],
    [`${yKey} avg`, formatNumber(yStats.avg)],
  ].forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "stat-card";
    card.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    els.statsStrip.append(card);
  });
}

function renderTable(dataset) {
  const rows = dataset.rows.slice(0, 80);
  const head = `<thead><tr>${dataset.columns.map((column) => `<th>${column}</th>`).join("")}</tr></thead>`;
  const body = rows
    .map((row) => `<tr>${dataset.columns.map((column) => `<td>${row[column] ?? ""}</td>`).join("")}</tr>`)
    .join("");
  els.datasetTable.innerHTML = `${head}<tbody>${body}</tbody>`;
}

function drawCanvas(rows, xKey, yKey, groupKey, xStats, yStats) {
  const canvas = els.canvas;
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.max(900, Math.floor(rect.width * scale));
  canvas.height = Math.max(420, Math.floor(rect.height * scale));
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);

  const width = canvas.width / scale;
  const height = canvas.height / scale;
  const pad = { left: 68, right: 24, top: 28, bottom: 58 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const colors = ["#0f766e", "#b35a1f", "#36566f", "#7c2d12", "#166534", "#9333ea", "#be123c"];
  const chartType = els.chartType.value;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  if (!rows.length) {
    ctx.fillStyle = "#65716d";
    ctx.font = "16px Avenir Next, sans-serif";
    ctx.fillText("No numeric rows for this selection", pad.left, pad.top + 30);
    return;
  }

  const xMin = xStats.min;
  const xMax = xStats.max === xMin ? xMin + 1 : xStats.max;
  const yMin = Math.min(0, yStats.min);
  const yMax = yStats.max === yMin ? yMin + 1 : yStats.max;
  const xScale = (value) => pad.left + ((value - xMin) / (xMax - xMin)) * plotW;
  const yScale = (value) => pad.top + plotH - ((value - yMin) / (yMax - yMin)) * plotH;

  ctx.strokeStyle = "#d9ded6";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#65716d";
  ctx.font = "12px SFMono-Regular, Menlo, monospace";

  for (let tick = 0; tick <= 5; tick += 1) {
    const x = pad.left + (plotW * tick) / 5;
    const y = pad.top + (plotH * tick) / 5;
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, pad.top + plotH);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(pad.left + plotW, y);
    ctx.stroke();
    ctx.fillText(formatNumber(xMin + ((xMax - xMin) * tick) / 5), x - 18, pad.top + plotH + 24);
    ctx.fillText(formatNumber(yMax - ((yMax - yMin) * tick) / 5), 8, y + 4);
  }

  ctx.strokeStyle = "#18221f";
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + plotH);
  ctx.lineTo(pad.left + plotW, pad.top + plotH);
  ctx.stroke();

  const groups = groupedRows(rows, groupKey);
  Array.from(groups.entries()).forEach(([groupName, groupRows], groupIndex) => {
    const color = colors[groupIndex % colors.length];
    const sorted = groupRows.slice().sort((a, b) => a[xKey] - b[xKey]);

    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2.2;

    if (chartType === "line") {
      ctx.beginPath();
      sorted.forEach((row, index) => {
        const x = xScale(row[xKey]);
        const y = yScale(row[yKey]);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }

    sorted.forEach((row, index) => {
      const x = xScale(row[xKey]);
      const y = yScale(row[yKey]);
      if (chartType === "bar") {
        const barW = Math.max(3, plotW / Math.max(sorted.length, 40) - 1);
        ctx.fillRect(x - barW / 2, y, barW, pad.top + plotH - y);
      } else {
        ctx.beginPath();
        ctx.arc(x, y, chartType === "scatter" ? 3.3 : 2.2, 0, Math.PI * 2);
        ctx.fill();
      }

      if (index === 0 && groupKey) {
        ctx.fillText(groupName, x + 6, y - 6);
      }
    });
  });

  ctx.fillStyle = "#18221f";
  ctx.font = "13px Avenir Next, sans-serif";
  ctx.fillText(xKey, pad.left + plotW / 2 - 24, height - 16);
  ctx.save();
  ctx.translate(18, pad.top + plotH / 2 + 24);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(yKey, 0, 0);
  ctx.restore();
}

function wireEvents() {
  document.querySelector("#refreshBtn").addEventListener("click", async () => {
    setBusy(true);
    try {
      await refreshStatus();
      els.runLog.textContent = "Status refreshed.";
      els.lastCommand.textContent = "GET /api/status";
    } catch (error) {
      els.runLog.textContent = error.message;
    } finally {
      setBusy(false);
    }
  });

  document.querySelector("#validateBtn").addEventListener("click", () => runAction("status"));
  document.querySelector("#prepareBtn").addEventListener("click", () => runAction("prepare"));
  document.querySelector("#buildBtn").addEventListener("click", () => runAction("build"));
  document.querySelector("#postprocessBtn").addEventListener("click", () => runAction("postprocess"));
  document.querySelector("#allBtn").addEventListener("click", () => runAction("all"));
  document.querySelector("#dummyBtn").addEventListener("click", makeDummyData);
  els.prepareTabBtn.addEventListener("click", () => setView("prepare"));
  els.workflowTabBtn.addEventListener("click", () => setView("workflow"));
  els.analysisTabBtn.addEventListener("click", () => setView("analysis"));
  els.datasetSelect.addEventListener("change", () => {
    state.activeDataset = (state.analysis.datasets || []).find((dataset) => dataset.id === els.datasetSelect.value);
    if (state.activeDataset) {
      const defaults = chooseDefaults(state.activeDataset);
      optionList(els.xColumn, state.activeDataset.numericColumns, defaults.x);
      optionList(els.yColumn, state.activeDataset.numericColumns, defaults.y);
      optionList(els.groupColumn, ["", ...state.activeDataset.columns], defaults.group);
    }
    drawAnalysis();
  });
  [els.xColumn, els.yColumn, els.groupColumn, els.chartType].forEach((select) => {
    select.addEventListener("change", drawAnalysis);
  });
  window.addEventListener("resize", () => {
    if (els.analysisView.classList.contains("active")) drawAnalysis();
  });

  [fields.poly1_monomers, fields.poly1_xlinkd, fields.poly1_temp, fields.poly1_prob, fields.poly1_totaltime, fields.poly1_loop_time].forEach((field) => {
    field.addEventListener("input", () => {
      syncPolymerizationControls();
      saveSettings();
    });
  });
  [fields.poly_same_settings, fields.show_advanced].forEach((field) => {
    field.addEventListener("change", syncPolymerizationControls);
  });

  Object.values(fields).forEach((field) => {
    field.addEventListener("change", () => {
      syncPolymerizationControls();
      saveSettings();
    });
  });
}

async function init() {
  restoreSettings();
  syncPolymerizationControls();
  wireEvents();
  try {
    await refreshStatus();
    await refreshAnalysis();
  } catch (error) {
    els.runLog.textContent = error.message;
    els.readiness.className = "readiness blocked";
    els.readiness.textContent = "Offline";
  }
}

init();
