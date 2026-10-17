
import pandas as pd
from importlib import import_module

try:
    mysql_connector = import_module("mysql.connector")
except ModuleNotFoundError:
    mysql_connector = None


# --------------------------------------------------
# SKYROUTES PROFIT LAB
# MySQL-Based Data Analysis
# --------------------------------------------------

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "dev@12345"  # Enter your MySQL password if you have one
DB_NAME = "SkyRoutesDB"

CSV_FILE = "data/AirlineRoutesData.csv"
OUTPUT_DIR = "outputs"


def connect_to_mysql(database=None):
    """Connect to the MySQL server or project database."""

    if mysql_connector is None:
        raise ModuleNotFoundError(
            "MySQL Connector/Python is required. Install it with "
            "'python -m pip install mysql-connector-python'."
        )

    config = {
        "host": DB_HOST,
        "user": DB_USER,
        "password": DB_PASSWORD
    }

    if database:
        config["database"] = database

    return mysql_connector.connect(**config)


def create_database():
    """Create the project database."""

    connection = connect_to_mysql()
    cursor = connection.cursor()

    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"
    )

    connection.commit()
    cursor.close()
    connection.close()

    print("MySQL database is ready.")


def import_dataset(connection):
    """Import the CSV dataset into the MySQL table."""

    df = pd.read_csv(CSV_FILE)

    required_columns = [
        "FlightID",
        "RouteCode",
        "Origin",
        "Destination",
        "FlightDate",
        "FlightDurationMins",
        "AircraftType",
        "SeatsAvailable",
        "SeatsSold",
        "Revenue",
        "OperationalCost"
    ]

    if list(df.columns) != required_columns:
        raise ValueError(
            "The CSV columns do not match the expected "
            "AirlineRoutesData.csv format."
        )

    df["FlightDate"] = pd.to_datetime(
        df["FlightDate"],
        errors="raise"
    ).dt.strftime("%Y-%m-%d")

    cursor = connection.cursor()

    # Recreate the project table to avoid duplicate records.
    cursor.execute("DROP TABLE IF EXISTS airline_routes")

    cursor.execute("""
        CREATE TABLE airline_routes (
            FlightID VARCHAR(20) PRIMARY KEY,
            RouteCode VARCHAR(10) NOT NULL,
            Origin VARCHAR(5) NOT NULL,
            Destination VARCHAR(5) NOT NULL,
            FlightDate DATE NOT NULL,
            FlightDurationMins INT NOT NULL,
            AircraftType VARCHAR(40) NOT NULL,
            SeatsAvailable INT NOT NULL,
            SeatsSold INT NOT NULL,
            Revenue DECIMAL(14,2) NOT NULL,
            OperationalCost DECIMAL(14,2) NOT NULL,
            CHECK (SeatsAvailable > 0),
            CHECK (
                SeatsSold >= 0
                AND SeatsSold <= SeatsAvailable
            ),
            CHECK (Revenue >= 0),
            CHECK (OperationalCost >= 0)
        )
    """)

    insert_sql = """
        INSERT INTO airline_routes (
            FlightID,
            RouteCode,
            Origin,
            Destination,
            FlightDate,
            FlightDurationMins,
            AircraftType,
            SeatsAvailable,
            SeatsSold,
            Revenue,
            OperationalCost
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    records = list(
        df.itertuples(index=False, name=None)
    )

    cursor.executemany(insert_sql, records)
    connection.commit()

    cursor.close()

    print(f"Successfully imported {len(df):,} flights.")
    return df


def get_sql_queries():
    """Return the seven required SQL queries and supporting analyses."""

    queries = {
        "01_Top10FrequentRoutes": """
            SELECT
                RouteCode,
                Origin,
                Destination,
                COUNT(*) AS NumberOfFlights
            FROM airline_routes
            GROUP BY RouteCode, Origin, Destination
            ORDER BY NumberOfFlights DESC
            LIMIT 10
        """,

        "02_RouteProfitability": """
            SELECT
                RouteCode,
                COUNT(*) AS NumberOfFlights,
                ROUND(AVG(Revenue), 2) AS AverageRevenue,
                ROUND(AVG(OperationalCost), 2)
                    AS AverageOperationalCost,
                ROUND(AVG(Revenue - OperationalCost), 2)
                    AS AverageProfit,
                ROUND(SUM(Revenue), 2) AS TotalRevenue,
                ROUND(SUM(OperationalCost), 2)
                    AS TotalOperationalCost,
                ROUND(SUM(Revenue - OperationalCost), 2)
                    AS TotalProfit
            FROM airline_routes
            GROUP BY RouteCode
            ORDER BY AverageProfit DESC
        """,

        "03_UnderperformingRoutes": """
            SELECT
                RouteCode,
                COUNT(*) AS NumberOfFlights,
                ROUND(AVG(Revenue), 2) AS AverageRevenue,
                ROUND(AVG(OperationalCost), 2)
                    AS AverageOperationalCost,
                ROUND(AVG(Revenue - OperationalCost), 2)
                    AS AverageProfit
            FROM airline_routes
            GROUP BY RouteCode
            HAVING AVG(Revenue - OperationalCost) < 0
            ORDER BY AverageProfit ASC
        """,

        "04_SeatOccupancy": """
            SELECT
                RouteCode,
                SUM(SeatsSold) AS TotalSeatsSold,
                SUM(SeatsAvailable) AS TotalSeatsAvailable,
                ROUND(
                    100.0 * SUM(SeatsSold)
                    / NULLIF(SUM(SeatsAvailable), 0),
                    2
                ) AS OccupancyPct
            FROM airline_routes
            GROUP BY RouteCode
            ORDER BY OccupancyPct DESC
        """,

        "05_MonthlyProfitByRoute": """
            SELECT
                DATE_FORMAT(FlightDate, '%Y-%m')
                    AS FlightMonth,
                RouteCode,
                COUNT(*) AS NumberOfFlights,
                ROUND(SUM(Revenue), 2) AS TotalRevenue,
                ROUND(SUM(OperationalCost), 2)
                    AS TotalOperationalCost,
                ROUND(SUM(Revenue - OperationalCost), 2)
                    AS TotalProfit
            FROM airline_routes
            GROUP BY DATE_FORMAT(FlightDate, '%Y-%m'), RouteCode
            ORDER BY FlightMonth, TotalProfit DESC
        """,

        "06_DomesticVsInternational": """
            SELECT
                CASE
                    WHEN Origin IN (
                        'DXB', 'LHR', 'SIN', 'DOH', 'BKK', 'KUL'
                    )
                    OR Destination IN (
                        'DXB', 'LHR', 'SIN', 'DOH', 'BKK', 'KUL'
                    )
                    THEN 'International'
                    ELSE 'Domestic'
                END AS RouteType,
                COUNT(*) AS NumberOfFlights,
                ROUND(SUM(Revenue), 2) AS TotalRevenue,
                ROUND(SUM(OperationalCost), 2)
                    AS TotalOperationalCost,
                ROUND(SUM(Revenue - OperationalCost), 2)
                    AS TotalProfit,
                ROUND(AVG(Revenue - OperationalCost), 2)
                    AS AverageProfitPerFlight
            FROM airline_routes
            GROUP BY RouteType
            ORDER BY TotalProfit DESC
        """,

        "07_RevenuePerMinuteRank": """
            SELECT
                RouteCode,
                ROUND(SUM(Revenue), 2) AS TotalRevenue,
                SUM(FlightDurationMins) AS TotalFlightMinutes,
                ROUND(
                    SUM(Revenue)
                    / NULLIF(SUM(FlightDurationMins), 0),
                    2
                ) AS RevenuePerMinute,
                DENSE_RANK() OVER (
                    ORDER BY
                    SUM(Revenue)
                    / NULLIF(SUM(FlightDurationMins), 0) DESC
                ) AS RevenuePerMinuteRank
            FROM airline_routes
            GROUP BY RouteCode
            ORDER BY RevenuePerMinuteRank, RouteCode
        """,

        "08_AircraftProfitability": """
            SELECT
                AircraftType,
                COUNT(*) AS NumberOfFlights,
                ROUND(AVG(Revenue - OperationalCost), 2)
                    AS AverageProfitPerFlight,
                ROUND(
                    100.0 * SUM(SeatsSold)
                    / NULLIF(SUM(SeatsAvailable), 0),
                    2
                ) AS OccupancyPct,
                ROUND(SUM(Revenue - OperationalCost), 2)
                    AS TotalProfit
            FROM airline_routes
            GROUP BY AircraftType
            ORDER BY AverageProfitPerFlight DESC
        """,

        "09_MonthlyOverallProfit": """
            SELECT
                DATE_FORMAT(FlightDate, '%Y-%m')
                    AS FlightMonth,
                COUNT(*) AS NumberOfFlights,
                ROUND(SUM(Revenue), 2) AS TotalRevenue,
                ROUND(SUM(OperationalCost), 2)
                    AS TotalOperationalCost,
                ROUND(SUM(Revenue - OperationalCost), 2)
                    AS TotalProfit
            FROM airline_routes
            GROUP BY DATE_FORMAT(FlightDate, '%Y-%m')
            ORDER BY FlightMonth
        """
    }

    return queries


def execute_queries(connection):
    """Execute SQL queries and export results to CSV files."""

    results = {}
    cursor = connection.cursor()

    for name, query in get_sql_queries().items():

        cursor.execute(query)

        columns = [
            column[0]
            for column in cursor.description
        ]

        result_df = pd.DataFrame(
            cursor.fetchall(),
            columns=columns
        )

        output_file = f"{OUTPUT_DIR}/{name}.csv"

        result_df.to_csv(
            output_file,
            index=False
        )

        results[name] = result_df

        print(
            f"Exported {output_file} "
            f"({len(result_df)} rows)"
        )

    cursor.close()
    return results


def create_insights(df, results):
    """Create the six-line RouteInsights.txt report."""

    route_df = results["02_RouteProfitability"]
    aircraft_df = results["08_AircraftProfitability"]
    monthly_df = results["09_MonthlyOverallProfit"]
    type_df = results["06_DomesticVsInternational"]

    best_route = route_df.loc[
        route_df["AverageProfit"].idxmax()
    ]

    worst_route = route_df.loc[
        route_df["AverageProfit"].idxmin()
    ]

    best_aircraft = aircraft_df.loc[
        aircraft_df["AverageProfitPerFlight"].idxmax()
    ]

    worst_aircraft = aircraft_df.loc[
        aircraft_df["AverageProfitPerFlight"].idxmin()
    ]

    best_month = monthly_df.loc[
        monthly_df["TotalProfit"].idxmax()
    ]

    worst_month = monthly_df.loc[
        monthly_df["TotalProfit"].idxmin()
    ]

    occupancy = (
        100 * df["SeatsSold"].sum()
        / df["SeatsAvailable"].sum()
    )

    type_index = type_df.set_index("RouteType")

    lines = [
        (
            f"1. Highest average-profit route: "
            f"{best_route['RouteCode']}, with average profit "
            f"of {best_route['AverageProfit']:,.2f}."
        ),
        (
            f"2. Lowest average-profit route: "
            f"{worst_route['RouteCode']}, with average profit "
            f"of {worst_route['AverageProfit']:,.2f}."
        ),
        (
            f"3. Highest average-profit aircraft: "
            f"{best_aircraft['AircraftType']} "
            f"({best_aircraft['AverageProfitPerFlight']:,.2f} per flight)."
        ),
        (
            f"4. Lowest average-profit aircraft: "
            f"{worst_aircraft['AircraftType']} "
            f"({worst_aircraft['AverageProfitPerFlight']:,.2f} per flight)."
        ),
        (
            f"5. Weighted seat occupancy is {occupancy:.2f}%. "
            f"Best month: {best_month['FlightMonth']}; "
            f"weakest month: {worst_month['FlightMonth']}."
        ),
        (
            f"6. Domestic total profit: "
            f"{type_index.loc['Domestic', 'TotalProfit']:,.2f}; "
            f"international total profit: "
            f"{type_index.loc['International', 'TotalProfit']:,.2f}."
        )
    ]

    with open("RouteInsights.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(lines))

    print("Created RouteInsights.txt")


def main():
    """Run the complete MySQL analysis workflow."""

    connection = None

    try:
        create_database()

        connection = connect_to_mysql(DB_NAME)

        df = import_dataset(connection)

        results = execute_queries(connection)

        create_insights(df, results)

        print("\nAll SQL analyses completed successfully.")
        print("Check the outputs folder for the CSV results.")

    except FileNotFoundError as error:
        print("File not found:", error)

    except Exception as error:
        print("MySQL error:", error)

    finally:
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()
