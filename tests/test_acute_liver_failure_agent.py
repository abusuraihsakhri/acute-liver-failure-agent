"""Regression and behavior tests for the acute liver failure decision engine."""

import io
import json
import math
import os
from pathlib import Path
import tempfile
import unittest

import cli
from liver_failure_prognostic import (
    ALFSGPrognosticIndex,
    AcetaminophenToxicityAssessor,
    AcuteLiverFailureDecisionEngine,
    HepaticEncephalopathyStager,
    KingsCollegeEvaluator,
    LiverFailureLabs,
    MELDCalculator,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestKingsCollegeCriteria(unittest.TestCase):
    def setUp(self):
        self.evaluator = KingsCollegeEvaluator()

    def test_apap_arterial_ph_acidosis(self):
        labs = LiverFailureLabs(arterial_ph=7.24, inr=2.5, creatinine_mg_dl=1.8)
        result = self.evaluator.evaluate_acetaminophen(labs, he_grade=2)
        self.assertTrue(result.criteria_met)
        self.assertNotIn("Status 1A /", result.transplant_listing_urgency)
        self.assertIn("transplant", result.transplant_listing_urgency.lower())

    def test_apap_post_resuscitation_lactate(self):
        labs = LiverFailureLabs(arterial_ph=7.34, lactate_mmol_l=2.0)
        result = self.evaluator.evaluate_acetaminophen(
            labs, he_grade=2, post_resuscitation_lactate=3.2
        )
        self.assertTrue(result.criteria_met)
        self.assertTrue(result.criteria_details["post_resuscitation_lactate_gt_3_0"])

    def test_admission_lactate_is_not_silently_treated_as_post_resuscitation(self):
        labs = LiverFailureLabs(
            arterial_ph=7.34,
            inr=3.0,
            creatinine_mg_dl=2.0,
            lactate_mmol_l=8.0,
        )
        result = self.evaluator.evaluate_acetaminophen(labs, he_grade=2)
        self.assertFalse(result.criteria_met)

    def test_apap_combined_triad_met(self):
        labs = LiverFailureLabs(
            arterial_ph=7.35, inr=7.2, creatinine_mg_dl=3.8, lactate_mmol_l=2.1
        )
        self.assertTrue(
            self.evaluator.evaluate_acetaminophen(labs, he_grade=3).criteria_met
        )

    def test_apap_subthreshold_not_met(self):
        labs = LiverFailureLabs(
            arterial_ph=7.36, inr=4.0, creatinine_mg_dl=2.5, lactate_mmol_l=2.0
        )
        self.assertFalse(
            self.evaluator.evaluate_acetaminophen(labs, he_grade=2).criteria_met
        )

    def test_non_apap_single_inr_gt_6_5(self):
        labs = LiverFailureLabs(inr=7.0, bilirubin_mg_dl=5.0)
        result = self.evaluator.evaluate_non_acetaminophen(
            labs, age=30, jaundice_to_coma_days=3
        )
        self.assertTrue(result.criteria_met)

    def test_non_apap_three_subcriteria_met(self):
        labs = LiverFailureLabs(inr=4.2, bilirubin_mg_dl=19.0)
        result = self.evaluator.evaluate_non_acetaminophen(
            labs, age=45, jaundice_to_coma_days=9, etiology="viral_hbv"
        )
        self.assertTrue(result.criteria_met)

    def test_autoimmune_not_misclassified_as_kcc_unfavorable_etiology(self):
        labs = LiverFailureLabs(inr=3.6, bilirubin_mg_dl=10.0)
        result = self.evaluator.evaluate_non_acetaminophen(
            labs, age=30, jaundice_to_coma_days=3, etiology="autoimmune"
        )
        self.assertFalse(result.criteria_details["unfavorable_etiology"])
        self.assertFalse(result.criteria_met)


class TestMELDCalculations(unittest.TestCase):
    def setUp(self):
        self.calc = MELDCalculator()

    def test_meld_baseline_normal(self):
        result = self.calc.calculate(
            LiverFailureLabs(inr=1.0, bilirubin_mg_dl=1.0, creatinine_mg_dl=1.0)
        )
        self.assertAlmostEqual(result.meld_score, 6.4, delta=0.5)

    def test_meld_na_hyponatremia_increase(self):
        normal = self.calc.calculate(
            LiverFailureLabs(
                inr=2.5, bilirubin_mg_dl=10.0, creatinine_mg_dl=2.0, sodium_meq_l=140.0
            )
        )
        low = self.calc.calculate(
            LiverFailureLabs(
                inr=2.5, bilirubin_mg_dl=10.0, creatinine_mg_dl=2.0, sodium_meq_l=125.0
            )
        )
        self.assertGreater(low.meld_na_score, normal.meld_na_score)

    def test_dialysis_sets_creatinine_to_four_for_legacy_meld(self):
        dialysis = self.calc.calculate(
            LiverFailureLabs(
                inr=2.0,
                bilirubin_mg_dl=5.0,
                creatinine_mg_dl=1.2,
                on_dialysis=True,
            )
        )
        no_dialysis = self.calc.calculate(
            LiverFailureLabs(inr=2.0, bilirubin_mg_dl=5.0, creatinine_mg_dl=1.2)
        )
        self.assertGreater(dialysis.meld_score, no_dialysis.meld_score)

    def test_meld_does_not_generate_status_1a_or_fake_mortality(self):
        result = self.calc.calculate(
            LiverFailureLabs(inr=15.0, bilirubin_mg_dl=45.0, creatinine_mg_dl=8.0)
        )
        self.assertEqual(result.meld_score, 40.0)
        self.assertIsNone(result.estimated_30_day_mortality_pct)
        self.assertNotIn("Status 1A /", result.unos_priority_tier)
        self.assertIn("not applicable", result.unos_priority_tier.lower())


class TestALFSGModel(unittest.TestCase):
    def setUp(self):
        self.model = ALFSGPrognosticIndex()

    def test_matches_published_equation_for_favorable_case(self):
        labs = LiverFailureLabs(inr=1.8, bilirubin_mg_dl=3.0)
        result = self.model.calculate(
            labs, age=28, he_grade=1, etiology="acetaminophen", vasopressor_use=False
        )
        expected_logit = (
            2.67
            + 1.56
            - 0.70 * math.log(3.0)
            - 1.35 * math.log(1.8)
        )
        expected = 100 / (1 + math.exp(-expected_logit))
        self.assertAlmostEqual(result.transplant_free_survival_pct, expected, delta=0.1)

    def test_vasopressor_use_lowers_predicted_tfs(self):
        labs = LiverFailureLabs(inr=1.8, bilirubin_mg_dl=3.0)
        no_pressor = self.model.calculate(
            labs, age=28, he_grade=1, etiology="acetaminophen", vasopressor_use=False
        )
        pressor = self.model.calculate(
            labs, age=28, he_grade=1, etiology="acetaminophen", vasopressor_use=True
        )
        self.assertLess(
            pressor.transplant_free_survival_pct,
            no_pressor.transplant_free_survival_pct,
        )

    def test_unfavorable_etiology_lowers_predicted_tfs(self):
        labs = LiverFailureLabs(inr=1.8, bilirubin_mg_dl=3.0)
        apap = self.model.calculate(labs, 28, 1, "acetaminophen")
        autoimmune = self.model.calculate(labs, 28, 1, "autoimmune")
        self.assertLess(
            autoimmune.transplant_free_survival_pct,
            apap.transplant_free_survival_pct,
        )

    def test_age_is_not_a_model_variable(self):
        labs = LiverFailureLabs(inr=2.1, bilirubin_mg_dl=6.0)
        young = self.model.calculate(labs, 20, 2, "dili")
        older = self.model.calculate(labs, 70, 2, "dili")
        self.assertEqual(
            young.transplant_free_survival_pct,
            older.transplant_free_survival_pct,
        )

    def test_deep_he_non_apap_has_low_predicted_tfs(self):
        labs = LiverFailureLabs(inr=4.8, bilirubin_mg_dl=18.0)
        result = self.model.calculate(labs, 55, 4, "autoimmune")
        self.assertLess(result.transplant_free_survival_pct, 20.0)
        self.assertIn("21-day", result.model_note)


class TestRumackMatthewNomogram(unittest.TestCase):
    def setUp(self):
        self.assessor = AcetaminophenToxicityAssessor()

    def test_revised_high_risk_line_starts_at_300_at_four_hours(self):
        result = self.assessor.assess(4.0, 310.0, alt_u_l=30.0, inr=1.0)
        self.assertTrue(result.nac_indicated)
        self.assertIn("high-risk", result.nomogram_risk.lower())

    def test_220_at_four_hours_is_treatment_not_high_risk_line(self):
        result = self.assessor.assess(4.0, 220.0)
        self.assertTrue(result.nac_indicated)
        self.assertEqual(result.nomogram_risk, "At/above 150-treatment line")

    def test_below_treatment_line_without_injury(self):
        result = self.assessor.assess(6.0, 30.0, alt_u_l=25.0, inr=1.0)
        self.assertFalse(result.nac_indicated)
        self.assertTrue(result.nomogram_applicable)

    def test_established_injury_is_not_overruled_by_below_line_value(self):
        result = self.assessor.assess(12.0, 10.0, alt_u_l=1500.0, inr=2.0)
        self.assertTrue(result.nac_indicated)

    def test_before_four_hours_nomogram_is_inapplicable(self):
        result = self.assessor.assess(2.0, 80.0)
        self.assertFalse(result.nomogram_applicable)
        self.assertIsNone(result.nac_indicated)

    def test_after_24_hours_nomogram_is_inapplicable(self):
        result = self.assessor.assess(30.0, 8.0)
        self.assertFalse(result.nomogram_applicable)
        self.assertIsNone(result.nac_indicated)

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            self.assessor.assess(-1.0, 80.0)


class TestEncephalopathyAndAmmonia(unittest.TestCase):
    def setUp(self):
        self.stager = HepaticEncephalopathyStager()
        self.engine = AcuteLiverFailureDecisionEngine()

    def test_grade_4_uses_qualitative_risk_not_unvalidated_percentage(self):
        stage = self.stager.stage(4)
        self.assertEqual(stage.grade, 4)
        self.assertNotIn("%", stage.cerebral_edema_risk)
        self.assertIn("ventilation", stage.airway_management.lower())

    def test_invalid_direct_stage_rejected(self):
        with self.assertRaises(ValueError):
            self.stager.stage(5)

    def test_high_ammonia_is_flagged_as_neurocritical_risk(self):
        evaluation = self.engine.evaluate_patient(
            "P_HIGH",
            LiverFailureLabs(ammonia_umol_l=175.0),
            he_grade=2,
        )
        self.assertTrue(
            evaluation.ammonia_icp_risk["hyperosmolar_therapy_consideration"]
        )

    def test_low_ammonia_low_grade_has_no_hyperosmolar_flag(self):
        evaluation = self.engine.evaluate_patient(
            "P_LOW",
            LiverFailureLabs(ammonia_umol_l=60.0),
            he_grade=1,
        )
        self.assertFalse(
            evaluation.ammonia_icp_risk["hyperosmolar_therapy_consideration"]
        )


class TestMasterDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AcuteLiverFailureDecisionEngine()

    def test_full_evaluation_apap_acidosis(self):
        labs = LiverFailureLabs(
            inr=5.5,
            bilirubin_mg_dl=7.0,
            creatinine_mg_dl=3.2,
            arterial_ph=7.21,
            ammonia_umol_l=180.0,
            glucose_mg_dl=55.0,
        )
        evaluation = self.engine.evaluate_patient(
            "PT-ACUTE-01",
            labs,
            he_grade=3,
            age=32,
            etiology="acetaminophen",
            apap_serum_ug_ml=160.0,
            apap_ingestion_hours=6.0,
            vasopressor_use=True,
        )
        self.assertTrue(evaluation.kings_college.criteria_met)
        joined = " ".join(evaluation.urgent_actions).lower()
        self.assertIn("transplant center", joined)
        self.assertIn("intubation", joined)
        self.assertIn("hypoglycemia", joined)
        self.assertIn("acetylcysteine", joined)
        self.assertNotIn("status 1a listing", joined)

    def test_partial_apap_nomogram_inputs_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate_patient(
                "P",
                LiverFailureLabs(),
                he_grade=1,
                apap_serum_ug_ml=100.0,
            )


class TestCLIExecution(unittest.TestCase):
    def _capture(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        old_stdout, old_stderr = os.sys.stdout, os.sys.stderr
        os.sys.stdout, os.sys.stderr = stdout, stderr
        try:
            code = cli.main(argv)
        finally:
            os.sys.stdout, os.sys.stderr = old_stdout, old_stderr
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_single_evaluation_json(self):
        code, output, _ = self._capture(
            [
                "--evaluate",
                "--patient-id",
                "PT-TEST-99",
                "--inr",
                "7.0",
                "--ph",
                "7.22",
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["patient_id"], "PT-TEST-99")
        self.assertTrue(data["kings_college"]["criteria_met"])
        self.assertIsNone(data["meld"]["estimated_30_day_mortality_pct"])

    def test_cli_accepts_explicit_post_resuscitation_lactate(self):
        code, output, _ = self._capture(
            [
                "--evaluate",
                "--ph",
                "7.35",
                "--inr",
                "2.0",
                "--cr",
                "1.0",
                "--he-grade",
                "1",
                "--post-resuscitation-lactate",
                "3.2",
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)["kings_college"]["criteria_met"])

    def test_cli_batch_json(self):
        records = [
            {"patient_id": "P1", "inr": 7.5, "ph": 7.20, "etiology": "acetaminophen"},
            {"patient_id": "P2", "inr": 1.5, "ph": 7.42, "etiology": "viral_hbv"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
            json.dump(records, handle)
            path = handle.name
        try:
            code, output, _ = self._capture(["--batch", path, "--json"])
            self.assertEqual(code, 0)
            data = json.loads(output)
            self.assertEqual(len(data), 2)
            self.assertTrue(data[0]["kings_college"]["criteria_met"])
            self.assertFalse(data[1]["kings_college"]["criteria_met"])
        finally:
            os.remove(path)

    def test_batch_false_string_is_not_truthy(self):
        records = [
            {
                "patient_id": "P",
                "inr": 2.0,
                "bili": 5.0,
                "cr": 1.2,
                "dialysis": "false",
            }
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
            json.dump(records, handle)
            path = handle.name
        try:
            code, output, _ = self._capture(["--batch", path, "--json"])
            self.assertEqual(code, 0)
            data = json.loads(output)[0]
            expected = MELDCalculator().calculate(
                LiverFailureLabs(inr=2.0, bilirubin_mg_dl=5.0, creatinine_mg_dl=1.2)
            )
            self.assertEqual(data["meld"]["meld_score"], expected.meld_score)
        finally:
            os.remove(path)

    def test_mismatched_apap_inputs_returns_error(self):
        code, _, error = self._capture(
            ["--evaluate", "--apap-level", "100", "--json"]
        )
        self.assertEqual(code, 2)
        self.assertIn("must be supplied together", error)


class TestInputValidation(unittest.TestCase):
    def test_negative_inr_rejected(self):
        with self.assertRaises(ValueError):
            LiverFailureLabs(inr=-1.0)

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            LiverFailureLabs(inr=float("nan"))

    def test_invalid_age_rejected(self):
        engine = AcuteLiverFailureDecisionEngine()
        with self.assertRaises(ValueError):
            engine.evaluate_patient("PT", LiverFailureLabs(), he_grade=2, age=150)

    def test_empty_etiology_rejected(self):
        engine = AcuteLiverFailureDecisionEngine()
        with self.assertRaises(ValueError):
            engine.evaluate_patient("PT", LiverFailureLabs(), he_grade=2, etiology="")


class TestCLIBatchFileValidation(unittest.TestCase):
    def test_batch_nonexistent_file(self):
        self.assertEqual(cli.main(["--batch", "nonexistent_file.csv"]), 1)

    def test_batch_unsupported_format(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as handle:
            handle.write("test")
            path = handle.name
        try:
            self.assertEqual(cli.main(["--batch", path]), 1)
        finally:
            os.remove(path)

    def test_batch_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
            handle.write("not valid json{{{")
            path = handle.name
        try:
            self.assertEqual(cli.main(["--batch", path]), 2)
        finally:
            os.remove(path)


class TestCLIOutputFile(unittest.TestCase):
    def test_cli_output_to_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as handle:
            path = handle.name
        try:
            code = cli.main(
                [
                    "--evaluate",
                    "--patient-id",
                    "PT-OUT-TEST",
                    "--ph",
                    "7.25",
                    "--json",
                    "--output",
                    path,
                ]
            )
            self.assertEqual(code, 0)
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(data["patient_id"], "PT-OUT-TEST")
        finally:
            os.remove(path)


class TestSampleAndPackageSurface(unittest.TestCase):
    def test_sample_csv_batch(self):
        stdout = io.StringIO()
        old_stdout = os.sys.stdout
        os.sys.stdout = stdout
        try:
            code = cli.main(["-i", str(PROJECT_ROOT / "sample.csv"), "--json"])
        finally:
            os.sys.stdout = old_stdout
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(stdout.getvalue())), 3)

    def test_package_exports_engine(self):
        import acute_liver_failure_agent as package

        self.assertTrue(hasattr(package, "AcuteLiverFailureDecisionEngine"))


if __name__ == "__main__":
    unittest.main()
