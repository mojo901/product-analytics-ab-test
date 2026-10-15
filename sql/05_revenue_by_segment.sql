-- Выручка и ключевые метрики по каналам привлечения и платформам.
-- Помогает понять, какие сегменты приносят ценных пользователей.

WITH user_rev AS (
    SELECT u.user_id,
           u.source,
           u.platform,
           COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END)          AS orders,
           COALESCE(SUM(CASE WHEN e.event_type = 'purchase' THEN e.revenue END), 0) AS revenue
    FROM users u
    LEFT JOIN events e USING (user_id)
    GROUP BY u.user_id, u.source, u.platform
)
SELECT source,
       platform,
       COUNT(*)                                                   AS users,
       ROUND(100.0 * AVG(orders > 0), 1)                          AS paying_share_pct,
       SUM(orders)                                                AS orders,
       ROUND(SUM(revenue), 0)                                     AS revenue,
       ROUND(SUM(revenue) / COUNT(*), 1)                          AS arpu,
       ROUND(SUM(revenue) / NULLIF(SUM(orders), 0), 1)            AS aov
FROM user_rev
WHERE platform <> 'unknown'
GROUP BY source, platform
ORDER BY arpu DESC;
