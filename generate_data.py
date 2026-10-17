from pathlib import Path

import numpy as np
import pandas as pd


def generate_dataset():
    """Generate the airline dataset required for SkyRoutes Profit Lab."""

    rng = np.random.default_rng(42)

    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    routes = [
        ("BOM-DEL", "BOM", "DEL", "Domestic"),
        ("DEL-BOM", "DEL", "BOM", "Domestic"),
        ("BOM-BLR", "BOM", "BLR", "Domestic"),
        ("BLR-BOM", "BLR", "BOM", "Domestic"),
        ("DEL-BLR", "DEL", "BLR", "Domestic"),
        ("BLR-DEL", "BLR", "DEL", "Domestic"),
        ("BOM-HYD", "BOM", "HYD", "Domestic"),
        ("HYD-BOM", "HYD", "BOM", "Domestic"),
        ("DEL-HYD", "DEL", "HYD", "Domestic"),
        ("HYD-DEL", "HYD", "DEL", "Domestic"),
        ("MAA-BOM", "MAA", "BOM", "Domestic"),
        ("BOM-MAA", "BOM", "MAA", "Domestic"),
        ("DEL-CCU", "DEL", "CCU", "Domestic"),
        ("CCU-DEL", "CCU", "DEL", "Domestic"),
        ("AMD-BOM", "AMD", "BOM", "Domestic"),
        ("BOM-AMD", "BOM", "AMD", "Domestic"),
        ("BOM-DXB", "BOM", "DXB", "International"),
        ("DXB-BOM", "DXB", "BOM", "International"),
        ("DEL-LHR", "DEL", "LHR", "International"),
        ("LHR-DEL", "LHR", "DEL", "International"),
        ("BLR-SIN", "BLR", "SIN", "International"),
        ("SIN-BLR", "SIN", "BLR", "International"),
        ("DEL-SIN", "DEL", "SIN", "International"),
        ("SIN-DEL", "SIN", "DEL", "International"),
        ("BOM-DOH", "BOM", "DOH", "International"),
        ("DOH-BOM", "DOH", "BOM", "International"),
        ("DEL-BKK", "DEL", "BKK", "International"),
        ("BKK-DEL", "BKK", "DEL", "International"),
        ("BOM-KUL", "BOM", "KUL", "International"),
        ("KUL-BOM", "KUL", "BOM", "International")
    ]

    aircraft_types = [
        "Airbus A320",
        "Airbus A321",
        "Boeing 737",
        "Boeing 787",
        "Airbus A350"
    ]

    aircraft_factors = {
        "Airbus A320": 1.00,
        "Airbus A321": 1.08,
        "Boeing 737": 1.02,
        "Boeing 787": 1.62,
        "Airbus A350": 1.78
    }

    dates = pd.date_range(
        "2025-01-01",
        "2025-12-31",
        freq="D"
    )

    loss_routes = {
        "DEL-CCU",
        "CCU-DEL",
        "AMD-BOM"
    }

    rows = []

    for i in range(1, 6001):

        route_code, origin, destination, route_type = (
            routes[rng.integers(0, len(routes))]
        )

        flight_date = dates[
            rng.integers(0, len(dates))
        ]

        aircraft = rng.choice(
            aircraft_types,
            p=[0.32, 0.18, 0.28, 0.14, 0.08]
        )

        if route_type == "Domestic":
            duration = int(
                np.clip(rng.normal(115, 35), 45, 260)
            )
            seats = int(
                rng.choice([150, 180, 186, 220])
            )
            fare = rng.uniform(2500, 8500)
            cost_rate = rng.uniform(900, 1700)
            fixed_cost = rng.uniform(120000, 280000)

        else:
            duration = int(
                np.clip(rng.normal(330, 100), 150, 850)
            )
            seats = int(
                rng.choice([180, 220, 260, 300, 340])
            )
            fare = rng.uniform(12000, 42000)
            cost_rate = rng.uniform(1200, 2600)
            fixed_cost = rng.uniform(450000, 1100000)

        seasonal_factor = (
            1.15
            if flight_date.month in [5, 6, 11, 12]
            else 0.90
            if flight_date.month in [2, 3, 9]
            else 1.00
        )

        occupancy = np.clip(
            rng.beta(7, 2.4) * seasonal_factor,
            0.35,
            0.99
        )

        seats_sold = int(
            np.clip(round(seats * occupancy), 0, seats)
        )

        revenue = (
            seats_sold
            * fare
            * rng.uniform(0.90, 1.10)
        )

        operational_cost = (
            duration * cost_rate + fixed_cost
        ) * aircraft_factors[aircraft] * rng.choice(
            [1.00, 1.00, 1.00, 1.18]
        )

        # Deliberately create loss-making routes for analysis.
        if route_code in loss_routes:
            revenue *= 0.10

            operational_cost = max(
                operational_cost * 1.50,
                revenue + 100000
            )

        rows.append({
            "FlightID": f"SKY{i:06d}",
            "RouteCode": route_code,
            "Origin": origin,
            "Destination": destination,
            "FlightDate": flight_date.strftime("%Y-%m-%d"),
            "FlightDurationMins": duration,
            "AircraftType": aircraft,
            "SeatsAvailable": seats,
            "SeatsSold": seats_sold,
            "Revenue": round(revenue, 2),
            "OperationalCost": round(operational_cost, 2)
        })

    df = pd.DataFrame(rows)

    output_file = data_dir / "AirlineRoutesData.csv"
    df.to_csv(output_file, index=False)

    print("Dataset generated successfully.")
    print(f"File: {output_file}")
    print(f"Total flight records: {len(df):,}")

    return df


if __name__ == "__main__":
    generate_dataset()