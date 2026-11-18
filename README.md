# Airbnb Singapore web dashboard

Three interactive pages backed by the user-exported Gold analytical base, snapshot 2026-09-23. 3,208 listing rows. Public release authorized by the owner in this session.

Serve this directory over HTTP. The HTML loads its adjacent content-addressed snapshot JSON. GitHub Pages uses branch gh-pages, folder / (root).

Valid prices require SGD, verified flag 1, and price > 0. Median, P25 and P75 are recomputed from listing rows with linear interpolation. Available nights ratio = summed available / summed calendar nights. Ratings use an unweighted listing-level mean for values in [1,5]. Private room share uses the currently filtered listing population. Median review count includes zeros.

Validated totals: 3,208 listings, 2,725 valid prices, median SGD 202.83, 900,960 / 1,170,950 available nights, 1,839 rated listings, and 46,000 historical review records. Central Private room median SGD 147.48 (n=1,237). Shared room median review count 7.5.

Includes analytical columns only, omitting host names, listing names, URLs and coordinates. Refresh requires a new Gold export and rebuild.
