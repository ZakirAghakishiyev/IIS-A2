
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
from explanation_engine import (
    generate_explanation,
    generate_preference_insight
)
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
COMPREHENSION_FILE = BASE_DIR / "comprehension.csv"

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



def comprehension_already_exists(session_id, scenario_id):
    """Check whether this session has completed the comprehension check."""
    if not COMPREHENSION_FILE.exists():
        return False

    with COMPREHENSION_FILE.open(
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


def save_comprehension(record):
    """Save comprehension results to a separate CSV file."""
    fields = [
        "timestamp",
        "session_id",
        "scenario_id",
        "company_name",
        "condition",
        "explanation_answer",
        "explanation_correct",
        "uncertainty_answer",
        "uncertainty_correct",
        "total_correct",
        "total_questions"
    ]

    file_exists = COMPREHENSION_FILE.exists()

    with COMPREHENSION_FILE.open(
        mode="a",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)

        if not file_exists:
            writer.writeheader()

        writer.writerow(record)


def get_comprehension_result(session_id, scenario_id):
    """Retrieve the comprehension result for this session and scenario."""
    if not COMPREHENSION_FILE.exists():
        return None

    with COMPREHENSION_FILE.open(
        newline="",
        encoding="utf-8"
    ) as file:
        for row in csv.DictReader(file):
            if (
                row.get("session_id") == session_id
                and row.get("scenario_id") == scenario_id
            ):
                return row

    return None

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


def calculate_comprehension_metrics(records):
    """Calculate comprehension scores and question accuracy."""
    total_submissions = len(records)

    total_correct = sum(
        int(row.get("total_correct") or 0)
        for row in records
    )

    total_questions = sum(
        int(row.get("total_questions") or 0)
        for row in records
    )

    explanation_answers = [
        row for row in records
        if row.get("explanation_correct") in ["True", "False"]
    ]

    explanation_correct = sum(
        1 for row in explanation_answers
        if row["explanation_correct"] == "True"
    )

    uncertainty_answers = [
        row for row in records
        if row.get("uncertainty_correct") in ["True", "False"]
    ]

    uncertainty_correct = sum(
        1 for row in uncertainty_answers
        if row["uncertainty_correct"] == "True"
    )

    return {
        "total_submissions": total_submissions,
        "total_correct": total_correct,
        "total_questions": total_questions,
        "average_score": round(
            total_correct / total_questions * 100, 1
        ) if total_questions else 0,
        "explanation_correct": explanation_correct,
        "explanation_total": len(explanation_answers),
        "explanation_accuracy": round(
            explanation_correct / len(explanation_answers) * 100, 1
        ) if explanation_answers else None,
        "uncertainty_correct": uncertainty_correct,
        "uncertainty_total": len(uncertainty_answers),
        "uncertainty_accuracy": round(
            uncertainty_correct / len(uncertainty_answers) * 100, 1
        ) if uncertainty_answers else None
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


@app.route("/personalise/<scenario_id>", methods=["POST"])
def submit_preferences(scenario_id):
    find_scenario(scenario_id)
    get_condition()

    investment_horizon = request.form.get(
        "investment_horizon", ""
    )

    risk_tolerance = request.form.get(
        "risk_tolerance", ""
    )

    investment_priority = request.form.get(
        "investment_priority", ""
    )

    if investment_horizon not in ["short", "medium", "long"]:
        abort(400, description="Invalid investment horizon.")

    if risk_tolerance not in ["low", "medium", "high"]:
        abort(400, description="Invalid risk tolerance.")

    if investment_priority not in [
        "growth", "stability", "balanced"
    ]:
        abort(400, description="Invalid investment priority.")

    preferences = {
        "investment_horizon": investment_horizon,
        "risk_tolerance": risk_tolerance,
        "investment_priority": investment_priority
    }

    session.setdefault("investment_preferences", {})
    session["investment_preferences"][scenario_id] = preferences
    session.modified = True

    return redirect(
        url_for("recommendation", scenario_id=scenario_id)
    )




@app.route("/recommendation/<scenario_id>")
def recommendation(scenario_id):
    scenario = find_scenario(scenario_id)
    condition = get_condition()

    recommendation_result = generate_recommendation(scenario)
    explanation = generate_explanation(scenario)
    uncertainty = get_uncertainty(scenario)

    preferences = session.get(
        "investment_preferences", {}
    ).get(scenario_id)

    preference_insight = (
        generate_preference_insight(scenario, preferences)
        if preferences else None
    )

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
        ),
        comprehension_result=get_comprehension_result(
            session.get("session_id"),
            scenario_id
        ),
        comprehension_submitted=(
            request.args.get("comprehension_submitted") == "1"
        ),
        comprehension_already_submitted=(
            request.args.get("comprehension_already_submitted") == "1"
        ),
        preferences=preferences,
        preference_insight=preference_insight,
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


@app.route("/comprehension/<scenario_id>", methods=["POST"])
def submit_comprehension(scenario_id):
    scenario = find_scenario(scenario_id)
    condition = get_condition()
    session_id = session["session_id"]

    # Prevent duplicate comprehension submissions.
    if comprehension_already_exists(session_id, scenario_id):
        return redirect(
            url_for(
                "recommendation",
                scenario_id=scenario_id,
                comprehension_already_submitted=1
            )
        )

    explanation_answer = request.form.get(
        "explanation_answer", ""
    )

    uncertainty_answer = request.form.get(
        "uncertainty_answer", ""
    )

    # Validate the explanation question.
    if explanation_answer not in [
        "recommendation_only",
        "evidence_and_risks",
        "positive_factors_only"
    ]:
        abort(400, description="Please answer the explanation question.")

    explanation_correct = (
        explanation_answer == "evidence_and_risks"
    )

    # The uncertainty question is only available in condition B.
    if condition == "explanation_uncertainty":
        if uncertainty_answer not in [
            "guaranteed",
            "prototype_estimate",
            "future_performance"
        ]:
            abort(400, description="Please answer the uncertainty question.")

        uncertainty_correct = (
            uncertainty_answer == "prototype_estimate"
        )

        total_questions = 2

    else:
        uncertainty_answer = ""
        uncertainty_correct = ""
        total_questions = 1

    total_correct = int(explanation_correct)

    if condition == "explanation_uncertainty":
        total_correct += int(uncertainty_correct)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "scenario_id": scenario["scenario_id"],
        "company_name": scenario["company_name"],
        "condition": condition,
        "explanation_answer": explanation_answer,
        "explanation_correct": explanation_correct,
        "uncertainty_answer": uncertainty_answer,
        "uncertainty_correct": uncertainty_correct,
        "total_correct": total_correct,
        "total_questions": total_questions
    }

    save_comprehension(record)

    return redirect(
        url_for(
            "recommendation",
            scenario_id=scenario_id,
            comprehension_submitted=1
        )
    )



@app.route("/evaluation")
def evaluation():
    # Load investment decision records.
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

    # Load comprehension records.
    if not COMPREHENSION_FILE.exists():
        comprehension_records = []
    else:
        with COMPREHENSION_FILE.open(
            newline="",
            encoding="utf-8"
        ) as file:
            comprehension_records = list(csv.DictReader(file))

    # Keep only records from the two experimental conditions.
    comprehension_records = [
        row for row in comprehension_records
        if row.get("condition") in CONDITIONS
    ]

    comprehension_explanation_only = [
        row for row in comprehension_records
        if row["condition"] == "explanation_only"
    ]

    comprehension_explanation_uncertainty = [
        row for row in comprehension_records
        if row["condition"] == "explanation_uncertainty"
    ]

    return render_template(
        "evaluation.html",

        overall=calculate_metrics(experimental_records),

        explanation_only=calculate_metrics(explanation_only),

        explanation_uncertainty=calculate_metrics(
            explanation_uncertainty
        ),

        comprehension=calculate_comprehension_metrics(
            comprehension_records
        ),

        comprehension_explanation_only=(
            calculate_comprehension_metrics(
                comprehension_explanation_only
            )
        ),

        comprehension_explanation_uncertainty=(
            calculate_comprehension_metrics(
                comprehension_explanation_uncertainty
            )
        ),

        total_records=len(records),

        excluded_records=(
            len(records) - len(experimental_records)
        )
    )


if __name__ == "__main__":
    app.run(debug=True)
