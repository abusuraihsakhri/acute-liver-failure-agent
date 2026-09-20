#!/usr/bin/env python3
"""Acute liver failure prognostic and critical-care decision-support utilities.

The module implements established prognostic tools and intentionally separates
prognostic criteria from organ-allocation policy. Results are decision-support
outputs only and require clinical interpretation at an experienced liver
transplant center.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
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

    def __post_init__(self) -> None:
        ranges = {
            "INR": (self.inr, 0.1, 50.0),
            "Bilirubin": (self.bilirubin_mg_dl, 0.0, 100.0),
            "Creatinine": (self.creatinine_mg_dl, 0.0, 30.0),
            "Arterial pH": (self.arterial_ph, 6.5, 7.8),
            "Lactate": (self.lactate_mmol_l, 0.0, 30.0),
            "Sodium": (self.sodium_meq_l, 100.0, 180.0),
            "Ammonia": (self.ammonia_umol_l, 0.0, 500.0),
            "AST": (self.ast_u_l, 0.0, 50000.0),
            "ALT": (self.alt_u_l, 0.0, 50000.0),
            "Platelets": (self.platelets_k_ul, 0.0, 1500.0),
            "Glucose": (self.glucose_mg_dl, 0.0, 1200.0),
        }
        for label, (value, lower, upper) in ranges.items():
            if not math.isfinite(value) or not (lower <= value <= upper):
                raise ValueError(f"{label} must be between {lower} and {upper}, got {value}")


@dataclass
class KingsCollegeResult:
    criteria_met: bool
    pathway: str
    transplant_listing_urgency: str
    criteria_details: Dict[str, bool]
    rationale: str


@dataclass
class MELDResult:
    meld_score: float
    meld_na_score: float
    estimated_30_day_mortality_pct: Optional[float]
    unos_priority_tier: str
    interpretation: str


@dataclass
class ALFSGResult:
    transplant_free_survival_pct: float
    mortality_or_transplant_risk_pct: float
    prognostic_tier: str
    recommendation: str
    model_note: str


@dataclass
class APAPToxicityResult:
    ingestion_time_hours: float
    serum_apap_ug_ml: float
    nomogram_risk: str
    nac_indicated: Optional[bool]
    nac_regimen: str
    clinical_severity: str
    nomogram_applicable: bool = True


@dataclass
class HepaticEncephalopathyStaging:
    grade: int
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
    """King's College Hospital poor-prognosis criteria for acute liver failure."""

    def evaluate_acetaminophen(
        self,
        labs: LiverFailureLabs,
        he_grade: int,
        post_resuscitation_lactate: Optional[float] = None,
    ) -> KingsCollegeResult:
        if post_resuscitation_lactate is not None:
            if not math.isfinite(post_resuscitation_lactate) or not (0.0 <= post_resuscitation_lactate <= 30.0):
                raise ValueError(
                    "Post-resuscitation lactate must be between 0.0 and 30.0 mmol/L"
                )

        lactate_criterion = (
            post_resuscitation_lactate is not None
            and post_resuscitation_lactate > 3.0
        )
        details = {
            "arterial_ph_lt_7_30": labs.arterial_ph < 7.30,
            "post_resuscitation_lactate_gt_3_0": lactate_criterion,
            "combined_inr_cr_he": (
                labs.inr > 6.5
                and labs.creatinine_mg_dl > 3.4
                and he_grade >= 3
            ),
            "inr_gt_6_5": labs.inr > 6.5,
            "creatinine_gt_3_4": labs.creatinine_mg_dl > 3.4,
            "grade_3_4_encephalopathy": he_grade >= 3,
        }

        criteria_met = (
            details["arterial_ph_lt_7_30"]
            or details["post_resuscitation_lactate_gt_3_0"]
            or details["combined_inr_cr_he"]
        )

        if criteria_met:
            urgency = "Urgent liver-transplant-center evaluation (KCC met)"
            rationale = (
                "King's College poor-prognosis criteria are met. KCC supports urgent "
                "transplant assessment but does not itself establish OPTN Status 1A."
            )
        else:
            urgency = "Serial ALF assessment; KCC not currently met"
            rationale = (
                "King's College criteria are not currently met. This does not exclude "
                "clinical deterioration or the need for early transplant-center discussion."
            )

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
        etiology: str = "indeterminate",
    ) -> KingsCollegeResult:
        normalized = etiology.lower().replace("_", " ").replace("-", " ")
        unfavorable_etiology = any(
            term in normalized
            for term in (
                "non a non b",
                "seronegative",
                "indeterminate",
                "drug induced",
                "dili",
                "halothane",
                "wilson",
            )
        )

        sub_criteria = {
            "age_lt_10_or_gt_40": age < 10 or age > 40,
            "unfavorable_etiology": unfavorable_etiology,
            "jaundice_to_encephalopathy_gt_7d": jaundice_to_coma_days > 7,
            "inr_gt_3_5": labs.inr > 3.5,
            "bilirubin_gt_17_5": labs.bilirubin_mg_dl > 17.5,
        }
        count = sum(bool(v) for v in sub_criteria.values())
        single_major = labs.inr > 6.5
        criteria_met = single_major or count >= 3

        details = {
            "inr_gt_6_5_standalone": single_major,
            "three_or_more_subcriteria": count >= 3,
            **sub_criteria,
        }

        if criteria_met:
            urgency = "Urgent liver-transplant-center evaluation (KCC met)"
            rationale = (
                f"King's College non-acetaminophen criteria are met "
                f"(INR > 6.5: {single_major}; subcriteria: {count}/5). "
                "KCC is a prognostic tool, not an OPTN Status 1A determination."
            )
        else:
            urgency = "Serial ALF assessment; KCC not currently met"
            rationale = (
                f"King's College non-acetaminophen criteria are not met "
                f"({count}/5 subcriteria). Early transplant-center assessment may still be appropriate."
            )

        return KingsCollegeResult(
            criteria_met=criteria_met,
            pathway="non_acetaminophen",
            transplant_listing_urgency=urgency,
            criteria_details=details,
            rationale=rationale,
        )


class MELDCalculator:
    """Legacy MELD and MELD-Na calculations retained as prognostic adjuncts.

    These values do not determine OPTN Status 1A for acute liver failure and
    should not be described as current U.S. organ-allocation scores.
    """

    def calculate(self, labs: LiverFailureLabs) -> MELDResult:
        bili = max(1.0, labs.bilirubin_mg_dl)
        inr = max(1.0, labs.inr)
        cr = 4.0 if labs.on_dialysis else max(1.0, min(4.0, labs.creatinine_mg_dl))

        raw_meld = (
            9.57 * math.log(cr)
            + 3.78 * math.log(bili)
            + 11.2 * math.log(inr)
            + 6.43
        )
        meld_score = round(max(6.0, min(40.0, raw_meld)), 1)

        na = max(125.0, min(137.0, labs.sodium_meq_l))
        if meld_score > 11:
            meld_na = (
                meld_score
                + 1.32 * (137.0 - na)
                - 0.033 * meld_score * (137.0 - na)
            )
            meld_na = max(meld_score, min(40.0, meld_na))
        else:
            meld_na = meld_score

        return MELDResult(
            meld_score=meld_score,
            meld_na_score=round(meld_na, 1),
            estimated_30_day_mortality_pct=None,
            unos_priority_tier="Not applicable to OPTN Status 1A in acute liver failure",
            interpretation=(
                "Historical MELD/MELD-Na calculation shown as a prognostic adjunct only. "
                "Current OPTN Status 1A eligibility is assessed separately."
            ),
        )


class ALFSGPrognosticIndex:
    """Published ALFSG model for 21-day transplant-free survival.

    Koch DG, Tillman H, Durkalski V, et al. Clin Gastroenterol Hepatol.
    2016;14(8):1199-1206.e2. The model uses coma grade, etiology,
    vasopressor use, bilirubin, and INR.
    """

    FAVORABLE_ETIOLOGIES = {
        "acetaminophen",
        "apap",
        "paracetamol",
        "ischemic",
        "ischemia",
        "shock liver",
        "pregnancy",
        "pregnancy associated",
        "acute fatty liver of pregnancy",
        "aflp",
        "hellp",
        "hepatitis a",
        "hav",
        "viral hav",
    }

    @classmethod
    def _is_favorable_etiology(cls, etiology: str) -> bool:
        normalized = " ".join(
            etiology.lower().replace("_", " ").replace("-", " ").split()
        )
        if normalized in cls.FAVORABLE_ETIOLOGIES:
            return True
        return (
            "acetaminophen" in normalized
            or "paracetamol" in normalized
            or normalized.startswith("apap")
            or "ischemi" in normalized
            or "pregnan" in normalized
        )

    def calculate(
        self,
        labs: LiverFailureLabs,
        age: int,
        he_grade: int,
        etiology: str = "acetaminophen",
        vasopressor_use: bool = False,
    ) -> ALFSGResult:
        # Age is retained in the signature for backwards compatibility; it is
        # not a variable in the published 2016 ALFSG prognostic model.
        del age

        deep_he = 1 if he_grade >= 3 else 0
        favorable = 1 if self._is_favorable_etiology(etiology) else 0
        vasopressor = 1 if vasopressor_use else 0

        # Validation permits bilirubin of zero; use a small positive floor only
        # for the logarithm. ALF cohorts typically have values well above this.
        bilirubin = max(labs.bilirubin_mg_dl, 0.1)
        inr = max(labs.inr, 0.1)

        logit = (
            2.67
            - 0.95 * deep_he
            + 1.56 * favorable
            - 1.25 * vasopressor
            - 0.70 * math.log(bilirubin)
            - 1.35 * math.log(inr)
        )
        tfs = 100.0 / (1.0 + math.exp(-logit))

        if tfs >= 80.0:
            tier = "Higher predicted 21-day transplant-free survival"
            recommendation = (
                "Continue intensive ALF management with serial reassessment; "
                "transplant decisions require the full clinical context."
            )
        elif tfs >= 50.0:
            tier = "Intermediate predicted 21-day transplant-free survival"
            recommendation = (
                "Urgent transplant-center evaluation and serial reassessment are appropriate."
            )
        else:
            tier = "Lower predicted 21-day transplant-free survival"
            recommendation = (
                "Urgent transplant-center evaluation is warranted; do not use this "
                "probability as a stand-alone listing or futility rule."
            )

        rounded = round(tfs, 1)
        return ALFSGResult(
            transplant_free_survival_pct=rounded,
            mortality_or_transplant_risk_pct=round(100.0 - rounded, 1),
            prognostic_tier=tier,
            recommendation=recommendation,
            model_note=(
                "Published ALFSG 2016 admission model; predicts 21-day transplant-free "
                "survival and is not a transplant-listing rule."
            ),
        )


class AcetaminophenToxicityAssessor:
    """Revised Rumack-Matthew nomogram support for acute acetaminophen ingestion."""

    @staticmethod
    def _severity(alt_u_l: float, inr: float) -> str:
        if alt_u_l > 1000.0 or inr > 3.0:
            return "Severe acute liver injury"
        if alt_u_l > 300.0 or inr > 1.5:
            return "Moderate biochemical liver injury"
        if alt_u_l > 50.0:
            return "Mild transaminase elevation"
        return "No significant biochemical injury in supplied values"

    def assess(
        self,
        time_since_ingestion_hours: float,
        serum_apap_ug_ml: float,
        alt_u_l: float = 30.0,
        inr: float = 1.0,
    ) -> APAPToxicityResult:
        if not math.isfinite(time_since_ingestion_hours) or time_since_ingestion_hours < 0:
            raise ValueError("Time since ingestion must be a finite non-negative number")
        if not math.isfinite(serum_apap_ug_ml) or serum_apap_ug_ml < 0:
            raise ValueError("Acetaminophen concentration must be a finite non-negative number")

        severity = self._severity(alt_u_l, inr)

        if not (4.0 <= time_since_ingestion_hours <= 24.0):
            return APAPToxicityResult(
                ingestion_time_hours=round(time_since_ingestion_hours, 1),
                serum_apap_ug_ml=round(serum_apap_ug_ml, 1),
                nomogram_risk=(
                    "Rumack-Matthew nomogram not applicable outside 4-24 hours "
                    "after an acute ingestion."
                ),
                nac_indicated=None,
                nac_regimen=(
                    "Do not use an out-of-range nomogram value to withhold acetylcysteine. "
                    "Use poison-center/clinical-toxicology guidance and clinical/laboratory context."
                ),
                clinical_severity=severity,
                nomogram_applicable=False,
            )

        treatment_line = 150.0 * (0.5 ** ((time_since_ingestion_hours - 4.0) / 4.0))
        high_risk_line = 300.0 * (0.5 ** ((time_since_ingestion_hours - 4.0) / 4.0))

        if serum_apap_ug_ml >= high_risk_line:
            risk = "At/above revised high-risk line"
            nac = True
        elif serum_apap_ug_ml >= treatment_line:
            risk = "At/above 150-treatment line"
            nac = True
        else:
            risk = "Below 150-treatment line"
            # Established liver injury is a separate reason to treat and should
            # not be overruled by a below-line nomogram point.
            nac = alt_u_l > 50.0 or inr > 1.5

        nac_regimen = (
            "Acetylcysteine indicated. Use a validated local/poison-center regimen "
            "delivering at least 300 mg/kg during the first 20-24 hours and continue "
            "until accepted stopping criteria are met; do not stop solely because a "
            "fixed infusion duration has elapsed."
            if nac
            else
            "Nomogram does not indicate acetylcysteine from the supplied values; "
            "confirm the history and repeat levels when delayed absorption is plausible."
        )

        return APAPToxicityResult(
            ingestion_time_hours=round(time_since_ingestion_hours, 1),
            serum_apap_ug_ml=round(serum_apap_ug_ml, 1),
            nomogram_risk=risk,
            nac_indicated=nac,
            nac_regimen=nac_regimen,
            clinical_severity=severity,
            nomogram_applicable=True,
        )


class HepaticEncephalopathyStager:
    """West Haven staging with ALF-oriented airway and neurologic cautions."""

    STAGES = {
        0: HepaticEncephalopathyStaging(
            0,
            "Minimal / no overt HE",
            "No overt encephalopathy; subtle psychomotor abnormalities may require testing.",
            "Low from encephalopathy grade alone",
            "Routine airway assessment and serial neurologic examination.",
        ),
        1: HepaticEncephalopathyStaging(
            1,
            "Grade I HE",
            "Trivial lack of awareness, euphoria/anxiety, shortened attention span, altered sleep rhythm.",
            "Low, but ALF can evolve rapidly",
            "Frequent neurologic reassessment; avoid unnecessary sedatives.",
        ),
        2: HepaticEncephalopathyStaging(
            2,
            "Grade II HE",
            "Lethargy/apathy, disorientation, personality change, inappropriate behavior, asterixis.",
            "Increasing; monitor closely for progression",
            "ICU-level monitoring when ALF is established; reassess airway frequently.",
        ),
        3: HepaticEncephalopathyStaging(
            3,
            "Grade III HE",
            "Somnolence to semi-stupor, response to stimuli, gross disorientation, bizarre behavior.",
            "High; cerebral edema/intracranial hypertension surveillance is important",
            "Endotracheal intubation is generally recommended for airway protection.",
        ),
        4: HepaticEncephalopathyStaging(
            4,
            "Grade IV HE (coma)",
            "Coma and no meaningful response to verbal stimuli.",
            "High; cerebral edema/intracranial hypertension surveillance is important",
            "Mechanical ventilation is typically required; use center-specific neurocritical monitoring.",
        ),
    }

    def stage(self, grade: int) -> HepaticEncephalopathyStaging:
        if not isinstance(grade, int) or grade not in self.STAGES:
            raise ValueError(f"Hepatic encephalopathy grade must be an integer 0-4, got {grade}")
        return self.STAGES[grade]


class AcuteLiverFailureDecisionEngine:
    """Combine prognostic models without converting them into allocation decisions."""

    def __init__(self) -> None:
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
        post_resuscitation_lactate: Optional[float] = None,
        vasopressor_use: bool = False,
    ) -> ComprehensiveALFEvaluation:
        if not isinstance(he_grade, int) or not (0 <= he_grade <= 4):
            raise ValueError(f"Hepatic encephalopathy grade must be an integer 0-4, got {he_grade}")
        if not isinstance(age, int) or not (0 <= age <= 120):
            raise ValueError(f"Age must be an integer between 0 and 120, got {age}")
        if not isinstance(jaundice_to_coma_days, int) or jaundice_to_coma_days < 0:
            raise ValueError("Jaundice-to-encephalopathy interval must be a non-negative integer")
        if not isinstance(etiology, str) or not etiology.strip():
            raise ValueError("Etiology must be a non-empty string")
        if bool(apap_serum_ug_ml is None) != bool(apap_ingestion_hours is None):
            raise ValueError(
                "Acetaminophen concentration and ingestion time must be supplied together"
            )

        he_stage = self.he_stager.stage(he_grade)
        normalized = etiology.lower()
        is_apap = any(term in normalized for term in ("acetaminophen", "apap", "paracetamol"))

        if is_apap:
            kings = self.kings_evaluator.evaluate_acetaminophen(
                labs,
                he_grade,
                post_resuscitation_lactate=post_resuscitation_lactate,
            )
        else:
            kings = self.kings_evaluator.evaluate_non_acetaminophen(
                labs,
                age,
                jaundice_to_coma_days,
                etiology,
            )

        meld = self.meld_calc.calculate(labs)
        alfsg = self.alfsg_calc.calculate(
            labs,
            age,
            he_grade,
            etiology,
            vasopressor_use=vasopressor_use,
        )

        apap = None
        if is_apap and apap_serum_ug_ml is not None:
            apap = self.apap_assessor.assess(
                apap_ingestion_hours,
                apap_serum_ug_ml,
                labs.alt_u_l,
                labs.inr,
            )

        neuro_high_risk = he_grade >= 3 or labs.ammonia_umol_l > 150
        ammonia_risk = {
            "serum_ammonia_umol_l": labs.ammonia_umol_l,
            "risk_tier": (
                "High-risk feature (>150 umol/L)"
                if labs.ammonia_umol_l > 150
                else (
                    "Elevated (100-150 umol/L)"
                    if labs.ammonia_umol_l > 100
                    else "Below 100 umol/L"
                )
            ),
            # Retained for API compatibility. True means osmotherapy/hypernatremia
            # should be considered in the full neurocritical context, not that a
            # treatment order can be generated from this value alone.
            "hyperosmolar_therapy_indicated": neuro_high_risk,
            "hyperosmolar_therapy_consideration": neuro_high_risk,
            "recommended_target_sodium": (
                "Consider 145-155 mEq/L only under ICU/transplant-center neurocritical protocol"
                if neuro_high_risk
                else "No prophylactic hypernatremia target generated by this tool"
            ),
        }

        actions: List[str] = []
        if kings.criteria_met:
            actions.append(
                "TRANSPLANT: KCC poor-prognosis criteria met — contact/transfer to an "
                "experienced liver transplant center urgently. KCC does not itself establish OPTN Status 1A."
            )
        else:
            actions.append(
                "TRANSPLANT: Acute liver failure warrants early transplant-center discussion "
                "and serial prognostic reassessment even when KCC is not met."
            )

        if he_grade >= 3:
            actions.append(
                "AIRWAY/NEURO: High-grade encephalopathy generally requires intubation "
                "for airway protection and neurocritical monitoring."
            )

        if is_apap:
            actions.append(
                "TOXICOLOGY: Initiate/continue IV acetylcysteine when clinically indicated "
                "and use poison-center/toxicology stopping criteria rather than a fixed 21-hour stop."
            )
            if apap is not None and not apap.nomogram_applicable:
                actions.append(
                    "TOXICOLOGY: The supplied acetaminophen time point is outside the "
                    "4-24 hour Rumack-Matthew nomogram window; do not extrapolate the nomogram."
                )
        elif he_grade <= 2:
            actions.append(
                "THERAPY: Consider IV acetylcysteine in early-stage non-acetaminophen ALF "
                "according to transplant-center protocol."
            )

        if neuro_high_risk:
            actions.append(
                "NEUROCRITICAL: Treat as increased cerebral-edema/intracranial-hypertension risk; "
                "consider hypertonic-saline strategy only within an ICU/transplant-center protocol."
            )

        if labs.glucose_mg_dl < 70.0:
            actions.append(
                "METABOLIC: Correct hypoglycemia promptly and monitor glucose frequently."
            )

        return ComprehensiveALFEvaluation(
            patient_id=patient_id,
            etiology=etiology,
            encephalopathy=he_stage,
            kings_college=kings,
            meld=meld,
            alfsg=alfsg,
            apap_assessment=apap,
            ammonia_icp_risk=ammonia_risk,
            urgent_actions=actions,
        )
