#!/usr/bin/env python3
"""Command-line interface for acute liver failure decision support."""

import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, Optional

from liver_failure_prognostic import (
    AcuteLiverFailureDecisionEngine,
    LiverFailureLabs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="acute-liver-failure-agent",
        description=(
            "Acute liver failure prognostic decision support. Outputs do not "
            "constitute transplant-listing or organ-allocation decisions."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--interactive", "-I", action="store_true")
    mode.add_argument("--evaluate", action="store_true")
    mode.add_argument("--batch", "-i", metavar="FILE")

    parser.add_argument("--patient-id", default="PT-001")
    parser.add_argument("--etiology", default="acetaminophen")
    parser.add_argument("--age", type=int, default=35)
    parser.add_argument("--he-grade", type=int, choices=range(5), default=2)
    parser.add_argument("--jaundice-to-coma-days", type=int, default=4)

    parser.add_argument("--inr", type=float, default=2.8)
    parser.add_argument("--bili", type=float, default=6.5)
    parser.add_argument("--cr", type=float, default=1.8)
    parser.add_argument("--ph", type=float, default=7.34)
    parser.add_argument("--lactate", type=float, default=2.4)
    parser.add_argument(
        "--post-resuscitation-lactate",
        type=float,
        default=None,
        help="Explicit post-resuscitation arterial lactate for acetaminophen KCC.",
    )
    parser.add_argument("--sodium", type=float, default=136.0)
    parser.add_argument("--ammonia", type=float, default=110.0)
    parser.add_argument("--alt", type=float, default=3500.0)
    parser.add_argument("--ast", type=float, default=4200.0)
    parser.add_argument("--glucose", type=float, default=85.0)
    parser.add_argument("--dialysis", action="store_true")
    parser.add_argument("--vasopressor-use", action="store_true")

    parser.add_argument("--apap-level", type=float, default=None)
    parser.add_argument("--apap-hours", type=float, default=None)

    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", "-o", metavar="FILE")
    return parser


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _optional_float(record: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return float(value)
    return None


def _record_to_evaluation(
    engine: AcuteLiverFailureDecisionEngine,
    record: Dict[str, Any],
):
    labs = LiverFailureLabs(
        inr=float(record.get("inr", 1.0)),
        bilirubin_mg_dl=float(record.get("bili", record.get("bilirubin", 1.0))),
        creatinine_mg_dl=float(record.get("cr", record.get("creatinine", 1.0))),
        arterial_ph=float(record.get("ph", 7.4)),
        lactate_mmol_l=float(record.get("lactate", 1.0)),
        sodium_meq_l=float(record.get("sodium", 140.0)),
        ammonia_umol_l=float(record.get("ammonia", 40.0)),
        alt_u_l=float(record.get("alt", 30.0)),
        ast_u_l=float(record.get("ast", 30.0)),
        glucose_mg_dl=float(record.get("glucose", 95.0)),
        on_dialysis=_bool_value(record.get("dialysis", False)),
    )

    return engine.evaluate_patient(
        patient_id=str(record.get("patient_id", "PT")),
        labs=labs,
        he_grade=int(record.get("he_grade", 0)),
        age=int(record.get("age", 40)),
        etiology=str(record.get("etiology", "acetaminophen")),
        jaundice_to_coma_days=int(record.get("jaundice_to_coma_days", 4)),
        apap_serum_ug_ml=_optional_float(record, "apap_level", "apap_serum_ug_ml"),
        apap_ingestion_hours=_optional_float(record, "apap_hours", "apap_ingestion_hours"),
        post_resuscitation_lactate=_optional_float(
            record, "post_resuscitation_lactate", "post_resus_lactate"
        ),
        vasopressor_use=_bool_value(record.get("vasopressor_use", False)),
    )


def _write_or_print(text: str, output: Optional[str]) -> int:
    if output:
        try:
            Path(output).write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"Error writing output file: {exc}", file=sys.stderr)
            return 1
    else:
        print(text)
    return 0


def _evaluation_text(ev) -> str:
    lines = [
        f"Acute Liver Failure Decision Support: {ev.patient_id}",
        f"  Etiology:        {ev.etiology}",
        f"  Encephalopathy:  Grade {ev.encephalopathy.grade} ({ev.encephalopathy.stage_name})",
        f"  King's College:  Criteria met={ev.kings_college.criteria_met}",
        f"  KCC action:      {ev.kings_college.transplant_listing_urgency}",
        f"  ALFSG 21-day TFS:{ev.alfsg.transplant_free_survival_pct}%",
        f"  MELD / MELD-Na:  {ev.meld.meld_score} / {ev.meld.meld_na_score} (adjunct only)",
        f"  Ammonia:         {ev.ammonia_icp_risk['risk_tier']}",
    ]
    if ev.apap_assessment is not None:
        lines.extend(
            [
                f"  APAP nomogram:   {ev.apap_assessment.nomogram_risk}",
                f"  NAC indicated:   {ev.apap_assessment.nac_indicated}",
            ]
        )
    lines.append("  Actions:")
    lines.extend(f"    - {action}" for action in ev.urgent_actions)
    return "\n".join(lines)


def _load_batch(path: Path) -> Iterable[Dict[str, Any]]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("JSON batch input must be an array of objects")
        return data

    with path.open(mode="r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def run_interactive() -> int:
    print("Acute Liver Failure Decision Support")
    print("Prognostic aid only; transplant allocation requires separate policy assessment.")
    try:
        patient_id = input("Patient ID [PT-001]: ").strip() or "PT-001"
        etiology = input(
            "Etiology [acetaminophen / viral / dili / autoimmune / indeterminate]: "
        ).strip() or "acetaminophen"
        age = int(input("Age [35]: ").strip() or "35")
        he_grade = int(input("West Haven grade 0-4 [2]: ").strip() or "2")
        inr = float(input("INR [2.8]: ").strip() or "2.8")
        bili = float(input("Bilirubin mg/dL [6.5]: ").strip() or "6.5")
        cr = float(input("Creatinine mg/dL [1.8]: ").strip() or "1.8")
        ph = float(input("Arterial pH [7.34]: ").strip() or "7.34")
        lactate = float(input("Current lactate mmol/L [2.4]: ").strip() or "2.4")
        post_lactate_raw = input(
            "Post-resuscitation lactate mmol/L [blank if not known]: "
        ).strip()
        post_lactate = float(post_lactate_raw) if post_lactate_raw else None
        sodium = float(input("Sodium mEq/L [136]: ").strip() or "136")
        ammonia = float(input("Ammonia umol/L [110]: ").strip() or "110")
        vasopressor = _bool_value(input("Vasopressor use? [no]: ").strip() or "no")

        apap_level = None
        apap_hours = None
        if any(x in etiology.lower() for x in ("acetaminophen", "apap", "paracetamol")):
            raw = input("Acetaminophen concentration ug/mL [blank if unavailable]: ").strip()
            if raw:
                apap_level = float(raw)
                apap_hours = float(input("Hours since ingestion: ").strip())

        labs = LiverFailureLabs(
            inr=inr,
            bilirubin_mg_dl=bili,
            creatinine_mg_dl=cr,
            arterial_ph=ph,
            lactate_mmol_l=lactate,
            sodium_meq_l=sodium,
            ammonia_umol_l=ammonia,
        )
        ev = AcuteLiverFailureDecisionEngine().evaluate_patient(
            patient_id=patient_id,
            labs=labs,
            he_grade=he_grade,
            age=age,
            etiology=etiology,
            apap_serum_ug_ml=apap_level,
            apap_ingestion_hours=apap_hours,
            post_resuscitation_lactate=post_lactate,
            vasopressor_use=vasopressor,
        )
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return 0
    except ValueError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2

    print()
    print(_evaluation_text(ev))
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.json:
        args.format = "json"

    if args.interactive or (
        not args.evaluate and not args.batch and argv is None and len(sys.argv) == 1
    ):
        return run_interactive()

    engine = AcuteLiverFailureDecisionEngine()

    try:
        if args.batch:
            path = Path(args.batch)
            if not path.exists():
                print(f"Error: File not found: {path}", file=sys.stderr)
                return 1
            if not path.is_file():
                print(f"Error: Not a file: {path}", file=sys.stderr)
                return 1
            if path.suffix.lower() not in {".json", ".csv"}:
                print(
                    f"Error: Unsupported file format '{path.suffix}'. Use .csv or .json",
                    file=sys.stderr,
                )
                return 1

            records = _load_batch(path)
            evaluations = [_record_to_evaluation(engine, record) for record in records]
            if args.format == "json":
                text = json.dumps([asdict(ev) for ev in evaluations], indent=2)
            else:
                text = "\n\n".join(_evaluation_text(ev) for ev in evaluations)
            return _write_or_print(text, args.output)

        labs = LiverFailureLabs(
            inr=args.inr,
            bilirubin_mg_dl=args.bili,
            creatinine_mg_dl=args.cr,
            arterial_ph=args.ph,
            lactate_mmol_l=args.lactate,
            sodium_meq_l=args.sodium,
            ammonia_umol_l=args.ammonia,
            alt_u_l=args.alt,
            ast_u_l=args.ast,
            glucose_mg_dl=args.glucose,
            on_dialysis=args.dialysis,
        )
        ev = engine.evaluate_patient(
            patient_id=args.patient_id,
            labs=labs,
            he_grade=args.he_grade,
            age=args.age,
            etiology=args.etiology,
            jaundice_to_coma_days=args.jaundice_to_coma_days,
            apap_serum_ug_ml=args.apap_level,
            apap_ingestion_hours=args.apap_hours,
            post_resuscitation_lactate=args.post_resuscitation_lactate,
            vasopressor_use=args.vasopressor_use,
        )
    except (ValueError, OSError, json.JSONDecodeError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        text = json.dumps(asdict(ev), indent=2)
    else:
        text = _evaluation_text(ev)
    return _write_or_print(text, args.output)


if __name__ == "__main__":
    sys.exit(main())
