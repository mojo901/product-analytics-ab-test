-- Продуктовая воронка по уникальным пользователям за весь период:
-- открыл приложение -> смотрел товар -> добавил в корзину -> оформление -> покупка

WITH steps AS (
    SELECT user_id,
           MAX(event_type = 'app_open')     AS opened,
           MAX(event_type = 'view_product') AS viewed,
           MAX(event_type = 'add_to_cart')  AS carted,
           MAX(event_type = 'checkout')     AS checked_out,
           MAX(event_type = 'purchase')     AS purchased
    FROM events
    GROUP BY user_id
),
funnel AS (
    SELECT 1 AS step_no, 'app_open'     AS step, SUM(opened)      AS users FROM steps UNION ALL
    SELECT 2,            'view_product',          SUM(viewed)              FROM steps UNION ALL
    SELECT 3,            'add_to_cart',           SUM(carted)              FROM steps UNION ALL
    SELECT 4,            'checkout',              SUM(checked_out)         FROM steps UNION ALL
    SELECT 5,            'purchase',              SUM(purchased)           FROM steps
)
SELECT step_no,
       step,
       users,
       ROUND(users * 100.0 / FIRST_VALUE(users) OVER (ORDER BY step_no), 1) AS conv_from_start_pct,
       ROUND(users * 100.0 / LAG(users) OVER (ORDER BY step_no), 1)         AS conv_from_prev_pct
FROM funnel
ORDER BY step_no;
