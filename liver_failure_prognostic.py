#!/usr/bin/env python3
"""
Acute Liver Failure (ALF) Critical Care Decision Support & Prognostication System.

Clinical Models Implemented:
1. King's College Hospital Criteria (Acetaminophen & Non-Acetaminophen Pathways).
2. UNOS MELD & MELD-Na / MELD 3.0 Organ Allocation Scoring.
3. Acute Liver Failure Study Group (ALFSG) Prognostic Index (Transplant-Free Survival).
4. West Haven Staging of Hepatic Encephalopathy (Grades 0 to IV).
5. Rumack-Matthew Nomogram for Acetaminophen Toxicity & IV N-Acetylcysteine (NAC) Protocol.
6. Hyperammonemia & Intracranial Hypertension / Cerebral Edema Risk Stratification.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
import math


@dataclass
class LiverFailureLabs:
    inr: float = 1.0
    bilirubin_mg_dl: float = 1.0
    creatinine_mg_dl: float = 1.0
    arterial_ph: float = 7.40
    lactate_mmol_l: float = 1.0
    sodium_meq_l: float = 140.0
    ammonia_umol_l: float = 40.0
    ast_u_l: float = 30.0
    alt_u_l: float = 30.0
    platelets_k_ul: float = 250.0
    glucose_mg_dl: float = 95.0
    on_dialysis: bool = False

    def __post_init__(self):
        """Validate laboratory values are within physiologically plausible ranges."""
        if not (0.1 <= self.inr <= 50.0):
            raise ValueError(f"INR must be between 0.1 and 50.0, got {self.inr}")
        if not (0.0 <= self.bilirubin_mg_dl <= 100.0):
            raise ValueError(f"Bilirubin must be between 0.0 and 100.0 mg/dL, got {self.bilirubin_mg_dl}")
        if not (0.0 <= self.creatinine_mg_dl <= 30.0):
            raise ValueError(f"Creatinine must be between 0.0 and 30.0 mg/dL, got {self.creatinine_mg_dl}")
        if not (6.5 <= self.arterial_ph <= 7.8):
            raise ValueError(f"Arterial pH must be between 6.5 and 7.8, got {self.arterial_ph}")
        if not (0.0 <= self.lactate_mmol_l <= 30.0):
            raise ValueError(f"Lactate must be between 0.0 and 30.0 mmol/L, got {self.lactate_mmol_l}")
        if not (100.0 <= self.sodium_meq_l <= 180.0):
            raise ValueError(f"Sodium must be between 100.0 and 180.0 mEq/L, got {self.sodium_meq_l}")
        if not (0.0 <= self.ammonia_umol_l <= 500.0):
            raise ValueError(f"Ammonia must be between 0.0 and 500.0 umol/L, got {self.ammonia_umol_l}")
        if not (0.0 <= self.ast_u_l <= 50000.0):
            raise ValueError(f"AST must be between 0.0 and 50000.0 U/L, got {self.ast_u_l}")
        if not (0.0 <= self.alt_u_l <= 50000.0):
            raise ValueError(f"ALT must be between 0.0 and 50000.0 U/L, got {self.alt_u_l}")
        if not (0.0 <= self.platelets_k_ul <= 1500.0):
            raise ValueError(f"Platelets must be between 0.0 and 1500.0 K/uL, got {self.platelets_k_ul}")
        if not (0.0 <= self.glucose_mg_dl <= 1200.0):
            raise ValueError(f"Glucose must be between 0.0 and 1200.0 mg/dL, got {self.glucose_mg_dl}")


@dataclass
class KingsCollegeResult:
    criteria_met: bool
    pathway: str  # "acetaminophen" or "non_acetaminophen"
    transplant_listing_urgency: str  # "UNOS Status 1A / Emergency Super-Urgent Listing" or "Continue Medical Optimization"
    criteria_details: Dict[str, bool]
    rationale: str


@dataclass
class MELDResult:
    meld_score: float
    meld_na_score: float
    estimated_30_day_mortality_pct: float
    unos_priority_tier: str


@dataclass
class ALFSGResult:
    transplant_free_survival_pct: float
    mortality_or_transplant_risk_pct: float
    prognostic_tier: str  # "High Survival", "Intermediate", "Critical - Urgent Transplant"
    recommendation: str


@dataclass
class APAPToxicityResult:
    ingestion_time_hours: float
    serum_apap_ug_ml: float
    nomogram_risk: str  # "Above 150 line (Probable Toxicity)", "Treatment Line (Possible)", "Below Line (Low Risk)"
    nac_indicated: bool
    nac_regimen: str
    clinical_severity: str


@dataclass
class HepaticEncephalopathyStaging:
    grade: int  # 0 to 4
    stage_name: str
    clinical_features: str
    cerebral_edema_risk: str
    airway_management: str


@dataclass
class ComprehensiveALFEvaluation:
    patient_id: str
    etiology: str
    encephalopathy: HepaticEncephalopathyStaging
    kings_college: KingsCollegeResult
    meld: MELDResult
    alfsg: ALFSGResult
    apap_assessment: Optional[APAPToxicityResult]
    ammonia_icp_risk: Dict[str, Any]
    urgent_actions: List[str]


class KingsCollegeEvaluator:
    """
    King's College Hospital Criteria for Liver Transplantation in Acute Liver Failure.
    O'Grady JG et al. Gastroenterology. 1989;97(2):439-445.
    """

    def evaluate_acetaminophen(
        self,
        labs: LiverFailureLabs,
        he_grade: int,
        post_resuscitation_lactate: Optional[float] = None
    ) -> KingsCollegeResult:
        lactate_val = post_resuscitation_lactate if post_resuscitation_lactate is not None else labs.lactate_mmol_l
        details = {
            "arterial_ph_lt_7_30": labs.arterial_ph < 7.30,
            "post_resuscitation_lactate_gt_3_5": lactate_val > 3.5,
            "combined_inr_cr_he": (
                labs.inr > 6.5 and
                labs.creatinine_mg_dl > 3.4 and
                he_grade >= 3
            ),
            "inr_gt_6_5": labs.inr > 6.5,
            "creatinine_gt_3_4": labs.creatinine_mg_dl > 3.4,
            "grade_3_4_encephalopathy": he_grade >= 3,
        }

        # Single criterion: pH < 7.30 OR Lactate > 3.5 OR (INR > 6.5 + Cr > 3.4 + Grade 3/4 HE)
        criteria_met = (
            details["arterial_ph_lt_7_30"] or
            details["post_resuscitation_lactate_gt_3_5"] or
            details["combined_inr_cr_he"]
        )

        if criteria_met:
            urgency = "UNOS Status 1A / Emergency Super-Urgent Listing"
            rationale = "Patient meets King's College acetaminophen criteria for emergency liver transplant."
        else:
            urgency = "Medical Management & Dynamic Intensive Care Monitoring"
            rationale = "Does not currently meet transplant criteria; maintain full medical therapy & serial labs."

        return KingsCollegeResult(
            criteria_met=criteria_met,
            pathway="acetaminophen",
            transplant_listing_urgency=urgency,
            criteria_details=details,
            rationale=rationale,
        )

    def evaluate_non_acetaminophen(
        self,
        labs: LiverFailureLabs,
        age: int,
        jaundice_to_coma_days: int,
        etiology: str = "indeterminate"
    ) -> KingsCollegeResult:
        unfavorable_etiology = any(
            et in etiology.lower()
            for et in ["non-a", "non-b", "seronegative", "drug", "dili", "halothane", "wilson", "autoimmune"]
        )

        sub_criteria = {
            "age_lt_10_or_gt_40": (age < 10 or age > 40),
            "unfavorable_etiology": unfavorable_etiology,
            "jaundice_to_encephalopathy_gt_7d": jaundice_to_coma_days > 7,
            "inr_gt_3_5": labs.inr > 3.5,
            "bilirubin_gt_17_5": labs.bilirubin_mg_dl > 17.5,
        }

        met_sub_criteria_count = sum(1 for v in sub_criteria.values() if v)
        single_major_criterion = labs.inr > 6.5

        criteria_met = single_major_criterion or (met_sub_criteria_count >= 3)

        details = {
            "inr_gt_6_5_standalone": single_major_criterion,
            "three_or_more_subcriteria": met_sub_criteria_count >= 3,
            **sub_criteria,
        }

        if criteria_met:
            urgency = "UNOS Status 1A / Emergency Super-Urgent Listing"
            rationale = (
                f"Meets King's College non-acetaminophen criteria "
                f"(INR > 6.5: {single_major_criterion}, Subcriteria met: {met_sub_criteria_count}/5)."
            )
        else:
            urgency = "Medical Management & Close Hepatology Surveillance"
            rationale = f"King's College non-acetaminophen criteria not met ({met_sub_criteria_count}/5 subcriteria met)."

        return KingsCollegeResult(
            criteria_met=criteria_met,
            pathway="non_acetaminophen",
            transplant_listing_urgency=urgency,
            criteria_details=details,
            rationale=rationale,
        )


class MELDCalculator:
    """
    Model for End-Stage Liver Disease (MELD) and MELD-Na Calculator.
    Kamath PS et al. Hepatology. 2001;33(2):464-470.
    Wiesner R et al. Mayo Clin Proc. 2001.
    """

    def calculate(self, labs: LiverFailureLabs) -> MELDResult:
        # Standard UNOS lower/upper bounds
        bili = max(1.0, labs.bilirubin_mg_dl)
        inr = max(1.0, labs.inr)

        if labs.on_dialysis:
            cr = 4.0
        else:
            cr = max(1.0, min(4.0, labs.creatinine_mg_dl))

        # Standard MELD equation: 9.57*ln(Cr) + 3.78*ln(Bili) + 11.2*ln(INR) + 6.43
        raw_meld = (
            9.57 * math.log(cr) +
            3.78 * math.log(bili) +
            11.2 * math.log(inr) +
            6.43
        )
        meld_score = round(max(6.0, min(40.0, raw_meld)), 1)

        # MELD-Na adjustment for hyponatremia (Na between 125 and 137)
        na = max(125.0, min(137.0, labs.sodium_meq_l))
        if meld_score > 11:
            meld_na = meld_score + 1.32 * (137.0 - na) - (0.033 * meld_score * (137.0 - na))
            meld_na = max(meld_score, min(40.0, meld_na))
        else:
            meld_na = meld_score
        meld_na_score = round(meld_na, 1)

        # 30-day mortality estimation
        if meld_score >= 40:
            mortality = 91.0
            tier = "Status 1A / Extremely Critical"
        elif meld_score >= 30:
            mortality = 74.5
            tier = "Tier 1 (Severe)"
        elif meld_score >= 20:
            mortality = 35.5
            tier = "Tier 2 (Moderate-High)"
        elif meld_score >= 15:
            mortality = 16.0
            tier = "Tier 3 (Moderate)"
        else:
            mortality = 4.5
            tier = "Tier 4 (Low 30-day risk)"

        return MELDResult(
            meld_score=meld_score,
            meld_na_score=meld_na_score,
            estimated_30_day_mortality_pct=mortality,
            unos_priority_tier=tier,
        )


class ALFSGPrognosticIndex:
    """
    Acute Liver Failure Study Group (ALFSG) Prognostic Index.
    Stravitz RT et al. Hepatology. 2007;46(4):1141-1148.
    """

    def calculate(
        self,
        labs: LiverFailureLabs,
        age: int,
        he_grade: int,
        etiology: str = "acetaminophen",
    ) -> ALFSGResult:
        # ALFSG points scoring
        points = 0
        if he_grade in (3, 4):
            points += 2
        elif he_grade in (1, 2):
            points += 1

        if labs.inr >= 3.5:
            points += 2
        elif labs.inr >= 2.0:
            points += 1

        if labs.bilirubin_mg_dl >= 10.0:
            points += 2
        elif labs.bilirubin_mg_dl >= 5.0:
            points += 1

        if labs.creatinine_mg_dl >= 2.0:
            points += 1

        if age >= 50:
            points += 1

        if "acetaminophen" not in etiology.lower() and "apap" not in etiology.lower():
            points += 2  # Non-APAP has lower spontaneous survival

        # Mapping points to transplant-free survival (TFS)
        if points <= 1:
            tfs = 92.0
            tier = "High Spontaneous Recovery Probability"
            rec = "Medical management with intensive hemodynamic and metabolic support."
        elif points <= 3:
            tfs = 75.0
            tier = "Moderate Spontaneous Recovery"
            rec = "Close monitoring in ICU; alert transplant coordinator."
        elif points <= 5:
            tfs = 45.0
            tier = "Guarded Prognosis"
            rec = "Initiate pre-transplant evaluation; prepare for emergent listing."
        elif points <= 7:
            tfs = 22.0
            tier = "Critical - High Mortality without Transplant"
            rec = "Urgent listing for orthotopic liver transplantation."
        else:
            tfs = 8.0
            tier = "Fulminant - Extremely Low Spontaneous Survival"
            rec = "Super-urgent Status 1A transplant listing immediately indicated."

        return ALFSGResult(
            transplant_free_survival_pct=round(tfs, 1),
            mortality_or_transplant_risk_pct=round(100.0 - tfs, 1),
            prognostic_tier=tier,
            recommendation=rec,
        )


class AcetaminophenToxicityAssessor:
    """
    Rumack-Matthew Nomogram for Acetaminophen Overdose & NAC Protocol.
    Rumack BH, Matthew H. Pediatrics. 1975;55(6):871-876.
    """

    def assess(
        self,
        time_since_ingestion_hours: float,
        serum_apap_ug_ml: float,
        alt_u_l: float = 30.0,
        inr: float = 1.0
    ) -> APAPToxicityResult:
        t = max(4.0, min(24.0, time_since_ingestion_hours))

        # 150-line: 150 ug/mL at 4h, half-life 4h (lambda = ln(2)/4 = 0.1733)
        treatment_line = 150.0 * (0.5 ** ((t - 4.0) / 4.0))
        high_risk_line = 200.0 * (0.5 ** ((t - 4.0) / 4.0))

        if serum_apap_ug_ml >= high_risk_line:
            risk = "Above 200 High-Risk Line (Probable Severe Hepatotoxicity)"
            nac = True
        elif serum_apap_ug_ml >= treatment_line:
            risk = "Above 150 Treatment Line (Possible Hepatotoxicity)"
            nac = True
        else:
            risk = "Below Treatment Line (Low Risk of Hepatotoxicity)"
            nac = (alt_u_l > 100.0 or inr > 1.5)  # If delayed presentation with established injury

        # Clinical severity
        if alt_u_l > 1000.0 or inr > 3.0:
            severity = "Fulminant Acute Liver Injury"
        elif alt_u_l > 300.0 or inr > 1.5:
            severity = "Moderate Hepatotoxicity"
        elif alt_u_l > 50.0:
            severity = "Mild Liver Transaminitis"
        else:
            severity = "No Significant Biochemical Injury"

        nac_regimen = (
            "21-Hour IV N-Acetylcysteine Regimen: "
            "1. Loading Dose: 150 mg/kg in 200 mL D5W over 60 min. "
            "2. Second Dose: 50 mg/kg in 500 mL D5W over 4 hours. "
            "3. Third Dose: 100 mg/kg in 1000 mL D5W over 16 hours."
        ) if nac else "NAC not routinely indicated; verify ingestion timeline."

        return APAPToxicityResult(
            ingestion_time_hours=round(time_since_ingestion_hours, 1),
            serum_apap_ug_ml=round(serum_apap_ug_ml, 1),
            nomogram_risk=risk,
            nac_indicated=nac,
            nac_regimen=nac_regimen,
            clinical_severity=severity,
        )


class HepaticEncephalopathyStager:
    """West Haven Criteria for Hepatic Encephalopathy."""

    STAGES = {
        0: HepaticEncephalopathyStaging(
            grade=0,
            stage_name="Minimal / Subclinical HE",
            clinical_features="Normal consciousness, subtle psychomotor slowing on specialized testing.",
            cerebral_edema_risk="Minimal (< 5%)",
            airway_management="Spontaneous breathing; standard monitoring.",
        ),
        1: HepaticEncephalopathyStaging(
            grade=1,
            stage_name="Grade I HE",
            clinical_features="Trivial lack of awareness, euphoria or anxiety, shortened attention span, impaired sleep rhythm.",
            cerebral_edema_risk="Low (< 10%)",
            airway_management="Frequent neuro checks q2h; quiet environment.",
        ),
        2: HepaticEncephalopathyStaging(
            grade=2,
            stage_name="Grade II HE",
            clinical_features="Lethargy or apathy, minimal disorientation for time or place, personality change, asterixis present.",
            cerebral_edema_risk="Moderate (15-25%)",
            airway_management="High-flow nasal cannula available; avoid sedation.",
        ),
        3: HepaticEncephalopathyStaging(
            grade=3,
            stage_name="Grade III HE",
            clinical_features="Somnolence to semi-stupor, responsive to verbal stimuli, gross disorientation, bizarre behavior.",
            cerebral_edema_risk="High (35-50%)",
            airway_management="Elective endotracheal intubation recommended for airway protection.",
        ),
        4: HepaticEncephalopathyStaging(
            grade=4,
            stage_name="Grade IV HE (Hepatic Coma)",
            clinical_features="Coma, unresponsive to verbal stimuli; decerebrate or decorticate posturing may occur.",
            cerebral_edema_risk="Critical (65-80%)",
            airway_management="Mandatory mechanical ventilation; invasive ICP monitoring or optic nerve ultrasound.",
        ),
    }

    def stage(self, grade: int) -> HepaticEncephalopathyStaging:
        clamped_grade = max(0, min(4, grade))
        return self.STAGES[clamped_grade]


class AcuteLiverFailureDecisionEngine:
    """Master Clinical Decision Support Engine for Acute Liver Failure."""

    def __init__(self):
        self.kings_evaluator = KingsCollegeEvaluator()
        self.meld_calc = MELDCalculator()
        self.alfsg_calc = ALFSGPrognosticIndex()
        self.apap_assessor = AcetaminophenToxicityAssessor()
        self.he_stager = HepaticEncephalopathyStager()

    def evaluate_patient(
        self,
        patient_id: str,
        labs: LiverFailureLabs,
        he_grade: int,
        age: int = 40,
        etiology: str = "acetaminophen",
        jaundice_to_coma_days: int = 4,
        apap_serum_ug_ml: Optional[float] = None,
        apap_ingestion_hours: Optional[float] = None,
    ) -> ComprehensiveALFEvaluation:
        if not isinstance(he_grade, int) or not (0 <= he_grade <= 4):
            raise ValueError(f"Hepatic encephalopathy grade must be an integer 0-4, got {he_grade}")
        if not (0 <= age <= 120):
            raise ValueError(f"Age must be between 0 and 120, got {age}")
        if not isinstance(etiology, str) or not etiology.strip():
            raise ValueError("Etiology must be a non-empty string")
        he_stage = self.he_stager.stage(he_grade)

        is_apap = ("acetaminophen" in etiology.lower() or "apap" in etiology.lower() or "paracetamol" in etiology.lower())

        if is_apap:
            kings_res = self.kings_evaluator.evaluate_acetaminophen(labs, he_grade)
        else:
            kings_res = self.kings_evaluator.evaluate_non_acetaminophen(labs, age, jaundice_to_coma_days, etiology)

        meld_res = self.meld_calc.calculate(labs)
        alfsg_res = self.alfsg_calc.calculate(labs, age, he_grade, etiology)

        apap_res = None
        if is_apap and apap_serum_ug_ml is not None and apap_ingestion_hours is not None:
            apap_res = self.apap_assessor.assess(apap_ingestion_hours, apap_serum_ug_ml, labs.alt_u_l, labs.inr)

        # Ammonia and Cerebral Edema Risk
        ammonia_risk = {
            "serum_ammonia_umol_l": labs.ammonia_umol_l,
            "risk_tier": "Critical (> 150 umol/L - high risk for cerebral herniation)" if labs.ammonia_umol_l > 150 else (
                "Elevated (100-150 umol/L - close ICP surveillance)" if labs.ammonia_umol_l > 100 else "Mild-Normal (< 100 umol/L)"
            ),
            "hyperosmolar_therapy_indicated": labs.ammonia_umol_l > 150 or he_grade >= 3,
            "recommended_target_sodium": "145-155 mEq/L using 3% Hypertonic Saline" if (labs.ammonia_umol_l > 150 or he_grade >= 3) else "135-145 mEq/L",
        }

        # Urgent Actions
        actions = []
        if kings_res.criteria_met:
            actions.append("EMERGENT: Contact regional liver transplant center immediately for UNOS Status 1A listing.")
        if he_grade >= 3:
            actions.append("AIRWAY: Secure endotracheal intubation for airway protection and neuroprotection.")
        if is_apap and (apap_res is None or apap_res.nac_indicated):
            actions.append("PHARMACOTHERAPY: Initiate/continue 21-hour IV N-Acetylcysteine (NAC) infusion.")
        if not is_apap and labs.inr > 2.0:
            actions.append("CONSIDER: Intravenous NAC therapy (demonstrated transplant-free survival benefit in early non-APAP ALF).")
        if ammonia_risk["hyperosmolar_therapy_indicated"]:
            actions.append("NEURO-ICU: Maintain head of bed elevated 30 degrees, induce mild hypernatremia (Na 145-150 mEq/L).")
        if labs.glucose_mg_dl < 70.0:
            actions.append("METABOLIC: Administer 10-20% IV Dextrose infusion to prevent hypoglycemia from hepatic glycogen depletion.")

        return ComprehensiveALFEvaluation(
            patient_id=patient_id,
            etiology=etiology,
            encephalopathy=he_stage,
            kings_college=kings_res,
            meld=meld_res,
            alfsg=alfsg_res,
            apap_assessment=apap_res,
            ammonia_icp_risk=ammonia_risk,
            urgent_actions=actions,
        )
