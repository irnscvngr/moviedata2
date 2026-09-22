SELECT
a.*,
b.duration
FROM letterboxd.ratings a
LEFT JOIN letterboxd.lb_all_movies_metadata b
ON a.letterboxd_uri = b.letterboxd_uri
WHERE rating >= 4
AND duration < 130
ORDER by rating DESC, duration ASC
