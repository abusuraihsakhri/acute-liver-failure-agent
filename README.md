# Acute Liver Failure Calculator

### [Open the Live Application →](https://abusuraihsakhri.github.io/acute-liver-failure-agent/)

A Python library, command-line tool, and browser calculator for acute liver failure (ALF) prognostic calculations. The project implements King's College Hospital criteria, the published Acute Liver Failure Study Group (ALFSG) 21-day transplant-free survival model, West Haven encephalopathy staging, contextual acetaminophen assessment, and historical MELD/MELD-Na calculations.

The browser version runs the same Python engine locally with Pyodide. No clinical inputs are sent to an application server.

## Clinical scope and limitations

This calculator does not replace clinical assessment and does not make diagnostic, treatment, transplant-listing, or organ-allocation decisions.

- **King's College criteria (KCC)** are poor-prognosis criteria that support urgent transplant-center assessment. Meeting KCC does **not** by itself establish U.S. OPTN Status 1A.
- **ALFSG prognostic index** uses the published 2016 logistic model: encephalopathy grade, favorable/unfavorable etiology, vasopressor use, bilirubin, and INR. It estimates 21-day transplant-free survival and is not a listing rule.
- **MELD/MELD-Na** are retained as historical prognostic adjunct calculations for compatibility. They are not presented as the current OPTN allocation method for ALF.
- **Rumack-Matthew assessment** is applied only to acute-ingestion acetaminophen concentrations obtained from 4 through 24 hours after ingestion. The current high-risk line begins at 300 µg/mL at 4 hours. Out-of-range time points are reported as non-applicable instead of being clamped onto the nomogram.
- **Acetylcysteine** should not be stopped simply because a fixed 20- or 21-hour infusion has elapsed; use validated stopping criteria and poison-center/clinical-toxicology guidance.
- ALF evolves rapidly. Serial clinical assessment and early discussion with an experienced liver transplant center remain essential.

## Main features

- King's College criteria for acetaminophen and non-acetaminophen ALF
- ALFSG 2016 21-day transplant-free survival probability
- Historical MELD and MELD-Na calculation
- West Haven hepatic encephalopathy staging
- Acetaminophen treatment-line and high-risk-line assessment
- Hyperammonemia and neurocritical risk prompts
- Single-case, interactive, and CSV/JSON batch CLI workflows
- Client-side browser UI with light/dark themes and JSON export
- No runtime Python dependencies

## Browser application

The static interface uses Pyodide to execute `liver_failure_prognostic.py` directly in the browser. Clinical form data remain in browser memory and are not persisted by the application. The site loads the Pyodide runtime from jsDelivr; this external request does not include form values.

GitHub Pages deployment is defined in `.github/workflows/pages.yml`.

## Installation

Requires Python 3.10 or later.

```bash
git clone https://github.com/abusuraihsakhri/acute-liver-failure-agent.git
cd acute-liver-failure-agent
python -m pip install .
```

The package installs two equivalent console commands for compatibility:

```bash
acute-liver-failure-agent --help
acute-liver-failure-engine --help
```

You can also run the repository CLI directly:

```bash
python cli.py --help
```

## CLI examples

Single evaluation:

```bash
acute-liver-failure-agent --evaluate \
  --patient-id CASE-001 \
  --etiology acetaminophen \
  --ph 7.25 \
  --inr 6.8 \
  --cr 3.5 \
  --he-grade 3 \
  --json
```

If a post-resuscitation lactate is known, provide it explicitly:

```bash
acute-liver-failure-agent --evaluate \
  --etiology acetaminophen \
  --post-resuscitation-lactate 3.2 \
  --json
```

ALFSG vasopressor status is supplied separately:

```bash
acute-liver-failure-agent --evaluate --vasopressor-use --json
```

Batch evaluation:

```bash
acute-liver-failure-agent --batch sample.csv --json
```

Interactive mode:

```bash
acute-liver-failure-agent --interactive
```

## Python API

```python
from liver_failure_prognostic import (
    AcuteLiverFailureDecisionEngine,
    LiverFailureLabs,
)

labs = LiverFailureLabs(
    inr=4.2,
    bilirubin_mg_dl=10.0,
    creatinine_mg_dl=2.1,
    arterial_ph=7.34,
    sodium_meq_l=136,
    ammonia_umol_l=120,
)

result = AcuteLiverFailureDecisionEngine().evaluate_patient(
    patient_id="CASE-001",
    labs=labs,
    he_grade=2,
    age=42,
    etiology="dili",
    vasopressor_use=False,
)

print(result.kings_college.criteria_met)
print(result.alfsg.transplant_free_survival_pct)
```

## Development and testing

```bash
python -m pip install pytest build
pytest -v
python -m build
python -m pip install --force-reinstall dist/*.whl
python -m pip check
```

CI tests Python 3.10, 3.12, and 3.13, builds the distribution, verifies both installed console scripts, runs a CLI smoke test, and checks the browser JavaScript syntax.

## Technology

- Python standard library
- HTML, CSS, and vanilla JavaScript
- Pyodide for client-side Python execution
- GitHub Actions
- GitHub Pages

The browser UI targets current evergreen desktop and mobile browsers with WebAssembly support.

## References

- O'Grady JG, et al. *Gastroenterology*. 1989;97(2):439-445. King's College Hospital criteria.
- Koch DG, et al. *Clin Gastroenterol Hepatol*. 2016;14(8):1199-1206.e2. PMID: 27085756. ALFSG prognostic model.
- Tujios S, Stravitz RT, Lee WM. *Semin Liver Dis*. 2022;42(3):362-378. PMID: 36001996. Acute liver failure management update.
- Dart RC, et al. *JAMA Netw Open*. 2023;6(8):e2327739. PMID: 37552484. U.S./Canada acetaminophen poisoning consensus statement.
- OPTN Policies, current liver candidate status requirements: https://optn.transplant.hrsa.gov/policies-bylaws/policies/

## License

MIT. See [LICENSE](LICENSE).
