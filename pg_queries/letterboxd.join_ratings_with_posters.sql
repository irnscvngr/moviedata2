SELECT
a.name,
a.year,
a.letterboxd_uri,
a.rating,
b.duration,
b.genres,
b.poster
FROM letterboxd.ratings a
LEFT JOIN letterboxd.lb_all_movies_metadata b
ON a.letterboxd_uri = b.letterboxd_uri
ORDER BY rating DESC