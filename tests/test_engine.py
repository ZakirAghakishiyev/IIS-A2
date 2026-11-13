import unittest

from recommendation_engine import generate_recommendation
from explanation_engine import generate_explanation
from uncertainty import get_uncertainty


class TestClarityEngine(unittest.TestCase):

    def setUp(self):
        self.scenario = {
            "recommendation": "Buy",
            "explanation": "The company shows sustained growth.",
            "positive_factors": "Strong revenue growth",
            "risk_factors": "Competitive pressure",
            "supporting_evidence": "Revenue increased by 18%.",
            "missing_information": "Customer concentration data",
            "confidence_score": 0.88,
            "uncertainty_level": "Low",
            "confidence_basis": "Consistent financial indicators."
        }

    def test_recommendation(self):
        self.assertEqual(
            generate_recommendation(self.scenario), "Buy"
        )

    def test_explanation(self):
        result = generate_explanation(self.scenario)
        self.assertIn("summary", result)
        self.assertIn("limitations", result)

    def test_uncertainty(self):
        result = get_uncertainty(self.scenario)
        self.assertEqual(result["confidence_percentage"], 88)
        self.assertEqual(result["uncertainty_level"], "Low")


if __name__ == "__main__":
    unittest.main()
