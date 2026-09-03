# Acute Liver Failure Critical Care & Transplant Decision Support Agent

A Python clinical decision support system and CLI tool for acute liver failure (ALF) critical care evaluation, prognostic scoring, and liver transplantation triage. Implements King's College Hospital Criteria, UNOS MELD and MELD-Na organ allocation scoring, the Acute Liver Failure Study Group (ALFSG) prognostic index, West Haven hepatic encephalopathy staging, Rumack-Matthew APAP nomogram assessment, and hyperammonemia/ICP management protocols.

Requires Python standard library only (zero external runtime dependencies).

---

## Features

- **King's College Hospital Criteria:** Evaluates both Acetaminophen (arterial pH < 7.30 or concurrent INR > 6.5, creatinine > 3.4 mg/dL, and Grade III/IV encephalopathy) and Non-Acetaminophen pathways (INR > 6.5 standalone or >= 3 of 5 unfavorable criteria: age <10 or >40, unfavorable etiology, jaundice-to-coma >7 days, INR > 3.5, bilirubin > 17.5 mg/dL).
- **MELD & MELD-Na Scoring:** Calculates 90-day/30-day mortality risk and UNOS Status 1A emergency prioritization tiers.
- **ALFSG Prognostic Index:** Estimates transplant-free survival (TFS) percentage using etiology, coma grade, INR, bilirubin, and creatinine predictors.
- **West Haven Hepatic Encephalopathy Staging:** Stages HE from Grade 0 (subclinical) through Grade IV (coma) with airway protection and cerebral edema risk stratification.
- **Rumack-Matthew Nomogram & NAC Protocol:** Evaluates acute acetaminophen overdose risk relative to 150 ug/mL and 200 ug/mL lines and outputs 21-hour IV N-Acetylcysteine dosing instructions.
- **Ammonia & ICP Risk Protocol:** Stratifies cerebral edema/herniation risk based on arterial ammonia and targets hyperosmolar therapy (3% hypertonic saline to serum Na 145-155 mEq/L).
- **Interactive Wizard & Batch CLI:** Guided clinical interview, single-patient evaluation flags, and batch processing of CSV patient rosters.

---

## Installation & Requirements

- Python 3.10+ (tested on 3.10, 3.11, 3.12)
- Zero external runtime dependencies. `pytest` is optional for running unit tests.

```bash
git clone https://github.com/abusuraihsakhri/acute-liver-failure-agent.git
cd acute-liver-failure-agent
```

---

## CLI Usage

### 1. Single Patient Evaluation
Evaluate acute liver failure presentation:
```bash
python cli.py --evaluate --patient-id PT-001 --etiology acetaminophen --ph 7.25 --inr 6.8 --cr 3.5 --he-grade 3
```
Output as JSON:
```bash
python cli.py --evaluate --patient-id PT-001 --etiology acetaminophen --ph 7.25 --inr 6.8 --cr 3.5 --he-grade 3 --json
```

### 2. Batch Patient CSV Evaluation
Evaluate patient cohort from CSV:
```bash
python cli.py -i sample.csv --json
```

### 3. Acetaminophen Toxicity Evaluation
Evaluate APAP ingestion with serum level:
```bash
python cli.py --evaluate --patient-id APAP-101 --etiology acetaminophen --apap-level 180 --apap-hours 6 --inr 3.2 --he-grade 2 --json
```

### 4. Interactive Clinical Wizard
Launch step-by-step terminal wizard:
```bash
python cli.py --interactive
```

---

## Python API Quickstart

```python
from liver_failure_prognostic import (
    LiverFailureLabs,
    AcuteLiverFailureDecisionEngine,
)

engine = AcuteLiverFailureDecisionEngine()

labs = LiverFailureLabs(
    inr=6.8,
    bilirubin_mg_dl=6.5,
    creatinine_mg_dl=3.5,
    arterial_ph=7.24,
    lactate_mmol_l=4.2,
    sodium_meq_l=136.0,
    ammonia_umol_l=120.0,
)

dossier = engine.evaluate_patient(
    patient_id="PT-001",
    labs=labs,
    he_grade=3,
    age=32,
    etiology="acetaminophen",
)

print(f"King's Criteria Met: {dossier.kings_college.criteria_met}")
print(f"Listing Urgency: {dossier.kings_college.transplant_listing_urgency}")
print(f"MELD Score: {dossier.meld.meld_score} | TFS: {dossier.alfsg.transplant_free_survival_pct}%")
for action in dossier.urgent_actions:
    print(f" -> {action}")
```

---

## Running Tests

Run the test suite using standard `unittest` or `pytest`:

```bash
python test_liver_failure_sentinel.py
# or
pytest -v
```

