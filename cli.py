#!/usr/bin/env python3
"""
Command Line Interface for Acute Liver Failure Prognostication & Transplant Decision Support.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

from liver_failure_prognostic import (
    LiverFailureLabs,
    AcuteLiverFailureDecisionEngine,
    KingsCollegeEvaluator,
    MELDCalculator,
    ALFSGPrognosticIndex,
    AcetaminophenToxicityAssessor,
    HepaticEncephalopathyStager,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alf-agent",
        description="Acute Liver Failure Critical Care & Transplant Decision Support Agent",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--interactive", "-I", action="store_true", help="Launch interactive clinical evaluation wizard.")
    mode.add_argument("--evaluate", action="store_true", help="Evaluate single patient with CLI parameters.")
    mode.add_argument("--batch", "-i", metavar="FILE", help="Batch evaluate patients from CSV or JSON file.")

    # Patient & Clinical parameters
    parser.add_argument("--patient-id", default="PT-001", help="Patient identifier (default: PT-001).")
    parser.add_argument("--etiology", default="acetaminophen", help="ALF etiology (acetaminophen, non-a-non-b, dili, viral, autoimmune, etc.).")
    parser.add_argument("--age", type=int, default=35, help="Patient age in years (default: 35).")
    parser.add_argument("--he-grade", type=int, default=2, choices=[0, 1, 2, 3, 4], help="West Haven hepatic encephalopathy grade (0-4).")
    parser.add_argument("--jaundice-to-coma-days", type=int, default=4, help="Interval in days between jaundice onset and encephalopathy.")

    # Laboratory parameters
    parser.add_argument("--inr", type=float, default=2.8, help="International Normalized Ratio (INR).")
    parser.add_argument("--bili", type=float, default=6.5, help="Total serum bilirubin (mg/dL).")
    parser.add_argument("--cr", type=float, default=1.8, help="Serum creatinine (mg/dL).")
    parser.add_argument("--ph", type=float, default=7.34, help="Arterial blood pH.")
    parser.add_argument("--lactate", type=float, default=2.4, help="Arterial blood lactate (mmol/L).")
    parser.add_argument("--sodium", type=float, default=136.0, help="Serum sodium (mEq/L).")
    parser.add_argument("--ammonia", type=float, default=110.0, help="Arterial ammonia (umol/L).")
    parser.add_argument("--alt", type=float, default=3500.0, help="Serum ALT (U/L).")
    parser.add_argument("--ast", type=float, default=4200.0, help="Serum AST (U/L).")
    parser.add_argument("--glucose", type=float, default=85.0, help="Serum glucose (mg/dL).")
    parser.add_argument("--dialysis", action="store_true", help="Patient is currently on renal replacement therapy.")

    # APAP Specific
    parser.add_argument("--apap-level", type=float, default=None, help="Serum acetaminophen level in ug/mL.")
    parser.add_argument("--apap-hours", type=float, default=None, help="Time since acute APAP ingestion in hours.")

    # Output formatting
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text).")
    parser.add_argument("--json", action="store_true", help="Output result as formatted JSON (shorthand for --format json).")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write results to file.")

    return parser


def run_interactive():
    print("=" * 75)
    print("  ACUTE LIVER FAILURE (ALF) CLINICAL DECISION SUPPORT WIZARD")
    print("=" * 75)
    try:
        patient_id = input("Patient ID [PT-001]: ").strip() or "PT-001"
        etiology = input("Etiology [acetaminophen / viral / dili / autoimmune / indeterminate]: ").strip() or "acetaminophen"
        if not etiology:
            raise ValueError("Etiology cannot be empty")
        age_str = input("Age in years [35]: ").strip() or "35"
        age = int(age_str)
        he_str = input("Hepatic Encephalopathy Grade (0=None, 1=Mild, 2=Asterixis, 3=Stupor, 4=Coma) [2]: ").strip() or "2"
        he_grade = int(he_str)
        if not (0 <= he_grade <= 4):
            raise ValueError("Hepatic Encephalopathy Grade must be between 0 and 4")

        print("\nEnter Lab Values:")
        inr = float(input("  INR [2.8]: ").strip() or "2.8")
        bili = float(input("  Total Bilirubin (mg/dL) [6.5]: ").strip() or "6.5")
        cr = float(input("  Creatinine (mg/dL) [1.8]: ").strip() or "1.8")
        ph = float(input("  Arterial pH [7.34]: ").strip() or "7.34")
        lactate = float(input("  Arterial Lactate (mmol/L) [2.4]: ").strip() or "2.4")
        sodium = float(input("  Sodium (mEq/L) [136.0]: ").strip() or "136.0")
        ammonia = float(input("  Ammonia (umol/L) [110.0]: ").strip() or "110.0")

        apap_level = None
        apap_hours = None
        if "acetaminophen" in etiology.lower() or "apap" in etiology.lower() or "paracetamol" in etiology.lower():
            apap_str = input("  Serum Acetaminophen (ug/mL, optional): ").strip()
            if apap_str:
                apap_level = float(apap_str)
                apap_hours = float(input("  Hours Post-Ingestion [8.0]: ").strip() or "8.0")

    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)
    except ValueError as e:
        print(f"\nInvalid input: {e}")
        sys.exit(1)

    labs = LiverFailureLabs(
        inr=inr, bilirubin_mg_dl=bili, creatinine_mg_dl=cr,
        arterial_ph=ph, lactate_mmol_l=lactate, sodium_meq_l=sodium,
        ammonia_umol_l=ammonia
    )

    engine = AcuteLiverFailureDecisionEngine()
    eval_res = engine.evaluate_patient(
        patient_id=patient_id,
        labs=labs,
        he_grade=he_grade,
        age=age,
        etiology=etiology,
        apap_serum_ug_ml=apap_level,
        apap_ingestion_hours=apap_hours,
    )

    print("\n" + "=" * 75)
    print(f"  CLINICAL PROGNOSTICATION SUMMARY: {patient_id} ({etiology.upper()})")
    print("=" * 75)
    print(f"Encephalopathy:    Grade {eval_res.encephalopathy.grade} - {eval_res.encephalopathy.stage_name}")
    print(f"  Cerebral Edema:  {eval_res.encephalopathy.cerebral_edema_risk}")
    print(f"  Airway Rec:      {eval_res.encephalopathy.airway_management}")
    print("-" * 75)
    print(f"King's College:    Criteria Met: {eval_res.kings_college.criteria_met}")
    print(f"  Urgency:         {eval_res.kings_college.transplant_listing_urgency}")
    print(f"  Rationale:       {eval_res.kings_college.rationale}")
    print("-" * 75)
    print(f"MELD Score:        {eval_res.meld.meld_score} | MELD-Na: {eval_res.meld.meld_na_score}")
    print(f"  30-Day Mortality:{eval_res.meld.estimated_30_day_mortality_pct}% | Tier: {eval_res.meld.unos_priority_tier}")
    print("-" * 75)
    print(f"ALFSG Model:       Transplant-Free Survival: {eval_res.alfsg.transplant_free_survival_pct}%")
    print(f"  Prognostic Tier: {eval_res.alfsg.prognostic_tier}")
    print(f"  Recommendation:  {eval_res.alfsg.recommendation}")
    if eval_res.apap_assessment:
        print("-" * 75)
        print(f"Rumack-Matthew:    {eval_res.apap_assessment.nomogram_risk}")
        print(f"  NAC Protocol:    {'INDICATED' if eval_res.apap_assessment.nac_indicated else 'Not Indicated'}")
        print(f"  Regimen:         {eval_res.apap_assessment.nac_regimen}")
    print("-" * 75)
    print("URGENT CLINICAL ACTIONS:")
    for act in eval_res.urgent_actions:
        print(f"  [!] {act}")
    print("=" * 75)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.json:
        args.format = "json"

    if args.interactive or (not args.evaluate and not args.batch and len(sys.argv) == 1):
        run_interactive()
        return 0

    engine = AcuteLiverFailureDecisionEngine()

    if args.batch:
        path = Path(args.batch)
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            return 1
        if not path.is_file():
            print(f"Error: Not a file: {path}", file=sys.stderr)
            return 1
        if path.suffix.lower() not in (".json", ".csv"):
            print(f"Error: Unsupported file format '{path.suffix}'. Use .csv or .json", file=sys.stderr)
            return 1
        evaluations = []
        if path.suffix.lower() == ".json":
            try:
                records = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"Error reading JSON file: {e}", file=sys.stderr)
                return 1
            for r in records:
                labs = LiverFailureLabs(
                    inr=float(r.get("inr", 1.0)),
                    bilirubin_mg_dl=float(r.get("bili", r.get("bilirubin", 1.0))),
                    creatinine_mg_dl=float(r.get("cr", r.get("creatinine", 1.0))),
                    arterial_ph=float(r.get("ph", 7.4)),
                    lactate_mmol_l=float(r.get("lactate", 1.0)),
                    sodium_meq_l=float(r.get("sodium", 140.0)),
                    ammonia_umol_l=float(r.get("ammonia", 40.0)),
                    alt_u_l=float(r.get("alt", 30.0)),
                    ast_u_l=float(r.get("ast", 30.0)),
                    on_dialysis=bool(r.get("dialysis", False)),
                )
                ev = engine.evaluate_patient(
                    patient_id=str(r.get("patient_id", "PT")),
                    labs=labs,
                    he_grade=int(r.get("he_grade", 0)),
                    age=int(r.get("age", 40)),
                    etiology=str(r.get("etiology", "acetaminophen")),
                )
                evaluations.append(ev)
        else:
            with open(path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    labs = LiverFailureLabs(
                        inr=float(r.get("inr", 1.0)),
                        bilirubin_mg_dl=float(r.get("bili", r.get("bilirubin", 1.0))),
                        creatinine_mg_dl=float(r.get("cr", r.get("creatinine", 1.0))),
                        arterial_ph=float(r.get("ph", 7.4)),
                        lactate_mmol_l=float(r.get("lactate", 1.0)),
                        sodium_meq_l=float(r.get("sodium", 140.0)),
                        ammonia_umol_l=float(r.get("ammonia", 40.0)),
                    )
                    ev = engine.evaluate_patient(
                        patient_id=str(r.get("patient_id", "PT")),
                        labs=labs,
                        he_grade=int(r.get("he_grade", 0)),
                        age=int(r.get("age", 40)),
                        etiology=str(r.get("etiology", "acetaminophen")),
                    )
                    evaluations.append(ev)

        if args.format == "json":
            out_str = json.dumps([e.__dict__ for e in evaluations], default=lambda o: o.__dict__, indent=2)
        else:
            out_lines = []
            for ev in evaluations:
                out_lines.append(
                    f"Patient {ev.patient_id} ({ev.etiology}): King's Met={ev.kings_college.criteria_met} | "
                    f"MELD={ev.meld.meld_score} | ALFSG TFS={ev.alfsg.transplant_free_survival_pct}% | "
                    f"Urgency={ev.kings_college.transplant_listing_urgency}"
                )
            out_str = "\n".join(out_lines)

        if args.output:
            try:
                Path(args.output).write_text(out_str, encoding="utf-8")
            except OSError as e:
                print(f"Error writing output file: {e}", file=sys.stderr)
                return 1
        else:
            print(out_str)
        return 0

    # Single patient evaluation mode
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
    )

    if args.format == "json":
        out_str = json.dumps(ev.__dict__, default=lambda o: o.__dict__, indent=2)
    else:
        out_str = (
            f"Acute Liver Failure Clinical Dossier for {ev.patient_id}:\n"
            f"  Etiology:          {ev.etiology.upper()}\n"
            f"  Encephalopathy:    Grade {ev.encephalopathy.grade} ({ev.encephalopathy.stage_name})\n"
            f"  King's College:    Criteria Met={ev.kings_college.criteria_met} -> [{ev.kings_college.transplant_listing_urgency}]\n"
            f"  MELD / MELD-Na:    {ev.meld.meld_score} / {ev.meld.meld_na_score} (30-day mortality: {ev.meld.estimated_30_day_mortality_pct}%)\n"
            f"  ALFSG TFS Score:   {ev.alfsg.transplant_free_survival_pct}% Transplant-Free Survival\n"
            f"  Ammonia/ICP Risk:  {ev.ammonia_icp_risk['risk_tier']}\n"
            f"  Urgent Actions:    {len(ev.urgent_actions)} triggered\n"
        )
        for act in ev.urgent_actions:
            out_str += f"    * {act}\n"

    if args.output:
        try:
            Path(args.output).write_text(out_str, encoding="utf-8")
        except OSError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            return 1
    else:
        print(out_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
