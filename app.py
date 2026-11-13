
from pathlib import Path

import pandas as pd
from flask import Flask, render_template, abort

app = Flask(__name__)

DATA_FILE = Path(__file__).parent / "scenarios.csv"


def load_scenarios():
    """Load the investment scenarios from the CSV file."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {DATA_FILE.name}. "
            "Place it in the same folder as app.py."
        )

    return pd.read_csv(DATA_FILE).fillna("")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/scenarios")
def scenarios():
    data = load_scenarios()
    scenario_list = data.to_dict(orient="records")

    return render_template(
        "scenarios.html",
        scenarios=scenario_list
    )


@app.route("/scenario/<scenario_id>")
def scenario_detail(scenario_id):
    data = load_scenarios()

    selected = data[data["scenario_id"] == scenario_id]

    if selected.empty:
        abort(404)

    scenario = selected.iloc[0].to_dict()

    return render_template(
        "scenario_detail.html",
        scenario=scenario
    )


if __name__ == "__main__":
    app.run(debug=True)
