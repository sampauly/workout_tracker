-- reset all non-catalog tables and restart sequences at 1
TRUNCATE TABLE workout_exercise, workout, "user" RESTART IDENTITY CASCADE;

-- set up user, change to desired username 
INSERT INTO "user" (username, email)
VALUES 
    ('YOUR_NAME', 'YOU@YOUR_EMAIL.COM');
