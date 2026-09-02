# Acute Liver Failure Agent

> **Domain:** Gastroenterology, Hepatology & Clinical Nutrition  
> **Reference Guidelines & Standards:** `AASLD & ACG Clinical Practice Guidelines`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Acute Liver Failure Agent** is an advanced analytical and computational platform implementing King's College Criteria & ALFSG Transplant Referral Agent.

Acute Liver Failure (ALF) Critical Care Decision Support & Prognostication System.

Clinical Models Implemented:
1. King's College Hospital Criteria (Acetaminophen & Non-Acetaminophen Pathways).
2. UNOS MELD & MELD-Na / MELD 3.0 Organ Allocation Scoring.
3. Acute Liver Failure Study Group (ALFSG) Prognostic Index (Transplant-Free Survival).
4. West Haven Staging of Hepatic Encephalopathy (Grades 0 to IV).
5. Rumack-Matthew Nomogram for Acetaminophen Toxicity & IV N-Acetylcysteine (NAC) Protocol.
6. Hyperammonemia & Intracranial Hypertension / Cerebral Edema Risk Stratification.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`LiverFailureLabs`** — dedicated module for liver failure labs evaluation and state verification.
- **`KingsCollegeResult`** — dedicated module for kings college result evaluation and state verification.
- **`MELDResult`** — dedicated module for m e l d result evaluation and state verification.
- **`ALFSGResult`** — dedicated module for a l f s g result evaluation and state verification.
- **`APAPToxicityResult`** — dedicated module for a p a p toxicity result evaluation and state verification.
- **`HepaticEncephalopathyStaging`** — dedicated module for hepatic encephalopathy staging evaluation and state verification.

---

## 📐 Mathematical Formulation & Logic

```text
  meld_score = round(max(6.0, min(40.0, raw_meld)), 1)
  meld_na_score = round(meld_na, 1)
  risk = "Above 200 High-Risk Line (Probable Severe Hepatotoxicity)"
  risk = "Above 150 Treatment Line (Possible Hepatotoxicity)"
  risk = "Below Treatment Line (Low Risk of Hepatotoxicity)"
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --interactive <value> --evaluate <value> --batch <value> --patient-id <value>
```

### Parameter Reference
- `--interactive`: Specifies input measurement or parameter value.
- `--evaluate`: Specifies input measurement or parameter value.
- `--batch`: Specifies input measurement or parameter value.
- `--patient-id`: Specifies input measurement or parameter value.
- `--etiology`: Specifies input measurement or parameter value.
- `--age`: Specifies input measurement or parameter value.
- `--he-grade`: Specifies input measurement or parameter value.
- `--jaundice-to-coma-days`: Specifies input measurement or parameter value.
- `--inr`: Specifies input measurement or parameter value.
- `--bili`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `case_id` | Parameter / observation metric | Required |
| `patient_synthetic_id` | Parameter / observation metric | Required |
| `metric_primary` | Parameter / observation metric | Required |
| `metric_secondary` | Parameter / observation metric | Required |
| `is_stat` | Parameter / observation metric | Required |
| `status_flag` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t acute-liver-failure-agent .
docker run -p 8000:8000 acute-liver-failure-agent
```
