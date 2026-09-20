"use strict";

const PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
let pyodide = null;
let lastResult = null;

const form = document.getElementById("alfForm");
const analyzeButton = document.getElementById("analyzeButton");
const exportButton = document.getElementById("exportButton");
const resetButton = document.getElementById("resetButton");
const themeToggle = document.getElementById("themeToggle");
const runtimeStatus = document.getElementById("runtimeStatus");
const emptyState = document.getElementById("emptyState");
const resultContent = document.getElementById("resultContent");
const errorBox = document.getElementById("errorBox");
const apapFields = document.getElementById("apapFields");

function optionalNumber(name) {
  const value = form.elements[name].value.trim();
  return value === "" ? null : Number(value);
}

function requiredNumber(name) {
  return Number(form.elements[name].value);
}

function isApapEtiology(value) {
  const normalized = value.toLowerCase();
  return normalized.includes("acetaminophen") ||
    normalized.includes("paracetamol") ||
    normalized.includes("apap");
}

function collectPayload() {
  const etiology = form.elements.etiology.value;
  const apapLevel = optionalNumber("apap_level");
  const apapHours = optionalNumber("apap_hours");

  if ((apapLevel === null) !== (apapHours === null)) {
    throw new Error("Provide both acetaminophen concentration and hours since ingestion, or leave both blank.");
  }

  return {
    patient_id: form.elements.patient_id.value.trim() || "CASE",
    etiology,
    age: requiredNumber("age"),
    he_grade: requiredNumber("he_grade"),
    jaundice_to_coma_days: requiredNumber("jaundice_days"),
    inr: requiredNumber("inr"),
    bili: requiredNumber("bili"),
    cr: requiredNumber("cr"),
    ph: requiredNumber("ph"),
    lactate: requiredNumber("lactate"),
    post_resuscitation_lactate: optionalNumber("post_lactate"),
    sodium: requiredNumber("sodium"),
    ammonia: requiredNumber("ammonia"),
    alt: requiredNumber("alt"),
    glucose: requiredNumber("glucose"),
    dialysis: form.elements.dialysis.checked,
    vasopressor_use: form.elements.vasopressor.checked,
    apap_level: isApapEtiology(etiology) ? apapLevel : null,
    apap_hours: isApapEtiology(etiology) ? apapHours : null,
  };
}

function safeText(elementId, value) {
  document.getElementById(elementId).textContent = String(value ?? "—");
}

function renderResult(result) {
  lastResult = result;
  emptyState.hidden = true;
  errorBox.hidden = true;
  resultContent.hidden = false;
  exportButton.disabled = false;

  safeText("kccValue", result.kings_college.criteria_met ? "Met" : "Not met");
  safeText("kccDetail", result.kings_college.transplant_listing_urgency);
  safeText("alfsgValue", `${result.alfsg.transplant_free_survival_pct}%`);
  safeText("alfsgDetail", result.alfsg.prognostic_tier);
  safeText("meldValue", `${result.meld.meld_score} / ${result.meld.meld_na_score}`);
  safeText("heValue", `Grade ${result.encephalopathy.grade}`);
  safeText("heDetail", result.encephalopathy.stage_name);

  safeText("ammoniaValue", `${result.ammonia_icp_risk.serum_ammonia_umol_l} µmol/L`);
  safeText(
    "ammoniaDetail",
    `${result.ammonia_icp_risk.risk_tier}. ${result.ammonia_icp_risk.recommended_target_sodium}`
  );

  const apapCard = document.getElementById("apapCard");
  if (result.apap_assessment) {
    apapCard.hidden = false;
    const nac = result.apap_assessment.nac_indicated;
    safeText("apapNac", nac === null ? "NAC: contextual" : (nac ? "NAC: indicated" : "NAC: not indicated"));
    safeText("apapRisk", result.apap_assessment.nomogram_risk);
  } else {
    apapCard.hidden = true;
  }

  const list = document.getElementById("actionsList");
  list.replaceChildren();
  for (const action of result.urgent_actions) {
    const item = document.createElement("li");
    item.textContent = action;
    list.appendChild(item);
  }
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

async function evaluateWithPython(payload) {
  pyodide.globals.set("payload_json", JSON.stringify(payload));
  try {
    const output = pyodide.runPython(`
import json
from dataclasses import asdict
from liver_failure_prognostic import LiverFailureLabs, AcuteLiverFailureDecisionEngine

p = json.loads(payload_json)
labs = LiverFailureLabs(
    inr=p["inr"],
    bilirubin_mg_dl=p["bili"],
    creatinine_mg_dl=p["cr"],
    arterial_ph=p["ph"],
    lactate_mmol_l=p["lactate"],
    sodium_meq_l=p["sodium"],
    ammonia_umol_l=p["ammonia"],
    alt_u_l=p["alt"],
    glucose_mg_dl=p["glucose"],
    on_dialysis=p["dialysis"],
)
evaluation = AcuteLiverFailureDecisionEngine().evaluate_patient(
    patient_id=p["patient_id"],
    labs=labs,
    he_grade=p["he_grade"],
    age=p["age"],
    etiology=p["etiology"],
    jaundice_to_coma_days=p["jaundice_to_coma_days"],
    apap_serum_ug_ml=p["apap_level"],
    apap_ingestion_hours=p["apap_hours"],
    post_resuscitation_lactate=p["post_resuscitation_lactate"],
    vasopressor_use=p["vasopressor_use"],
)
json.dumps(asdict(evaluation), allow_nan=False)
`);
    return JSON.parse(output);
  } finally {
    pyodide.globals.delete("payload_json");
  }
}

async function initializePython() {
  try {
    pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });
    const response = await fetch("./liver_failure_prognostic.py", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Unable to load clinical engine (HTTP ${response.status}).`);
    }
    const source = await response.text();
    pyodide.FS.writeFile("/home/pyodide/liver_failure_prognostic.py", source);
    pyodide.runPython("import liver_failure_prognostic");
    runtimeStatus.textContent = "Python engine ready";
    runtimeStatus.classList.add("ready");
    analyzeButton.disabled = false;
  } catch (error) {
    runtimeStatus.textContent = "Engine failed to load";
    runtimeStatus.classList.add("failed");
    showError(`The browser Python runtime could not start: ${error.message}`);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!pyodide) return;

  errorBox.hidden = true;
  analyzeButton.disabled = true;
  analyzeButton.textContent = "Analyzing…";
  try {
    const payload = collectPayload();
    const result = await evaluateWithPython(payload);
    renderResult(result);
  } catch (error) {
    showError(error.message || String(error));
  } finally {
    analyzeButton.disabled = false;
    analyzeButton.textContent = "Analyze";
  }
});

form.elements.etiology.addEventListener("change", () => {
  apapFields.hidden = !isApapEtiology(form.elements.etiology.value);
});

resetButton.addEventListener("click", () => {
  form.reset();
  apapFields.hidden = false;
  lastResult = null;
  exportButton.disabled = true;
  resultContent.hidden = true;
  errorBox.hidden = true;
  emptyState.hidden = false;
});

exportButton.addEventListener("click", () => {
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "alf-evaluation.json";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
});

themeToggle.addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.dataset.theme !== "dark";
  root.dataset.theme = dark ? "dark" : "light";
  themeToggle.textContent = dark ? "Light" : "Dark";
  themeToggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
});

initializePython();
