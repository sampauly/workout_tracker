-- reset all non-catalog tables and restart sequences at 1
TRUNCATE TABLE session_exercise, workout_session, workout_exercise, workout, "user" RESTART IDENTITY CASCADE;

-- user
INSERT INTO "user" (username, email)
VALUES 
    ('sam', 'sam@test.com'),
    ('aiden', 'aiden@test.com'),
    ('zachary', 'zachary@test.com');

-- workouts
INSERT INTO workout (user_id, name, description)
SELECT user_id, v.name, v.description
FROM "user", (VALUES
    ('push', 'chest shoulders triceps'),
    ('pull', 'back biceps'),
    ('legs', 'leg day')
) AS v(name, description)
WHERE "user".username = 'aiden';

-- push day
INSERT INTO workout_exercise (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
VALUES
    ((SELECT workout_id FROM workout WHERE name = 'push'), 1,  3, 8,  135, 'lbs',        1),
    ((SELECT workout_id FROM workout WHERE name = 'push'), 2,  3, 10,  70, 'lbs',        2),
    ((SELECT workout_id FROM workout WHERE name = 'push'), 13, 3, 10,  50, 'lbs',        3),
    ((SELECT workout_id FROM workout WHERE name = 'push'), 28, 3, 12,  35, 'lbs',        4);

-- pull day
INSERT INTO workout_exercise (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
VALUES
    ((SELECT workout_id FROM workout WHERE name = 'pull'), 9,  3, 8,  155, 'lbs',        1),
    ((SELECT workout_id FROM workout WHERE name = 'pull'), 8,  3, 10, 120, 'lbs',        2),
    ((SELECT workout_id FROM workout WHERE name = 'pull'), 23, 3, 10,  25, 'lbs',        3),
    ((SELECT workout_id FROM workout WHERE name = 'pull'), 7,  2, 8,    0, 'bodyweight', 4);

-- legs
INSERT INTO workout_exercise (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
VALUES
    ((SELECT workout_id FROM workout WHERE name = 'legs'), 46, 4, 6,  185, 'lbs',        1),
    ((SELECT workout_id FROM workout WHERE name = 'legs'), 50, 3, 8,  135, 'lbs',        2),
    ((SELECT workout_id FROM workout WHERE name = 'legs'), 47, 3, 12, 200, 'lbs',        3),
    ((SELECT workout_id FROM workout WHERE name = 'legs'), 51, 3, 15,  90, 'lbs',        4);
