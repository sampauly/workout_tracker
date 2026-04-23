from flask import render_template
from app.db import connect_db,check_db
from app import app

@app.route('/')
@app.route('/index')
def index():
    check_db()
    # Temp data for testing
    workouts = [
        {
            "date": "2026-04-23",
            "exercise": "Bench Press",
            "sets": 3,
            "reps": 8,
            "weight": 185,
            "notes": "Felt solid",
        },
        {
            "date": "2026-04-22",
            "exercise": "Squat",
            "sets": 5,
            "reps": 5,
            "weight": 225,
            "notes": "",
        },
    ]

    return render_template("index.html", workouts=workouts)