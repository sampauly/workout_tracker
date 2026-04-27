from flask import render_template, session, redirect, url_for, request, flash
from datetime import datetime, timezone
import math
import random
from app.db import get_db
from app import app


@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        cur.execute('SELECT user_id, username FROM "user" WHERE user_id = %s', (user_id,))
        user = cur.fetchone()
        cur.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
        flash('User not found.', 'danger')
        return redirect(url_for('login'))

    cur.execute('SELECT user_id, username, email FROM "user" ORDER BY username')
    users = cur.fetchall()
    cur.close()
    return render_template('login.html', users=users)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM workout WHERE user_id = %s', (session['user_id'],))
    workout_count = cur.fetchone()[0]
    cur.close()
    return render_template('dashboard.html', workout_count=workout_count)


@app.route('/exercises', methods=['GET', 'POST'])
def exercises():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    add_errors = {}

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        muscle_group = (request.form.get('muscle_group') or '').strip()
        equipment = (request.form.get('equipment') or '').strip()

        if not name:
            add_errors['name'] = 'Exercise name is required.'
        elif len(name) > 100:
            add_errors['name'] = 'Max 100 characters.'

        if not add_errors:
            cur.execute(
                'INSERT INTO exercise (name, muscle_group, equipment) VALUES (%s, %s, %s)',
                (name, muscle_group or None, equipment or None),
            )
            conn.commit()
            cur.close()
            flash(f'"{name}" added to the catalog.', 'success')
            return redirect(url_for('exercises'))

    muscle_group_filter = request.args.get('muscle_group')
    equipment_filter = request.args.get('equipment')

    if muscle_group_filter and equipment_filter:
        cur.execute(
            'SELECT exercise_id, name, muscle_group, equipment FROM exercise WHERE muscle_group ILIKE %s AND equipment ILIKE %s ORDER BY name',
            (f'%{muscle_group_filter}%', f'%{equipment_filter}%')
        )
    elif muscle_group_filter:
        cur.execute(
            'SELECT exercise_id, name, muscle_group, equipment FROM exercise WHERE muscle_group ILIKE %s ORDER BY name',
            (f'%{muscle_group_filter}%',)
        )
    elif equipment_filter:
        cur.execute(
            'SELECT exercise_id, name, muscle_group, equipment FROM exercise WHERE equipment ILIKE %s ORDER BY name',
            (f'%{equipment_filter}%',)
        )
    else:
        cur.execute('SELECT exercise_id, name, muscle_group, equipment FROM exercise ORDER BY name')

    exercises = cur.fetchall()
    cur.close()

    return render_template('exercises.html', exercises=exercises, add_errors=add_errors,
                           add_form={'name': request.form.get('name', ''),
                                     'muscle_group': request.form.get('muscle_group', ''),
                                     'equipment': request.form.get('equipment', '')} if add_errors else None)



@app.route('/stats')
def stats():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    conn = get_db()
    cur = conn.cursor()

    # Aggregate: total workouts + average exercises per workout
    cur.execute(
        """
        SELECT
            COUNT(DISTINCT w.workout_id)          AS total_workouts,
            ROUND(AVG(sub.cnt)::numeric, 1)       AS avg_exercises
        FROM workout w
        LEFT JOIN (
            SELECT workout_id, COUNT(*) AS cnt
            FROM workout_exercise
            GROUP BY workout_id
        ) sub ON sub.workout_id = w.workout_id
        WHERE w.user_id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    total_workouts = row[0] or 0
    avg_exercises = row[1] or 0

    # Join + aggregate: top 5 heaviest planned lifts
    cur.execute(
        """
        SELECT
            e.name,
            e.muscle_group,
            MAX(we.weight)   AS max_weight,
            we.weight_metric
        FROM workout_exercise we
        JOIN workout  w ON w.workout_id  = we.workout_id
        JOIN exercise e ON e.exercise_id = we.exercise_id
        WHERE w.user_id = %s
          AND we.weight IS NOT NULL
          AND we.weight > 0
        GROUP BY e.name, e.muscle_group, we.weight_metric
        ORDER BY max_weight DESC
        LIMIT 5
        """,
        (user_id,),
    )
    top_lifts = [
        {'name': r[0], 'muscle_group': r[1], 'max_weight': r[2], 'weight_metric': r[3]}
        for r in cur.fetchall()
    ]

    # Join + aggregate: most trained muscle groups
    cur.execute(
        """
        SELECT
            e.muscle_group,
            COUNT(*) AS times_trained
        FROM workout_exercise we
        JOIN workout  w ON w.workout_id  = we.workout_id
        JOIN exercise e ON e.exercise_id = we.exercise_id
        WHERE w.user_id = %s
          AND e.muscle_group IS NOT NULL
          AND BTRIM(e.muscle_group) <> ''
        GROUP BY e.muscle_group
        ORDER BY times_trained DESC
        """,
        (user_id,),
    )
    muscle_groups = [
        {'muscle_group': r[0], 'times_trained': r[1]}
        for r in cur.fetchall()
    ]
    cur.close()

    return render_template(
        'stats.html',
        total_workouts=total_workouts,
        avg_exercises=avg_exercises,
        top_lifts=top_lifts,
        muscle_groups=muscle_groups,
    )


@app.route('/workouts/new', methods=['GET', 'POST'])
def new_workout():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    submitted = None
    errors = {}
    row_errors = []

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT exercise_id, name, muscle_group FROM exercise ORDER BY name')
    exercise_catalog = [{'exercise_id': r[0], 'name': r[1], 'muscle_group': r[2]} for r in cur.fetchall()]
    cur.close()

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        description = (request.form.get('description') or '').strip()

        exercise_ids = request.form.getlist('exercise_id')
        sets_list = request.form.getlist('sets')
        reps_list = request.form.getlist('reps')
        weight_list = request.form.getlist('weight')
        weight_metric_list = request.form.getlist('weight_metric')
        order_index_list = request.form.getlist('order_index')

        if not name:
            errors['name'] = 'Workout name is required.'
        elif len(name) > 100:
            errors['name'] = 'Workout name must be 100 characters or less.'

        if description and len(description) > 2000:
            errors['description'] = 'Description must be 2000 characters or less.'

        # Validate exercise rows (workout_exercise schema)
        rows = []
        max_len = max(
            len(exercise_ids),
            len(sets_list),
            len(reps_list),
            len(weight_list),
            len(weight_metric_list),
            len(order_index_list),
        )

        def _get(lst, idx):
            return (lst[idx] if idx < len(lst) else '') or ''

        allowed_metrics = {'kg', 'lb', ''}

        for i in range(max_len):
            row_err = {}

            exercise_id_raw = _get(exercise_ids, i).strip()
            sets_raw = _get(sets_list, i).strip()
            reps_raw = _get(reps_list, i).strip()
            weight_raw = _get(weight_list, i).strip()
            weight_metric_raw = _get(weight_metric_list, i).strip().lower()
            order_index_raw = _get(order_index_list, i).strip()

            # Allow completely blank rows (e.g. if the UI leaves one behind)
            if not any([exercise_id_raw, sets_raw, reps_raw, weight_raw, weight_metric_raw, order_index_raw]):
                continue

            exercise_id = None
            try:
                exercise_id = int(exercise_id_raw)
                if exercise_id <= 0:
                    row_err['exercise_id'] = 'Must be a positive integer.'
            except ValueError:
                row_err['exercise_id'] = 'Exercise ID must be an integer.'

            sets_val = None
            try:
                sets_val = int(sets_raw)
                if sets_val <= 0:
                    row_err['sets'] = 'Sets must be a positive integer.'
            except ValueError:
                row_err['sets'] = 'Sets must be an integer.'

            reps_val = None
            try:
                reps_val = int(reps_raw)
                if reps_val <= 0:
                    row_err['reps'] = 'Reps must be a positive integer.'
            except ValueError:
                row_err['reps'] = 'Reps must be an integer.'

            weight_val = None
            if weight_raw:
                try:
                    weight_val = float(weight_raw)
                    if weight_val < 0:
                        row_err['weight'] = 'Weight cannot be negative.'
                except ValueError:
                    row_err['weight'] = 'Weight must be a number.'

            if weight_metric_raw not in allowed_metrics:
                row_err['weight_metric'] = 'Use kg or lb.'

            # Default to lb if the user entered a weight but left the metric blank.
            if weight_val is not None and not weight_metric_raw:
                weight_metric_raw = 'lb'

            order_index = i + 1
            if order_index_raw:
                try:
                    order_index = int(order_index_raw)
                    if order_index <= 0:
                        row_err['order_index'] = 'Order index must be a positive integer.'
                except ValueError:
                    row_err['order_index'] = 'Order index must be an integer.'

            rows.append(
                {
                    'exercise_id': exercise_id_raw,
                    'sets': sets_raw,
                    'reps': reps_raw,
                    'weight': weight_raw,
                    'weight_metric': weight_metric_raw,
                    'order_index': order_index_raw or str(order_index),
                }
            )
            row_errors.append(row_err)

        if not rows:
            errors['exercises'] = 'Add at least one exercise.'

        submitted = {
            'user_id': session.get('user_id'),
            'name': name,
            'description': description,
            'exercises': rows,
        }

        if not errors and any(bool(re) for re in row_errors):
            errors['exercises'] = 'Fix exercise row errors.'

        if not errors:
            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO workout (user_id, name, description)
                    VALUES (%s, %s, %s)
                    RETURNING workout_id
                    """,
                    (session.get('user_id'), name, (description or None)),
                )
                workout_id = cur.fetchone()[0]

                for ex in rows:
                    cur.execute(
                        """
                        INSERT INTO workout_exercise
                          (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
                        VALUES
                          (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            workout_id,
                            int(ex['exercise_id']),
                            int(ex['sets']),
                            int(ex['reps']),
                            (float(ex['weight']) if ex['weight'] else None),
                            (ex['weight_metric'] or None),
                            int(ex['order_index']) if ex['order_index'] else None,
                        ),
                    )

                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

            flash('Workout saved.', 'success')
            return redirect(url_for('dashboard'))

    return render_template('new_workout.html', submitted=submitted, errors=errors, row_errors=row_errors, exercise_catalog=exercise_catalog)


@app.route('/workouts')
def workouts():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
          w.workout_id,
          w.name,
          w.description,
          w.created_at,
          COUNT(we.exercise_id) AS exercise_count
        FROM workout w
        LEFT JOIN workout_exercise we ON we.workout_id = w.workout_id
        WHERE w.user_id = %s
        GROUP BY w.workout_id
        ORDER BY w.created_at DESC, w.workout_id DESC
        """,
        (session.get('user_id'),),
    )
    rows = cur.fetchall()
    cur.close()

    workouts = [
        {
            'workout_id': r[0],
            'name': r[1],
            'description': r[2],
            'created_at': r[3],
            'exercise_count': r[4],
        }
        for r in rows
    ]

    return render_template('workouts.html', workouts=workouts)


@app.route('/workouts/<int:workout_id>/edit', methods=['GET', 'POST'])
def edit_workout(workout_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    submitted = None
    errors = {}
    row_errors = []

    conn = get_db()
    cur = conn.cursor()

    cur.execute('SELECT exercise_id, name, muscle_group FROM exercise ORDER BY name')
    exercise_catalog = [{'exercise_id': r[0], 'name': r[1], 'muscle_group': r[2]} for r in cur.fetchall()]

    cur.execute(
        """
        SELECT workout_id, user_id, name, description
        FROM workout
        WHERE workout_id = %s
        """,
        (workout_id,),
    )
    w = cur.fetchone()
    if not w or w[1] != session.get('user_id'):
        cur.close()
        flash('Workout not found.', 'danger')
        return redirect(url_for('workouts'))

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        description = (request.form.get('description') or '').strip()

        exercise_ids = request.form.getlist('exercise_id')
        sets_list = request.form.getlist('sets')
        reps_list = request.form.getlist('reps')
        weight_list = request.form.getlist('weight')
        weight_metric_list = request.form.getlist('weight_metric')
        order_index_list = request.form.getlist('order_index')

        if not name:
            errors['name'] = 'Workout name is required.'
        elif len(name) > 100:
            errors['name'] = 'Workout name must be 100 characters or less.'

        if description and len(description) > 2000:
            errors['description'] = 'Description must be 2000 characters or less.'

        rows = []
        max_len = max(
            len(exercise_ids),
            len(sets_list),
            len(reps_list),
            len(weight_list),
            len(weight_metric_list),
            len(order_index_list),
        )

        def _get(lst, idx):
            return (lst[idx] if idx < len(lst) else '') or ''

        allowed_metrics = {'kg', 'lb', ''}

        for i in range(max_len):
            row_err = {}

            exercise_id_raw = _get(exercise_ids, i).strip()
            sets_raw = _get(sets_list, i).strip()
            reps_raw = _get(reps_list, i).strip()
            weight_raw = _get(weight_list, i).strip()
            weight_metric_raw = _get(weight_metric_list, i).strip().lower()
            order_index_raw = _get(order_index_list, i).strip()

            if not any([exercise_id_raw, sets_raw, reps_raw, weight_raw, weight_metric_raw, order_index_raw]):
                continue

            try:
                exercise_id = int(exercise_id_raw)
                if exercise_id <= 0:
                    row_err['exercise_id'] = 'Must be a positive integer.'
            except ValueError:
                row_err['exercise_id'] = 'Exercise ID must be an integer.'

            try:
                sets_val = int(sets_raw)
                if sets_val <= 0:
                    row_err['sets'] = 'Sets must be a positive integer.'
            except ValueError:
                row_err['sets'] = 'Sets must be an integer.'

            try:
                reps_val = int(reps_raw)
                if reps_val <= 0:
                    row_err['reps'] = 'Reps must be a positive integer.'
            except ValueError:
                row_err['reps'] = 'Reps must be an integer.'

            weight_val = None
            if weight_raw:
                try:
                    weight_val = float(weight_raw)
                    if weight_val < 0:
                        row_err['weight'] = 'Weight cannot be negative.'
                except ValueError:
                    row_err['weight'] = 'Weight must be a number.'

            if weight_metric_raw not in allowed_metrics:
                row_err['weight_metric'] = 'Use kg or lb.'

            if weight_val is not None and not weight_metric_raw:
                row_err['weight_metric'] = 'Select kg or lb when weight is provided.'

            order_index = i + 1
            if order_index_raw:
                try:
                    order_index = int(order_index_raw)
                    if order_index <= 0:
                        row_err['order_index'] = 'Order index must be a positive integer.'
                except ValueError:
                    row_err['order_index'] = 'Order index must be an integer.'

            rows.append(
                {
                    'exercise_id': exercise_id_raw,
                    'sets': sets_raw,
                    'reps': reps_raw,
                    'weight': weight_raw,
                    'weight_metric': weight_metric_raw,
                    'order_index': order_index_raw or str(order_index),
                }
            )
            row_errors.append(row_err)

        if not rows:
            errors['exercises'] = 'Add at least one exercise.'

        submitted = {
            'user_id': session.get('user_id'),
            'name': name,
            'description': description,
            'exercises': rows,
        }

        if not errors and any(bool(re) for re in row_errors):
            errors['exercises'] = 'Fix exercise row errors.'

        if not errors:
            try:
                cur.execute(
                    """
                    UPDATE workout
                    SET name = %s, description = %s
                    WHERE workout_id = %s AND user_id = %s
                    """,
                    (name, (description or None), workout_id, session.get('user_id')),
                )

                cur.execute("DELETE FROM workout_exercise WHERE workout_id = %s", (workout_id,))

                for ex in rows:
                    cur.execute(
                        """
                        INSERT INTO workout_exercise
                          (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
                        VALUES
                          (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            workout_id,
                            int(ex['exercise_id']),
                            int(ex['sets']),
                            int(ex['reps']),
                            (float(ex['weight']) if ex['weight'] else None),
                            (ex['weight_metric'] or None),
                            int(ex['order_index']) if ex['order_index'] else None,
                        ),
                    )

                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

            flash('Workout updated.', 'success')
            return redirect(url_for('workouts'))

    # GET (or POST with errors): load existing rows for prefill when not submitted
    cur.execute(
        """
        SELECT exercise_id, sets, reps, weight, weight_metric, order_index
        FROM workout_exercise
        WHERE workout_id = %s
        ORDER BY order_index ASC NULLS LAST, exercise_id ASC
        """,
        (workout_id,),
    )
    ex_rows = cur.fetchall()
    cur.close()

    if submitted is None:
        submitted = {
            'user_id': session.get('user_id'),
            'name': w[2],
            'description': w[3] or '',
            'exercises': [
                {
                    'exercise_id': str(r[0]),
                    'sets': '' if r[1] is None else str(r[1]),
                    'reps': '' if r[2] is None else str(r[2]),
                    'weight': '' if r[3] is None else str(r[3]),
                    'weight_metric': (r[4] or ''),
                    'order_index': '' if r[5] is None else str(r[5]),
                }
                for r in ex_rows
            ]
            or [{'exercise_id': '', 'sets': '', 'reps': '', 'weight': '', 'weight_metric': '', 'order_index': '1'}],
        }

    return render_template(
        'edit_workout.html',
        workout_id=workout_id,
        submitted=submitted,
        errors=errors,
        row_errors=row_errors,
        exercise_catalog=exercise_catalog,
    )


@app.route('/workouts/<int:workout_id>/delete', methods=['POST'])
def delete_workout(workout_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id FROM workout WHERE workout_id = %s",
        (workout_id,),
    )
    w = cur.fetchone()
    if not w or w[0] != session.get('user_id'):
        cur.close()
        flash('Workout not found.', 'danger')
        return redirect(url_for('workouts'))

    try:
        cur.execute("DELETE FROM workout_exercise WHERE workout_id = %s", (workout_id,))
        cur.execute("DELETE FROM workout WHERE workout_id = %s AND user_id = %s", (workout_id, session.get('user_id')))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

    flash('Workout deleted.', 'success')
    return redirect(url_for('workouts'))


@app.route('/recommend', methods=['GET', 'POST'])
def recommend():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    conn = get_db()
    cur = conn.cursor()

    # Ensure a fair calculation: require >5 logged workouts.
    cur.execute("SELECT COUNT(*) FROM workout WHERE user_id = %s", (user_id,))
    workout_count = cur.fetchone()[0] or 0
    if workout_count <= 5:
        cur.close()
        flash('Log at least 6 workouts to get recommendations.', 'warning')
        return redirect(url_for('workouts'))

    # Muscle group stats: recency + total usage (based on workout_exercise history).
    cur.execute(
        """
        SELECT
          e.muscle_group,
          MAX(w.created_at) AS last_trained_at,
          COUNT(*)          AS exercise_entries
        FROM workout w
        JOIN workout_exercise we ON we.workout_id = w.workout_id
        JOIN exercise e ON e.exercise_id = we.exercise_id
        WHERE w.user_id = %s
          AND e.muscle_group IS NOT NULL
          AND BTRIM(e.muscle_group) <> ''
        GROUP BY e.muscle_group
        """,
        (user_id,),
    )
    mg_rows = cur.fetchall()

    # If the user has workouts but none of the exercises have muscle groups set.
    if not mg_rows:
        cur.close()
        flash('Not enough muscle group data on exercises to recommend yet.', 'warning')
        return redirect(url_for('exercises'))

    cur.execute(
        """
        SELECT COUNT(*)
        FROM workout w
        JOIN workout_exercise we ON we.workout_id = w.workout_id
        JOIN exercise e ON e.exercise_id = we.exercise_id
        WHERE w.user_id = %s
          AND e.muscle_group IS NOT NULL
          AND BTRIM(e.muscle_group) <> ''
        """,
        (user_id,),
    )
    total_entries = cur.fetchone()[0] or 0
    total_entries = max(int(total_entries), 1)

    # Avoid recommending exercises from the last 2 workouts when possible.
    cur.execute(
        """
        WITH recent AS (
          SELECT workout_id
          FROM workout
          WHERE user_id = %s
          ORDER BY created_at DESC, workout_id DESC
          LIMIT 2
        )
        SELECT DISTINCT we.exercise_id
        FROM workout_exercise we
        JOIN recent r ON r.workout_id = we.workout_id
        """,
        (user_id,),
    )
    recent_exercise_ids = {r[0] for r in cur.fetchall()}

    now = datetime.now(timezone.utc)
    mg_stats = []
    for muscle_group, last_trained_at, exercise_entries in mg_rows:
        # created_at is typically tz-naive in many setups; treat it as UTC for scoring.
        if last_trained_at is None:
            days_since = 999.0
        else:
            if getattr(last_trained_at, "tzinfo", None) is None:
                last_trained_at = last_trained_at.replace(tzinfo=timezone.utc)
            days_since = max(0.0, (now - last_trained_at).total_seconds() / 86400.0)

        entries = int(exercise_entries or 0)
        freq = entries / total_entries  # 0..1

        # Score increases when it's been longer since trained, and when it's less frequent overall.
        # Recency is capped to reduce huge gaps dominating.
        recency_component = min(days_since, 60.0) / 60.0  # 0..1
        rarity_component = 1.0 - min(max(freq, 0.0), 1.0)  # 0..1
        # Slightly favor recency over rarity to avoid ignoring recovery patterns.
        score = 0.65 * recency_component + 0.35 * rarity_component

        mg_stats.append(
            {
                "muscle_group": muscle_group,
                "last_trained_at": last_trained_at,
                "days_since": days_since,
                "entries": entries,
                "score": score,
            }
        )

    mg_stats.sort(key=lambda x: x["score"], reverse=True)

    # Choose up to 3 target groups, but keep some diversity if scores are clustered.
    top_groups = [m["muscle_group"] for m in mg_stats[:3]]
    if len(top_groups) < 3:
        # Fallback: pad with any remaining groups.
        for m in mg_stats:
            if m["muscle_group"] not in top_groups:
                top_groups.append(m["muscle_group"])
            if len(top_groups) >= 3:
                break

    # Load exercise catalog for search/autocomplete (and for name display).
    cur.execute(
        """
        SELECT exercise_id, name, muscle_group, equipment
        FROM exercise
        ORDER BY name ASC
        """
    )
    exercise_catalog_rows = cur.fetchall()
    exercise_catalog = [
        {"exercise_id": r[0], "name": r[1], "muscle_group": r[2], "equipment": r[3]}
        for r in exercise_catalog_rows
    ]
    exercise_name_by_id = {r[0]: r[1] for r in exercise_catalog_rows}

    # Pull a pool of candidate exercises per group and sample a small set.
    recommended = []
    used_exercise_ids = set()

    def _suggest_sets_reps(exercise_id: int):
        cur.execute(
            """
            SELECT AVG(we.sets)::float, AVG(we.reps)::float
            FROM workout w
            JOIN workout_exercise we ON we.workout_id = w.workout_id
            WHERE w.user_id = %s AND we.exercise_id = %s
            """,
            (user_id, exercise_id),
        )
        avg_sets, avg_reps = cur.fetchone()
        sets_val = int(round(avg_sets)) if avg_sets else 3
        reps_val = int(round(avg_reps)) if avg_reps else 10
        sets_val = min(max(sets_val, 2), 6)
        reps_val = min(max(reps_val, 5), 20)
        return sets_val, reps_val

    for mg in top_groups:
        # Prefer exercises not in recent workouts; if that filters everything out, allow recent ones.
        cur.execute(
            """
            SELECT exercise_id, name, muscle_group, equipment
            FROM exercise
            WHERE muscle_group = %s
            ORDER BY RANDOM()
            LIMIT 20
            """,
            (mg,),
        )
        pool = cur.fetchall()

        # Re-rank the pool with a deterministic-ish shuffle and recent-exclusion preference.
        random.shuffle(pool)
        pool_preferred = [p for p in pool if p[0] not in recent_exercise_ids]
        pool_fallback = [p for p in pool if p[0] in recent_exercise_ids]
        ordered_pool = pool_preferred + pool_fallback

        picked_for_group = 0
        for ex_id, ex_name, ex_mg, ex_equipment in ordered_pool:
            if ex_id in used_exercise_ids:
                continue
            sets_val, reps_val = _suggest_sets_reps(int(ex_id))
            recommended.append(
                {
                    "exercise_id": ex_id,
                    "name": ex_name,
                    "muscle_group": ex_mg,
                    "equipment": ex_equipment,
                    "sets": sets_val,
                    "reps": reps_val,
                }
            )
            used_exercise_ids.add(ex_id)
            picked_for_group += 1
            if picked_for_group >= 2:
                break

    submitted = None
    errors = {}
    row_errors = []

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        description = (request.form.get('description') or '').strip()

        exercise_ids = request.form.getlist('exercise_id')
        exercise_names = request.form.getlist('exercise_name')
        sets_list = request.form.getlist('sets')
        reps_list = request.form.getlist('reps')
        weight_list = request.form.getlist('weight')
        weight_metric_list = request.form.getlist('weight_metric')
        order_index_list = request.form.getlist('order_index')

        if not name:
            errors['name'] = 'Workout name is required.'
        elif len(name) > 100:
            errors['name'] = 'Workout name must be 100 characters or less.'

        if description and len(description) > 2000:
            errors['description'] = 'Description must be 2000 characters or less.'

        rows = []
        max_len = max(
            len(exercise_ids),
            len(exercise_names),
            len(sets_list),
            len(reps_list),
            len(weight_list),
            len(weight_metric_list),
            len(order_index_list),
        )

        def _get(lst, idx):
            return (lst[idx] if idx < len(lst) else '') or ''

        allowed_metrics = {'kg', 'lb', ''}

        for i in range(max_len):
            row_err = {}

            exercise_id_raw = _get(exercise_ids, i).strip()
            exercise_name_raw = _get(exercise_names, i).strip()
            sets_raw = _get(sets_list, i).strip()
            reps_raw = _get(reps_list, i).strip()
            weight_raw = _get(weight_list, i).strip()
            weight_metric_raw = _get(weight_metric_list, i).strip().lower()
            order_index_raw = _get(order_index_list, i).strip()

            # Allow completely blank rows (e.g. if the UI leaves one behind)
            if not any([exercise_id_raw, exercise_name_raw, sets_raw, reps_raw, weight_raw, weight_metric_raw, order_index_raw]):
                continue

            exercise_id = None
            if exercise_id_raw:
                try:
                    exercise_id = int(exercise_id_raw)
                    if exercise_id <= 0:
                        row_err['exercise_id'] = 'Must be a positive integer.'
                except ValueError:
                    row_err['exercise_id'] = 'Exercise ID must be an integer.'
            else:
                # Allow selecting by name (UI should set exercise_id, but we fall back just in case).
                if exercise_name_raw:
                    matches = [
                        ex["exercise_id"]
                        for ex in exercise_catalog
                        if (ex["name"] or "").strip().lower() == exercise_name_raw.strip().lower()
                    ]
                    if len(matches) == 1:
                        exercise_id = int(matches[0])
                        exercise_id_raw = str(exercise_id)
                    else:
                        row_err['exercise_id'] = 'Pick an exercise from search (name must match exactly).'
                else:
                    row_err['exercise_id'] = 'Pick an exercise.'

            sets_val = None
            try:
                sets_val = int(sets_raw)
                if sets_val <= 0:
                    row_err['sets'] = 'Sets must be a positive integer.'
            except ValueError:
                row_err['sets'] = 'Sets must be an integer.'

            reps_val = None
            try:
                reps_val = int(reps_raw)
                if reps_val <= 0:
                    row_err['reps'] = 'Reps must be a positive integer.'
            except ValueError:
                row_err['reps'] = 'Reps must be an integer.'

            weight_val = None
            if weight_raw:
                try:
                    weight_val = float(weight_raw)
                    if weight_val < 0:
                        row_err['weight'] = 'Weight cannot be negative.'
                except ValueError:
                    row_err['weight'] = 'Weight must be a number.'

            if weight_metric_raw not in allowed_metrics:
                row_err['weight_metric'] = 'Use kg or lb.'

            if weight_val is not None and not weight_metric_raw:
                row_err['weight_metric'] = 'Select kg or lb when weight is provided.'

            order_index = i + 1
            if order_index_raw:
                try:
                    order_index = int(order_index_raw)
                    if order_index <= 0:
                        row_err['order_index'] = 'Order index must be a positive integer.'
                except ValueError:
                    row_err['order_index'] = 'Order index must be an integer.'

            rows.append(
                {
                    'exercise_id': exercise_id_raw,
                    'exercise_name': exercise_name_raw,
                    'sets': sets_raw,
                    'reps': reps_raw,
                    'weight': weight_raw,
                    'weight_metric': weight_metric_raw,
                    'order_index': order_index_raw or str(order_index),
                }
            )
            row_errors.append(row_err)

        if not rows:
            errors['exercises'] = 'Add at least one exercise.'

        submitted = {
            'user_id': user_id,
            'name': name,
            'description': description,
            'exercises': rows,
        }

        if not errors and any(bool(re) for re in row_errors):
            errors['exercises'] = 'Fix exercise row errors.'

        # Ensure exercises exist (and belong to the catalog).
        if not errors:
            for ex in rows:
                try:
                    cur.execute("SELECT 1 FROM exercise WHERE exercise_id = %s", (int(ex['exercise_id']),))
                    if cur.fetchone() is None:
                        errors['exercises'] = 'One or more exercise IDs do not exist.'
                        break
                except Exception:
                    errors['exercises'] = 'One or more exercise IDs are invalid.'
                    break

        # Backfill exercise_name for display when POSTing invalid data (or when JS didn't set it).
        if submitted and submitted.get('exercises'):
            for ex in submitted['exercises']:
                if not ex.get('exercise_name') and ex.get('exercise_id'):
                    try:
                        ex_id_int = int(ex['exercise_id'])
                        ex['exercise_name'] = exercise_name_by_id.get(ex_id_int, '')
                    except Exception:
                        pass

        if not errors:
            try:
                cur.execute(
                    """
                    INSERT INTO workout (user_id, name, description)
                    VALUES (%s, %s, %s)
                    RETURNING workout_id
                    """,
                    (user_id, name, (description or None)),
                )
                workout_id = cur.fetchone()[0]

                for ex in rows:
                    cur.execute(
                        """
                        INSERT INTO workout_exercise
                          (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
                        VALUES
                          (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            workout_id,
                            int(ex['exercise_id']),
                            int(ex['sets']),
                            int(ex['reps']),
                            (float(ex['weight']) if ex['weight'] else None),
                            (ex['weight_metric'] or None),
                            int(ex['order_index']) if ex['order_index'] else None,
                        ),
                    )

                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

            flash('Recommended workout logged.', 'success')
            return redirect(url_for('workouts'))

    # GET (or POST with errors): build a default editable "submitted" structure from the recommendation
    if submitted is None:
        submitted = {
            'user_id': user_id,
            'name': 'Recommended workout',
            'description': f"Recommended focus: {', '.join(top_groups)}",
            'exercises': [
                {
                    'exercise_id': str(ex['exercise_id']),
                    'exercise_name': exercise_name_by_id.get(ex['exercise_id'], ex['name']),
                    'sets': str(ex['sets']),
                    'reps': str(ex['reps']),
                    'weight': '',
                    'weight_metric': 'lb',
                    'order_index': str(i + 1),
                }
                for i, ex in enumerate(recommended)
            ]
            or [{'exercise_id': '', 'sets': '', 'reps': '', 'weight': '', 'weight_metric': '', 'order_index': '1'}],
        }

    cur.close()

    # If we somehow couldn't pick anything (e.g. empty exercise catalog), fail gracefully.
    if not recommended and request.method == 'GET':
        flash('No exercises available to recommend yet.', 'warning')
        return redirect(url_for('exercises'))

    return render_template(
        "recommend.html",
        workout_count=workout_count,
        muscle_groups=mg_stats,
        top_groups=top_groups,
        recommended=recommended,
        exercise_catalog=exercise_catalog,
        submitted=submitted,
        errors=errors,
        row_errors=row_errors,
    )
