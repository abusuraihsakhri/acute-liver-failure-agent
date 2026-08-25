"""
Comprehensive Unit Test Suite for Acute Liver Failure (ALF) Critical Care Decision Engine.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from liver_failure_prognostic import (
    LiverFailureLabs,
    KingsCollegeEvaluator,
    MELDCalculator,
    ALFSGPrognosticIndex,
    AcetaminophenToxicityAssessor,
    HepaticEncephalopathyStager,
    AcuteLiverFailureDecisionEngine,
)
import cli


class TestKingsCollegeCriteria(unittest.TestCase):
    def setUp(self):
        self.evaluator = KingsCollegeEvaluator()

    def test_apap_arterial_ph_acidosis(self):
        labs = LiverFailureLabs(arterial_ph=7.24, inr=2.5, creatinine_mg_dl=1.8)
        res = self.evaluator.evaluate_acetaminophen(labs, he_grade=2)
        self.assertTrue(res.criteria_met)
        self.assertIn("Status 1A", res.transplant_listing_urgency)

    def test_apap_post_resuscitation_lactate(self):
        labs = LiverFailureLabs(arterial_ph=7.34, inr=3.0, creatinine_mg_dl=2.0, lactate_mmol_l=4.2)
        res = self.evaluator.evaluate_acetaminophen(labs, he_grade=2)
        self.assertTrue(res.criteria_met)

    def test_apap_combined_triad_met(self):
        labs = LiverFailureLabs(arterial_ph=7.35, inr=7.2, creatinine_mg_dl=3.8, lactate_mmol_l=2.1)
        res = self.evaluator.evaluate_acetaminophen(labs, he_grade=3)
        self.assertTrue(res.criteria_met)

    def test_apap_subthreshold_not_met(self):
        labs = LiverFailureLabs(arterial_ph=7.36, inr=4.0, creatinine_mg_dl=2.5, lactate_mmol_l=2.0)
        res = self.evaluator.evaluate_acetaminophen(labs, he_grade=2)
        self.assertFalse(res.criteria_met)

    def test_non_apap_single_inr_gt_6_5(self):
        labs = LiverFailureLabs(inr=7.0, bilirubin_mg_dl=5.0)
        res = self.evaluator.evaluate_non_acetaminophen(labs, age=30, jaundice_to_coma_days=3)
        self.assertTrue(res.criteria_met)

    def test_non_apap_three_subcriteria_met(self):
        # Age > 40 (1), Bili > 17.5 (2), INR > 3.5 (3)
        labs = LiverFailureLabs(inr=4.2, bilirubin_mg_dl=19.0)
        res = self.evaluator.evaluate_non_acetaminophen(labs, age=45, jaundice_to_coma_days=4)
        self.assertTrue(res.criteria_met)

    def test_non_apap_two_subcriteria_not_met(self):
        # Age > 40 (1), Jaundice > 7d (2), but INR < 3.5 and Bili < 17.5
        labs = LiverFailureLabs(inr=2.2, bilirubin_mg_dl=8.0)
        res = self.evaluator.evaluate_non_acetaminophen(labs, age=52, jaundice_to_coma_days=10, etiology="viral")
        self.assertFalse(res.criteria_met)


class TestMELDCalculations(unittest.TestCase):
    def setUp(self):
        self.calc = MELDCalculator()

    def test_meld_baseline_normal(self):
        labs = LiverFailureLabs(inr=1.0, bilirubin_mg_dl=1.0, creatinine_mg_dl=1.0)
        res = self.calc.calculate(labs)
        self.assertAlmostEqual(res.meld_score, 6.4, delta=0.5)
        self.assertEqual(res.unos_priority_tier, "Tier 4 (Low 30-day risk)")

    def test_meld_severe_injury(self):
        labs = LiverFailureLabs(inr=4.5, bilirubin_mg_dl=20.0, creatinine_mg_dl=3.5)
        res = self.calc.calculate(labs)
        self.assertGreater(res.meld_score, 35.0)
        self.assertGreater(res.estimated_30_day_mortality_pct, 70.0)

    def test_meld_na_hyponatremia_increase(self):
        labs_norm_na = LiverFailureLabs(inr=2.5, bilirubin_mg_dl=10.0, creatinine_mg_dl=2.0, sodium_meq_l=140.0)
        labs_low_na = LiverFailureLabs(inr=2.5, bilirubin_mg_dl=10.0, creatinine_mg_dl=2.0, sodium_meq_l=125.0)
        res_norm = self.calc.calculate(labs_norm_na)
        res_low = self.calc.calculate(labs_low_na)
        self.assertGreater(res_low.meld_na_score, res_norm.meld_na_score)

    def test_meld_dialysis_sets_cr_4(self):
        labs_dialysis = LiverFailureLabs(inr=2.0, bilirubin_mg_dl=5.0, creatinine_mg_dl=1.2, on_dialysis=True)
        res = self.calc.calculate(labs_dialysis)
        labs_no_dialysis = LiverFailureLabs(inr=2.0, bilirubin_mg_dl=5.0, creatinine_mg_dl=1.2, on_dialysis=False)
        res_no_dialysis = self.calc.calculate(labs_no_dialysis)
        self.assertGreater(res.meld_score, res_no_dialysis.meld_score)


class TestALFSGModel(unittest.TestCase):
    def setUp(self):
        self.model = ALFSGPrognosticIndex()

    def test_favorable_mild_apap(self):
        labs = LiverFailureLabs(inr=1.8, bilirubin_mg_dl=3.0, creatinine_mg_dl=1.1)
        res = self.model.calculate(labs, age=28, he_grade=1, etiology="acetaminophen")
        self.assertGreaterEqual(res.transplant_free_survival_pct, 75.0)

    def test_critical_coma_non_apap(self):
        labs = LiverFailureLabs(inr=4.8, bilirubin_mg_dl=18.0, creatinine_mg_dl=2.6)
        res = self.model.calculate(labs, age=55, he_grade=4, etiology="autoimmune")
        self.assertLessEqual(res.transplant_free_survival_pct, 25.0)
        self.assertIn("urgent", res.recommendation.lower())


class TestRumackMatthewNomogram(unittest.TestCase):
    def setUp(self):
        self.assessor = AcetaminophenToxicityAssessor()

    def test_high_risk_above_treatment_line(self):
        res = self.assessor.assess(time_since_ingestion_hours=4.0, serum_apap_ug_ml=220.0, alt_u_l=450.0, inr=1.8)
        self.assertTrue(res.nac_indicated)
        self.assertIn("Above", res.nomogram_risk)
        self.assertIn("21-Hour IV", res.nac_regimen)

    def test_below_treatment_line_safe(self):
        res = self.assessor.assess(time_since_ingestion_hours=6.0, serum_apap_ug_ml=30.0, alt_u_l=25.0, inr=1.0)
        self.assertFalse(res.nac_indicated)
        self.assertIn("Below", res.nomogram_risk)

    def test_fulminant_hepatic_injury_severity(self):
        res = self.assessor.assess(time_since_ingestion_hours=12.0, serum_apap_ug_ml=80.0, alt_u_l=12000.0, inr=4.5)
        self.assertEqual(res.clinical_severity, "Fulminant Acute Liver Injury")


class TestEncephalopathyAndAmmonia(unittest.TestCase):
    def setUp(self):
        self.stager = HepaticEncephalopathyStager()

    def test_grade_4_intubation_mandatory(self):
        stage = self.stager.stage(4)
        self.assertEqual(stage.grade, 4)
        self.assertIn("Mandatory", stage.airway_management)
        self.assertIn("65-80%", stage.cerebral_edema_risk)

    def test_grade_1_mild_features(self):
        stage = self.stager.stage(1)
        self.assertEqual(stage.grade, 1)
        self.assertIn("Grade I", stage.stage_name)

    def test_grade_0_and_grade_2_staging(self):
        s0 = self.stager.stage(0)
        self.assertEqual(s0.grade, 0)
        self.assertIn("Subclinical", s0.stage_name)
        s2 = self.stager.stage(2)
        self.assertEqual(s2.grade, 2)
        self.assertIn("Grade II", s2.stage_name)


class TestMasterDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AcuteLiverFailureDecisionEngine()

    def test_full_evaluation_apap_acidosis(self):
        labs = LiverFailureLabs(
            inr=5.5,
            bilirubin_mg_dl=7.0,
            creatinine_mg_dl=3.2,
            arterial_ph=7.21,
            lactate_mmol_l=4.5,
            ammonia_umol_l=180.0,
            glucose_mg_dl=55.0,
        )
        eval_res = self.engine.evaluate_patient(
            patient_id="PT-ACUTE-01",
            labs=labs,
            he_grade=3,
            age=32,
            etiology="acetaminophen",
            apap_serum_ug_ml=160.0,
            apap_ingestion_hours=6.0,
        )
        self.assertTrue(eval_res.kings_college.criteria_met)
        self.assertTrue(any("transplant center" in a.lower() for a in eval_res.urgent_actions))
        self.assertTrue(any("intubation" in a.lower() for a in eval_res.urgent_actions))
        self.assertTrue(any("dextrose" in a.lower() for a in eval_res.urgent_actions))
        self.assertTrue(eval_res.ammonia_icp_risk["hyperosmolar_therapy_indicated"])


class TestCLIExecution(unittest.TestCase):
    def test_cli_single_evaluation_json(self):
        out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = out
        try:
            code = cli.main([
                "--evaluate",
                "--patient-id", "PT-TEST-99",
                "--inr", "7.0",
                "--ph", "7.22",
                "--format", "json"
            ])
            self.assertEqual(code, 0)
        finally:
            sys.stdout = old_stdout

        data = json.loads(out.getvalue())
        self.assertEqual(data["patient_id"], "PT-TEST-99")
        self.assertTrue(data["kings_college"]["criteria_met"])

    def test_cli_batch_json(self):
        records = [
            {"patient_id": "P1", "inr": 7.5, "ph": 7.20, "etiology": "acetaminophen"},
            {"patient_id": "P2", "inr": 1.5, "ph": 7.42, "etiology": "viral"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(records, f)
            temp_path = f.name

        try:
            out = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = out
            try:
                code = cli.main(["--batch", temp_path, "--format", "json"])
                self.assertEqual(code, 0)
            finally:
                sys.stdout = old_stdout

            data = json.loads(out.getvalue())
            self.assertEqual(len(data), 2)
            self.assertTrue(data[0]["kings_college"]["criteria_met"])
            self.assertFalse(data[1]["kings_college"]["criteria_met"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestAmmoniaAndExtendedCalculations(unittest.TestCase):
    def setUp(self):
        self.engine = AcuteLiverFailureDecisionEngine()
        self.calc = MELDCalculator()
        self.assessor = AcetaminophenToxicityAssessor()

    def test_ammonia_risk_tiers(self):
        # High ammonia (>150)
        labs_high = LiverFailureLabs(ammonia_umol_l=175.0)
        ev_high = self.engine.evaluate_patient("P_HIGH", labs_high, he_grade=2)
        self.assertTrue(ev_high.ammonia_icp_risk["hyperosmolar_therapy_indicated"])

        # Normal ammonia (<100)
        labs_norm = LiverFailureLabs(ammonia_umol_l=60.0)
        ev_norm = self.engine.evaluate_patient("P_NORM", labs_norm, he_grade=1)
        self.assertFalse(ev_norm.ammonia_icp_risk["hyperosmolar_therapy_indicated"])

    def test_meld_upper_clamp_40(self):
        labs_extreme = LiverFailureLabs(inr=15.0, bilirubin_mg_dl=45.0, creatinine_mg_dl=8.0)
        res = self.calc.calculate(labs_extreme)
        self.assertEqual(res.meld_score, 40.0)
        self.assertEqual(res.meld_na_score, 40.0)

    def test_apap_decay_half_life_calculation(self):
        # 150 line at 4h is 150 ug/mL, at 8h is 75 ug/mL, at 12h is 37.5 ug/mL
        res_8h_high = self.assessor.assess(time_since_ingestion_hours=8.0, serum_apap_ug_ml=85.0)
        self.assertTrue(res_8h_high.nac_indicated)
        res_8h_low = self.assessor.assess(time_since_ingestion_hours=8.0, serum_apap_ug_ml=60.0)
        self.assertFalse(res_8h_low.nac_indicated)

    def test_cli_batch_csv(self):
        csv_content = (
            "patient_id,inr,bili,cr,ph,lactate,sodium,ammonia,he_grade,age,etiology\n"
            "PT_CSV_1,7.2,4.0,3.8,7.22,4.8,135,180,3,30,acetaminophen\n"
            "PT_CSV_2,1.4,1.2,0.9,7.40,1.0,140,45,0,25,acetaminophen\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            out = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = out
            try:
                code = cli.main(["--batch", temp_path, "--format", "json"])
                self.assertEqual(code, 0)
            finally:
                sys.stdout = old_stdout

            data = json.loads(out.getvalue())
            self.assertEqual(len(data), 2)
            self.assertTrue(data[0]["kings_college"]["criteria_met"])
            self.assertFalse(data[1]["kings_college"]["criteria_met"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()

