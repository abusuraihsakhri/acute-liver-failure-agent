"""
Root Test Runner for Acute Liver Failure (ALF) Prognostication System.
"""

import sys
import unittest
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_acute_liver_failure_agent import (
    TestKingsCollegeCriteria,
    TestMELDCalculations,
    TestALFSGModel,
    TestRumackMatthewNomogram,
    TestEncephalopathyAndAmmonia,
    TestMasterDecisionEngine,
    TestCLIExecution,
)

if __name__ == "__main__":
    unittest.main()
