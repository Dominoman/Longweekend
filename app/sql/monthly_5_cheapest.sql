WITH ranked_by_destination AS (
    SELECT
        *,
        strftime('%Y-%m', local_departure) AS month,
        ROW_NUMBER() OVER (
            PARTITION BY strftime('%Y-%m', local_departure), flyTo
            ORDER BY price ASC
        ) AS dest_rank
    FROM itinerary
),
cheapest_per_destination AS (
    SELECT *
    FROM ranked_by_destination
    WHERE dest_rank = 1
),
ranked_per_month AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY month
            ORDER BY price ASC
        ) AS month_rank
    FROM cheapest_per_destination
)
SELECT
    month,
    flyFrom,
    flyTo,
    cityFrom,
    cityTo,
    local_departure,
    local_arrival,
    price
FROM ranked_per_month
WHERE month_rank <= 5
ORDER BY month, price;