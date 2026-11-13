def generate_explanation(scenario):
    """
    Create an accessible explanation using the scenario evidence.
    """

    return {
        "summary": scenario["explanation"],
        "positive_factors": scenario["positive_factors"],
        "risk_factors": scenario["risk_factors"],
        "supporting_evidence": scenario["supporting_evidence"],
        "limitations": scenario["missing_information"]
    }
