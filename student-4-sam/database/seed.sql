INSERT INTO shipments (
    origin,
    destination,
    status,
    driver,
    vehicle,
    departure_date,
    estimated_arrival,
    delay_minutes
)
VALUES
(
    'Sydney',
    'Melbourne',
    'IN_TRANSIT',
    'James Smith',
    'TRK-04',
    '2026-09-03 08:00',
    '2026-09-03 18:00',
    0
);

INSERT INTO shipments (
    origin,
    destination,
    status,
    driver,
    vehicle,
    departure_date,
    estimated_arrival,
    delay_minutes
)
VALUES
(
    'Sydney',
    'Brisbane',
    'DELAYED',
    'Michael Brown',
    'TRK-07',
    '2026-09-03 07:00',
    '2026-09-03 20:00',
    180
);

INSERT INTO shipments (
    origin,
    destination,
    status,
    driver,
    vehicle,
    departure_date,
    estimated_arrival,
    delay_minutes
)
VALUES
(
    'Melbourne',
    'Sydney',
    'PLANNED',
    'Daniel Wilson',
    'TRK-02',
    '2026-09-04 09:00',
    '2026-09-04 19:00',
    0
);