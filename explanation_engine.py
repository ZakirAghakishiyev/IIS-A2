
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


def generate_preference_insight(scenario, preferences):
    """
    Contextualise the scenario explanation using user preferences.

    This does not alter the underlying recommendation.
    """

    horizon = preferences["investment_horizon"]
    risk = preferences["risk_tolerance"]
    priority = preferences["investment_priority"]

    insights = []

    # Risk tolerance
    if risk == "low":

        if scenario["uncertainty_level"] == "High":
            insights.append(
                "Your preference for lower risk may conflict "
                "with the high uncertainty in this scenario. "
                "Pay particular attention to the identified risks."
            )

        else:
            insights.append(
                "Your preference for lower risk makes it "
                "important to review the potential downside "
                "and missing information before deciding."
            )

    elif risk == "medium":

        insights.append(
            "You indicated a medium risk tolerance. Consider "
            "whether the potential benefits justify the "
            "risks and uncertainty described."
        )

    else:

        insights.append(
            "You indicated that you are comfortable with higher "
            "risk. This does not remove the need to assess the "
            "evidence and possible downside."
        )

    # Investment horizon
    if horizon == "short":

        insights.append(
            "For a short-term horizon, pay particular attention "
            "to near-term risks and the available cash runway."
        )

    elif horizon == "medium":

        insights.append(
            "For a medium-term horizon, consider how the "
            "company's financial position and identified risks "
            "could develop over time."
        )

    else:

        insights.append(
            "For a long-term horizon, consider the sustainability "
            "of the company's growth and its longer-term risks."
        )

    # Investment priority
    if priority == "growth":

        insights.append(
            "Your priority is growth. Review the revenue growth "
            "and positive factors alongside the risks that could "
            "limit future progress."
        )

    elif priority == "stability":

        insights.append(
            "Your priority is stability. Give particular attention "
            "to profitability, debt, cash runway and the identified "
            "risk factors."
        )

    else:

        insights.append(
            "Your priority is balanced. Consider both the "
            "company's positive factors and its financial and "
            "operational risks."
        )

    return {
        "risk_tolerance": risk.title(),
        "investment_horizon": horizon.title(),
        "investment_priority": priority.title(),
        "insights": insights
    }
