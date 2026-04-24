-- demo user
insert into user (username, email)
values ('sam', 'sam@test.com');


-- workouts
insert into workout (user_id, name, description)
values
(1, 'push', 'chest shoulders triceps'),
(1, 'pull', 'back biceps'),
(1, 'legs', 'leg day');


-- push day
insert into workout_exercise (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
values
(1, 1, 3, 8, 135, 'lbs', 1),
(1, 2, 3, 10, 70, 'lbs', 2),
(1, 13, 3, 10, 50, 'lbs', 3),
(1, 28, 3, 12, 35, 'lbs', 4);


-- pull day
insert into workout_exercise (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
values
(2, 9, 3, 8, 155, 'lbs', 1),
(2, 8, 3, 10, 120, 'lbs', 2),
(2, 23, 3, 10, 25, 'lbs', 3),
(2, 7, 2, 8, 0, 'bodyweight', 4);


-- legs
insert into workout_exercise (workout_id, exercise_id, sets, reps, weight, weight_metric, order_index)
values
(3, 46, 4, 6, 185, 'lbs', 1),
(3, 50, 3, 8, 135, 'lbs', 2),
(3, 47, 3, 12, 200, 'lbs', 3),
(3, 51, 3, 15, 90, 'lbs', 4);
