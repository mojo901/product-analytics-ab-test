-- DAU по дням, MAU по месяцам и Sticky Factor (средний DAU / MAU)
-- Активный пользователь = открыл приложение (app_open) в этот день.

WITH daily AS (
    SELECT DATE(event_time)         AS day,
           COUNT(DISTINCT user_id)  AS dau
    FROM events
    WHERE event_type = 'app_open'
    GROUP BY DATE(event_time)
),
monthly AS (
    SELECT STRFTIME('%Y-%m', event_time) AS month,
           COUNT(DISTINCT user_id)       AS mau
    FROM events
    WHERE event_type = 'app_open'
    GROUP BY STRFTIME('%Y-%m', event_time)
)
SELECT m.month,
       m.mau,
       ROUND(AVG(d.dau), 0)                 AS avg_dau,
       ROUND(AVG(d.dau) * 100.0 / m.mau, 1) AS sticky_factor_pct
FROM monthly m
JOIN daily d ON STRFTIME('%Y-%m', d.day) = m.month
GROUP BY m.month, m.mau
ORDER BY m.month;
