-- SELECT * FROM medimops.movie_price_lines

-- CREATE OR REPLACE VIEW
-- medimops.product_price_comparison
-- AS
WITH
date_bounds AS (
    SELECT 
        CURRENT_DATE AS today,
        CURRENT_DATE - INTERVAL '30 days' AS four_weeks_ago
),
ranked_prices AS (
    SELECT 
        p.letterboxd_uri,
        p.price_desktop_min,
        p.date,
        -- Find the single most recent price up to today
        ROW_NUMBER() OVER (
            PARTITION BY p.letterboxd_uri 
            ORDER BY p.date DESC
        ) AS rn
    FROM medimops.movie_price_lines p
    CROSS JOIN date_bounds b
    WHERE p.date <= b.today
),
aggregated_metrics AS (
    SELECT 
        p.letterboxd_uri,
		p.letterboxd_name,
        -- Get the price from the most recent row
        MAX(CASE WHEN r.rn = 1 THEN p.price_desktop_min END) AS current_price,
        MAX(CASE WHEN r.rn = 1 THEN p.date END) AS most_recent_date,
        -- Get the 4-week average price
        AVG(p.price_desktop_min) AS avg_price_4w
    FROM medimops.movie_price_lines p
    CROSS JOIN date_bounds b
    LEFT JOIN ranked_prices r 
        ON p.letterboxd_uri = r.letterboxd_uri 
       AND p.date = r.date 
       AND r.rn = 1
    WHERE p.date BETWEEN b.four_weeks_ago AND b.today
    GROUP BY p.letterboxd_uri, p.letterboxd_name
)
SELECT 
	letterboxd_name,
    letterboxd_uri,
    most_recent_date,
    current_price,
    ROUND(avg_price_4w::numeric, 2) AS avg_price_4w,
    -- Ratio = Current Price / 4-Week Average
    ROUND((current_price::numeric / NULLIF(avg_price_4w, 0)::numeric), 4) AS price_to_4w_avg_ratio
FROM aggregated_metrics
ORDER BY price_to_4w_avg_ratio;