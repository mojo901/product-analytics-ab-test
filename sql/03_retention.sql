-- Retention 1, 7 и 30 дня по недельным когортам регистрации.
-- Retention N-го дня = доля когорты, открывшей приложение ровно на N-й день после регистрации.
-- Для честного сравнения учитываем только пользователей, у которых этот день уже наступил
-- (последний день наблюдений — 2025-09-30). В последних когортах D30 будет частичным или NULL.

WITH cohort AS (
    SELECT user_id,
           DATE(registration_time)                              AS reg_day,
           DATE(registration_time, '-6 days', 'weekday 1')      AS cohort_week  -- понедельник недели
    FROM users
),
activity AS (
    SELECT DISTINCT e.user_id,
           CAST(JULIANDAY(DATE(e.event_time)) - JULIANDAY(c.reg_day) AS INTEGER) AS day_n
    FROM events e
    JOIN cohort c USING (user_id)
    WHERE e.event_type = 'app_open'
),
per_user AS (
    SELECT c.user_id,
           c.cohort_week,
           c.reg_day,
           MAX(a.day_n = 1)  AS d1,
           MAX(a.day_n = 7)  AS d7,
           MAX(a.day_n = 30) AS d30
    FROM cohort c
    LEFT JOIN activity a USING (user_id)
    GROUP BY c.user_id, c.cohort_week, c.reg_day
)
SELECT cohort_week,
       COUNT(*) AS cohort_size,
       -- метрику считаем только по пользователям, у которых нужный день уже наступил;
       -- если таких в когорте нет совсем, получится NULL
       ROUND(100.0 * AVG(CASE WHEN reg_day <= DATE('2025-09-30', '-1 days')  THEN d1  END), 1) AS retention_d1_pct,
       ROUND(100.0 * AVG(CASE WHEN reg_day <= DATE('2025-09-30', '-7 days')  THEN d7  END), 1) AS retention_d7_pct,
       ROUND(100.0 * AVG(CASE WHEN reg_day <= DATE('2025-09-30', '-30 days') THEN d30 END), 1) AS retention_d30_pct
FROM per_user
GROUP BY cohort_week
ORDER BY cohort_week;
