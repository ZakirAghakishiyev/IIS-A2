from pathlib import Path
from datetime import datetime, timezone
import csv

import pandas as pd
from flask import (
    Flask, render_template, abort, request,
    redirect, url_for
)

from recommendation_engine import generate_recommendation
from explanation_engine import generate_explanation
from uncertainty import get_uncertainty

app = Flask(__name__)

DATA_FILE = Path(__file__).parent / "scenarios.csv"
DECISIONS_FILE = Path(__file__).parent / "decisions.csv"


def load_scenarios():
    """Load investment scenarios from the CSV file."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            "scenarios.csv must be in the same folder as app.py"
        )

    return pd.read_csv(DATA_FILE).fillna("")


def find_scenario(scenario_id):
    """Find a scenario by its ID."""
    data = load_scenarios()
    selected = data[data["scenario_id"] == scenario_id]

    if selected.empty:
        abort(404)

    return selected.iloc[0].to_dict()


def save_decision(record):
    """Append a user decision to decisions.csv."""
    fields = [
        "timestamp",
        "scenario_id",
        "company_name",
        "recommendation",
        "confidence_score",
        "uncertainty_level",
        "user_decision",
        "reason"
    ]

    file_exists = DECISIONS_FILE.exists()

    with DECISIONS_FILE.open(
        mode="a",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)

        if not file_exists:
            writer.writeheader()

        writer.writerow(record)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/scenarios")
def scenarios():
    data = load_scenarios()

    return render_template(
        "scenarios.html",
        scenarios=data.to_dict(orient="records")
    )


@app.route("/scenario/<scenario_id>")
def scenario_detail(scenario_id):
    scenario = find_scenario(scenario_id)

    return render_template(
        "scenario_detail.html",
        scenario=scenario
    )


@app.route("/recommendation/<scenario_id>")
def recommendation(scenario_id):
    scenario = find_scenario(scenario_id)

    recommendation_result = generate_recommendation(scenario)
    explanation = generate_explanation(scenario)
    uncertainty = get_uncertainty(scenario)

    return render_template(
        "recommendation.html",
        scenario=scenario,
        recommendation=recommendation_result,
        explanation=explanation,
        uncertainty=uncertainty,
        submitted=request.args.get("submitted") == "1"
    )


@app.route("/decision/<scenario_id>", methods=["POST"])
def submit_decision(scenario_id):
    scenario = find_scenario(scenario_id)

    user_decision = request.form.get("user_decision", "")
    reason = request.form.get("reason", "").strip()

    if user_decision not in ["Accept", "Reject"]:
        abort(400, description="Please select Accept or Reject.")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario_id": scenario["scenario_id"],
        "company_name": scenario["company_name"],
        "recommendation": scenario["recommendation"],
        "confidence_score": scenario["confidence_score"],
        "uncertainty_level": scenario["uncertainty_level"],
        "user_decision": user_decision,
        "reason": reason
    }

    save_decision(record)

    return redirect(
        url_for("recommendation",
                scenario_id=scenario_id,
                submitted=1)
    )


if __name__ == "__main__":
    app.run(debug=True)
