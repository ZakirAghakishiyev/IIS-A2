
from pathlib import Path
from datetime import datetime, timezone
import csv
import uuid
import os

import pandas as pd
from flask import (
    Flask, render_template, abort, request,
    redirect, url_for, session
)

from recommendation_engine import generate_recommendation
from explanation_engine import generate_explanation
from uncertainty import get_uncertainty


app = Flask(__name__)
app.secret_key = os.environ.get(
    "CLARITY_SECRET_KEY",
    "development-only-change-this-key"
)

BASE_DIR = Path(__file__).parent

DATA_FILE = BASE_DIR / "scenarios.csv"
DECISIONS_FILE = BASE_DIR / "decisions.csv"
SESSIONS_FILE = BASE_DIR / "participant_sessions.csv"

CONDITIONS = [
    "explanation_only",
    "explanation_uncertainty"
]


def load_scenarios():
    """Load the controlled investment scenarios."""
    if not DATA_FILE.exists():
        raise FileNotFoundError("scenarios.csv not found.")

    return pd.read_csv(DATA_FILE).fillna("")


def find_scenario(scenario_id):
    """Find a scenario using its ID."""
    data = load_scenarios()
    selected = data[data["scenario_id"] == scenario_id]

    if selected.empty:
        abort(404)

    return selected.iloc[0].to_dict()


def assign_session():
    """
    Give each browser session an anonymous ID and
    assign it to the currently smaller condition group.
    """
    if "session_id" in session and "condition" in session:
        return

    session_id = str(uuid.uuid4())

    counts = {
        "explanation_only": 0,
        "explanation_uncertainty": 0
    }

    if SESSIONS_FILE.exists():
        with SESSIONS_FILE.open(
            newline="",
            encoding="utf-8"
        ) as file:
            for row in csv.DictReader(file):
                condition = row.get("condition")
                if condition in counts:
                    counts[condition] += 1

    # Choose the condition with fewer assigned sessions.
    # Alternate when the counts are equal.
    if counts["explanation_only"] <= counts["explanation_uncertainty"]:
        condition = "explanation_only"
    else:
        condition = "explanation_uncertainty"

    session["session_id"] = session_id
    session["condition"] = condition

    fields = [
        "session_id",
        "condition",
        "assigned_at"
    ]

    file_exists = SESSIONS_FILE.exists()

    with SESSIONS_FILE.open(
        mode="a",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "session_id": session_id,
            "condition": condition,
            "assigned_at": datetime.now(timezone.utc).isoformat()
        })


def get_condition():
    """Return the condition assigned to this session."""
    assign_session()
    return session["condition"]


def decision_already_exists(session_id, scenario_id):
    """Check whether this session has already answered this scenario."""
    if not DECISIONS_FILE.exists():
        return False

    with DECISIONS_FILE.open(
        newline="",
        encoding="utf-8"
    ) as file:
        for row in csv.DictReader(file):
            if (
                row.get("session_id") == session_id
                and row.get("scenario_id") == scenario_id
            ):
                return True

    return False


def save_decision(record):
    """Save one decision to the CSV file."""
    fields = [
        "timestamp",
        "session_id",
        "scenario_id",
        "company_name",
        "recommendation",
        "reference_assessment",
        "confidence_score",
        "uncertainty_level",
        "condition",
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


def calculate_metrics(records):
    """Calculate reliance measures from controlled decisions."""
    total = len(records)

    defensible = [
        row for row in records
        if row["reference_assessment"] == "Defensible"
    ]

    misleading = [
        row for row in records
        if row["reference_assessment"] == "Misleading"
    ]

    appropriate = sum(
        1 for row in records
        if (
            row["reference_assessment"] == "Defensible"
            and row["user_decision"] == "Accept"
        ) or (
            row["reference_assessment"] == "Misleading"
            and row["user_decision"] == "Reject"
        )
    )

    over_reliance = sum(
        1 for row in misleading
        if row["user_decision"] == "Accept"
    )

    under_reliance = sum(
        1 for row in defensible
        if row["user_decision"] == "Reject"
    )

    accepted = sum(
        1 for row in records
        if row["user_decision"] == "Accept"
    )

    rejected = sum(
        1 for row in records
        if row["user_decision"] == "Reject"
    )

    return {
        "total": total,
        "accepted": accepted,
        "rejected": rejected,
        "appropriate": appropriate,
        "appropriate_rate": round(
            appropriate / total * 100, 1
        ) if total else 0,
        "over_reliance": over_reliance,
        "over_reliance_rate": round(
            over_reliance / len(misleading) * 100, 1
        ) if misleading else 0,
        "misleading_total": len(misleading),
        "under_reliance": under_reliance,
        "under_reliance_rate": round(
            under_reliance / len(defensible) * 100, 1
        ) if defensible else 0,
        "defensible_total": len(defensible)
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/scenarios")
def scenarios():
    get_condition()
    data = load_scenarios()

    return render_template(
        "scenarios.html",
        scenarios=data.to_dict(orient="records")
    )


@app.route("/scenario/<scenario_id>")
def scenario_detail(scenario_id):
    scenario = find_scenario(scenario_id)
    get_condition()

    return render_template(
        "scenario_detail.html",
        scenario=scenario
    )


@app.route("/recommendation/<scenario_id>")
def recommendation(scenario_id):
    scenario = find_scenario(scenario_id)
    condition = get_condition()

    recommendation_result = generate_recommendation(scenario)
    explanation = generate_explanation(scenario)
    uncertainty = get_uncertainty(scenario)

    return render_template(
        "recommendation.html",
        scenario=scenario,
        recommendation=recommendation_result,
        explanation=explanation,
        uncertainty=uncertainty,
        condition=condition,
        show_uncertainty=(
            condition == "explanation_uncertainty"
        ),
        submitted=request.args.get("submitted") == "1",
        already_submitted=(
            request.args.get("already_submitted") == "1"
        )
    )


@app.route("/decision/<scenario_id>", methods=["POST"])
def submit_decision(scenario_id):
    scenario = find_scenario(scenario_id)
    condition = get_condition()
    session_id = session["session_id"]

    # Prevent a second decision for this scenario
    # from the same browser session.
    if decision_already_exists(session_id, scenario_id):
        return redirect(
            url_for(
                "recommendation",
                scenario_id=scenario_id,
                already_submitted=1
            )
        )

    user_decision = request.form.get("user_decision", "")
    reason = request.form.get("reason", "").strip()

    if user_decision not in ["Accept", "Reject"]:
        abort(400, description="Please select Accept or Reject.")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "scenario_id": scenario["scenario_id"],
        "company_name": scenario["company_name"],
        "recommendation": scenario["recommendation"],
        "reference_assessment": scenario["reference_assessment"],
        "confidence_score": scenario["confidence_score"],
        "uncertainty_level": scenario["uncertainty_level"],
        "condition": condition,
        "user_decision": user_decision,
        "reason": reason
    }

    save_decision(record)

    return redirect(
        url_for(
            "recommendation",
            scenario_id=scenario_id,
            submitted=1
        )
    )


@app.route("/evaluation")
def evaluation():
    if not DECISIONS_FILE.exists():
        records = []
    else:
        data = pd.read_csv(DECISIONS_FILE).fillna("")
        records = data.to_dict(orient="records")

    experimental_records = [
        row for row in records
        if row.get("condition") in CONDITIONS
        and row.get("reference_assessment") in [
            "Defensible", "Misleading"
        ]
    ]

    explanation_only = [
        row for row in experimental_records
        if row["condition"] == "explanation_only"
    ]

    explanation_uncertainty = [
        row for row in experimental_records
        if row["condition"] == "explanation_uncertainty"
    ]

    return render_template(
        "evaluation.html",
        overall=calculate_metrics(experimental_records),
        explanation_only=calculate_metrics(explanation_only),
        explanation_uncertainty=calculate_metrics(
            explanation_uncertainty
        ),
        total_records=len(records),
        excluded_records=len(records) - len(experimental_records)
    )


if __name__ == "__main__":
    app.run(debug=True)
