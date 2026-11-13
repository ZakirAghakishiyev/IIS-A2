def get_uncertainty(scenario):
    """
    Retrieve the controlled confidence and uncertainty
    information assigned to a scenario.
    """

    confidence = float(scenario["confidence_score"])
    uncertainty_level = scenario["uncertainty_level"]

    if not 0 <= confidence <= 1:
        raise ValueError("Confidence must be between 0 and 1.")

    if uncertainty_level not in ["Low", "Medium", "High"]:
        raise ValueError("Invalid uncertainty level.")

    return {
        "confidence": confidence,
        "confidence_percentage": round(confidence * 100),
        "uncertainty_level": uncertainty_level,
        "confidence_basis": scenario["confidence_basis"]
    }
