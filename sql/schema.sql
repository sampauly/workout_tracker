CREATE TABLE "user" (
    user_id     SERIAL PRIMARY KEY,
    username    VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workout (
    workout_id  SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES "user"(user_id),
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE exercise (
    exercise_id  SERIAL PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    muscle_group VARCHAR(100),
    equipment    VARCHAR(100)
);

CREATE TABLE workout_exercise (
    workout_id    INTEGER NOT NULL REFERENCES workout(workout_id),
    exercise_id   INTEGER NOT NULL REFERENCES exercise(exercise_id),
    sets          INTEGER,
    reps          INTEGER,
    weight        FLOAT,
    weight_metric VARCHAR(10),
    order_index   INTEGER,
    PRIMARY KEY (workout_id, exercise_id)
);

CREATE TABLE workout_session (
    session_id   SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES "user"(user_id),
    workout_id   INTEGER NOT NULL REFERENCES workout(workout_id),
    session_date TIMESTAMP NOT NULL
);

CREATE TABLE session_exercise (
    session_exercise_id SERIAL PRIMARY KEY,
    session_id          INTEGER NOT NULL REFERENCES workout_session(session_id),
    exercise_id         INTEGER NOT NULL REFERENCES exercise(exercise_id),
    sets_completed      INTEGER,
    reps_completed      INTEGER,
    weight_used         FLOAT
);
