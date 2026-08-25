# Acute Liver Failure (ALF) Critical Care & Prognostication System

Production-grade hepatology and intensive care decision support engine implementing validated international criteria (**AASLD / EASL guidelines**) for **transplant listing**, **multiorgan failure prognostication**, **acetaminophen toxicity management**, and **neuro-ICU cerebral edema protocols**.

---

## Clinical Frameworks Implemented

### 1. King's College Hospital Criteria (*O'Grady et al., Gastroenterology 1989*)
- **Acetaminophen (APAP) Induced Acute Liver Failure**:
  * **Arterial $\text{pH} < 7.30$** (irrespective of grade of encephalopathy) after fluid resuscitation, **OR**
  * **Post-resuscitation arterial lactate $> 3.5\text{ mmol/L}$**, **OR**
  * Co-occurrence of all 3 within 24 hours:
    1. Grade III or IV Hepatic Encephalopathy
    2. Serum Creatinine $> 3.4\text{ mg/dL}$ ($300\ \mu\text{mol/L}$)
    3. $\text{INR} > 6.5$ (Prothrombin time $> 100\text{ s}$)
- **Non-Acetaminophen Induced Acute Liver Failure**:
  * **$\text{INR} > 6.5$** (standalone, irrespective of encephalopathy), **OR**
  * Any **3 of the following 5 subcriteria**:
    1. Age $< 10$ or $> 40$ years
    2. Etiology: Non-A/Non-B hepatitis, halothane, idiosyncratic drug-induced liver injury (DILI), or Wilson's disease
    3. Duration of jaundice before encephalopathy onset $> 7$ days
    4. $\text{INR} > 3.5$ (Prothrombin time $> 50\text{ s}$)
    5. Serum Bilirubin $> 17.5\text{ mg/dL}$ ($300\ \mu\text{mol/L}$)

---

### 2. MELD & MELD-Na Organ Allocation Score (*Kamath et al., Hepatology 2001*)

$$\text{MELD} = 9.57 \ln(\text{Cr}) + 3.78 \ln(\text{Bilirubin}) + 11.2 \ln(\text{INR}) + 6.43$$

$$\text{MELD-Na} = \text{MELD} + 1.32 \times (137 - \text{Na}) - [0.033 \times \text{MELD} \times (137 - \text{Na})]$$

Bounds:
- $\text{Creatinine} \in [1.0, 4.0]\text{ mg/dL}$ (dialysis automatically defaults to $4.0\text{ mg/dL}$).
- $\text{Bilirubin} \ge 1.0\text{ mg/dL}$, $\text{INR} \ge 1.0$.
- $\text{Sodium} \in [125, 137]\text{ mEq/L}$.
- Final score bounded between $6.0$ and $40.0$.

---

### 3. Acute Liver Failure Study Group (ALFSG) Prognostic Index
Estimates 21-day **Transplant-Free Survival (TFS)** based on:
- Hepatic coma grade (West Haven)
- INR and coagulopathy depth
- Total serum bilirubin
- Renal impairment (Creatinine)
- Patient age and etiology risk weighting (APAP vs Non-APAP)

---

### 4. Rumack-Matthew Nomogram & 21-Hour IV NAC Protocol
- 150 $\mu\text{g/mL}$ at 4 hours treatment line ($t_{1/2} = 4.0\text{ h}$).
- 21-hour intravenous N-acetylcysteine infusion:
  1. **Loading Dose**: $150\text{ mg/kg}$ in $200\text{ mL } \text{D}_5\text{W}$ over 60 minutes.
  2. **Second Dose**: $50\text{ mg/kg}$ in $500\text{ mL } \text{D}_5\text{W}$ over 4 hours.
  3. **Third Dose**: $100\text{ mg/kg}$ in $1000\text{ mL } \text{D}_5\text{W}$ over 16 hours.

---

### 5. Neuro-ICU Cerebral Edema & Ammonia Surveillance
- Arterial ammonia $> 150\ \mu\text{mol/L}$ or Grade $\ge 3$ HE triggers hyperosmolar protocol ($3\%$ hypertonic saline targeting serum sodium $145\text{--}150\text{ mEq/L}$, head of bed elevated $30^\circ$, elective endotracheal intubation for airway protection).

---

## Command Line Interface (CLI)

### 1. Single Patient Evaluation
```bash
python cli.py --evaluate --patient-id "ALF-001" --etiology "acetaminophen" --inr 6.8 --ph 7.22 --cr 3.6 --lactate 4.8 --he-grade 3
```

### 2. Output as JSON
```bash
python cli.py --evaluate --patient-id "ALF-002" --etiology "viral" --inr 4.2 --bili 19.5 --age 48 --format json
```

### 3. Batch Processing
```bash
python cli.py --batch patients.json --format json --output evaluated_cohort.json
```

### 4. Interactive Clinical Wizard
```bash
python cli.py --interactive
```

---

## Unit Testing

Run the comprehensive unit test suite:

```bash
python -m unittest discover -s tests -v
# or
python test_liver_failure_sentinel.py
```
