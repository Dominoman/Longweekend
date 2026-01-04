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
    rlocal_departure,
    rlocal_arrival,
    price,
    durationDeparture,
    durationReturn,
    nightsInDest,
    deep_link,
    CASE
        WHEN instr(airlines, ',') > 0
        THEN substr(airlines, 1, instr(airlines, ',') - 1)
        ELSE airlines
    END as firstairline

FROM ranked_per_month
WHERE month_rank <= 5
ORDER BY month, price;