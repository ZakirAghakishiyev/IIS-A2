def generate_recommendation(scenario):
    """
    Return the predefined recommendation for a scenario.

    The current prototype uses controlled scenario data.
    It does not generate real investment advice.
    """

    recommendation = scenario["recommendation"]

    if recommendation not in ["Buy", "Hold", "Avoid"]:
        raise ValueError("Invalid recommendation in scenario data.")

    return recommendation
