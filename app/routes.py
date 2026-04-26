from flask import render_template, session, redirect, url_for, request, flash
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


@app.route('/exercises')
def exercises():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    muscle_group = request.args.get('muscle_group')
    equipment = request.args.get('equipment')

    if muscle_group and equipment:
        cur.execute(
            'SELECT exercise_id, name, muscle_group, equipment FROM exercise WHERE muscle_group ILIKE %s AND equipment ILIKE %s ORDER BY name',
            (f'%{muscle_group}%', f'%{equipment}%')
        )
    elif muscle_group:
        cur.execute(
            'SELECT exercise_id, name, muscle_group, equipment FROM exercise WHERE muscle_group ILIKE %s ORDER BY name',
            (f'%{muscle_group}%',)
        )
    elif equipment:
        cur.execute(
            'SELECT exercise_id, name, muscle_group, equipment FROM exercise WHERE equipment ILIKE %s ORDER BY name',
            (f'%{equipment}%',)
        )
    else:
        cur.execute(
            'SELECT exercise_id, name, muscle_group, equipment FROM exercise ORDER BY name'
        )

    exercises = cur.fetchall()
    cur.close()

    return render_template('exercises.html', exercises=exercises)



@app.route('/workouts/new', methods=['GET', 'POST'])
def new_workout():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    submitted = None
    errors = {}
    row_errors = []

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

    return render_template('new_workout.html', submitted=submitted, errors=errors, row_errors=row_errors)
