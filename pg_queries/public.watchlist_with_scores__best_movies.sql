SELECT * FROM public.watchlist_with_scores
WHERE letterboxd_rating >= 3.5
AND critics_score >= 75
AND audience_score >= 75
AND duration < 100
ORDER BY letterboxd_rating*critics_score*audience_score/duration DESC