-- Метрики A/B-теста нового экрана оформления заказа.
-- Окно наблюдения: первые 14 дней после регистрации каждого участника.

WITH participants AS (
    SELECT ab.user_id,
           ab.ab_group,
           u.registration_time
    FROM ab_groups ab
    JOIN users u USING (user_id)
),
user_metrics AS (
    SELECT p.user_id,
           p.ab_group,
           MAX(e.event_type = 'checkout')                                   AS reached_checkout,
           MAX(e.event_type = 'purchase')                                   AS purchased,
           COALESCE(SUM(CASE WHEN e.event_type = 'purchase' THEN e.revenue END), 0) AS revenue
    FROM participants p
    LEFT JOIN events e
           ON e.user_id = p.user_id
          AND e.event_time <  DATETIME(p.registration_time, '+14 days')
    GROUP BY p.user_id, p.ab_group
)
SELECT ab_group,
       COUNT(*)                                                        AS users,
       SUM(purchased)                                                  AS buyers,
       ROUND(100.0 * AVG(purchased), 2)                                AS conversion_pct,
       ROUND(100.0 * SUM(purchased) / NULLIF(SUM(reached_checkout), 0), 2) AS checkout_to_purchase_pct,
       ROUND(AVG(revenue), 2)                                          AS arpu,
       ROUND(SUM(revenue) / NULLIF(SUM(purchased), 0), 2)              AS arppu
FROM user_metrics
GROUP BY ab_group
ORDER BY ab_group;
