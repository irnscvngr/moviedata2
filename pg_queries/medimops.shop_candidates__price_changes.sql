SELECT STDDEV(price_desktop) AS std_price, letterboxd_uri, title
FROM medimops.shop_candidates
GROUP BY title, rank, letterboxd_uri
HAVING STDDEV(price_desktop) IS NOT NULL
AND STDDEV(price_desktop) != 0