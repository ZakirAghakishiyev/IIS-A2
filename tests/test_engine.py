
import unittest

from recommendation_engine import generate_recommendation
from explanation_engine import (
    generate_explanation,
    generate_preference_insight
)
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

        self.preferences = {
            "investment_horizon": "long",
            "risk_tolerance": "low",
            "investment_priority": "stability"
        }

    # Recommendation tests

    def test_recommendation(self):
        self.assertEqual(
            generate_recommendation(self.scenario), "Buy"
        )

    def test_all_valid_recommendations(self):
        for recommendation in ["Buy", "Hold", "Avoid"]:
            self.scenario["recommendation"] = recommendation

            self.assertEqual(
                generate_recommendation(self.scenario),
                recommendation
            )

    def test_invalid_recommendation(self):
        self.scenario["recommendation"] = "Strong Buy"

        with self.assertRaises(ValueError):
            generate_recommendation(self.scenario)

    # Explanation tests

    def test_explanation(self):
        result = generate_explanation(self.scenario)

        self.assertIn("summary", result)
        self.assertIn("positive_factors", result)
        self.assertIn("risk_factors", result)
        self.assertIn("supporting_evidence", result)
        self.assertIn("limitations", result)

    # Uncertainty tests

    def test_uncertainty(self):
        result = get_uncertainty(self.scenario)

        self.assertEqual(result["confidence_percentage"], 88)
        self.assertEqual(result["uncertainty_level"], "Low")

    def test_confidence_out_of_range(self):
        self.scenario["confidence_score"] = 1.5

        with self.assertRaises(ValueError):
            get_uncertainty(self.scenario)

    def test_negative_confidence(self):
        self.scenario["confidence_score"] = -0.2

        with self.assertRaises(ValueError):
            get_uncertainty(self.scenario)

    def test_invalid_uncertainty_level(self):
        self.scenario["uncertainty_level"] = "Extreme"

        with self.assertRaises(ValueError):
            get_uncertainty(self.scenario)

    # Personalisation tests

    def test_preference_insight(self):
        result = generate_preference_insight(
            self.scenario,
            self.preferences
        )

        self.assertEqual(result["risk_tolerance"], "Low")
        self.assertEqual(result["investment_horizon"], "Long")
        self.assertEqual(result["investment_priority"], "Stability")

        self.assertEqual(len(result["insights"]), 3)

    def test_high_uncertainty_and_low_risk(self):
        self.scenario["uncertainty_level"] = "High"

        result = generate_preference_insight(
            self.scenario,
            self.preferences
        )

        self.assertIn(
            "high uncertainty",
            result["insights"][0]
        )

    def test_personalisation_does_not_change_recommendation(self):
        original = generate_recommendation(self.scenario)

        generate_preference_insight(
            self.scenario,
            self.preferences
        )

        self.assertEqual(
            generate_recommendation(self.scenario),
            original
        )


if __name__ == "__main__":
    unittest.main()
