SELECT 
    a.title,
    a.year AS year_choices,
    b.year AS year_tmdb,
    b.year_difference
FROM "1_bronze"."choics__current_movies" a
LEFT JOIN LATERAL (
    SELECT 
        EXTRACT(year FROM b.release_date) AS "year",
        ABS(a.year - EXTRACT(year FROM b.release_date)) AS year_difference
    FROM "1_bronze"."tmdb__movie_details" b
    WHERE b.title_german = a.title
    ORDER BY ABS(a.year - EXTRACT(year FROM b.release_date)) ASC
    LIMIT 1
) b ON true
ORDER BY year_difference DESC