import sqlite3
from datetime import datetime, timedelta

SQLITE_DB_NAME = "energywatch.db"
TABLE_PRICE_CHANGES = "PriceChanges"

def get_cities() -> list:
    sqlite_connection = sqlite3.connect(SQLITE_DB_NAME)
    sqlite_connection.row_factory = sqlite3.Row
    cursor = sqlite_connection.cursor()
    sql_query = f"""SELECT DISTINCT City 
                    FROM {TABLE_PRICE_CHANGES}
                    ORDER BY City ASC"""  # Alphabetische Sortierung
    cursor.execute(sql_query)
    results = cursor.fetchall()
    cities = [row['City'] for row in results]
    
    cursor.close()
    return cities

def get_poviders(city) -> list:
    try:
        sqlite_connection = sqlite3.connect(SQLITE_DB_NAME)
        sqlite_connection.row_factory = sqlite3.Row
        cursor = sqlite_connection.cursor()
        sql_query = f"""SELECT DISTINCT Provider 
                        FROM {TABLE_PRICE_CHANGES}
                        WHERE City='{city}'
                        ORDER BY Provider ASC"""  # Alphabetische Sortierung
        cursor.execute(sql_query)
        results = cursor.fetchall()
        providers = [row['Provider'] for row in results]
        
        cursor.close()
        return providers

        
        
    except Exception as e:
        print("Verbindung fehlerhaft:", e)
    finally:
        if sqlite_connection:
            sqlite_connection.close()

def get_unique_dates(city, provider):
    now = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(SQLITE_DB_NAME)
    cursor = conn.cursor()
    query = f"""
    SELECT DISTINCT Date
    FROM {TABLE_PRICE_CHANGES}
    WHERE City = ? AND Provider = ?
    ORDER BY Date
    """
    cursor.execute(query, (city, provider))
    dates = [row[0] for row in cursor.fetchall()]
    if now not in dates:
        dates.append(now)

    conn.close()
    return dates

def get_start_date(city, provider):
    conn = sqlite3.connect(SQLITE_DB_NAME)
    cursor = conn.cursor()
    query = f"""
        SELECT Date
        FROM {TABLE_PRICE_CHANGES}
        WHERE City = ? AND Provider = ?
        ORDER BY Date ASC
        LIMIT 1
        """
    cursor.execute(query, (city, provider))
    result = cursor.fetchone()  # Das erste Ergebnis wird geholt
    
    conn.close()
    
    if result:
        start_date_str = result[0]
        return start_date_str
    else:
        return None 

def create_date_dict(start_date_str):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    today = datetime.today()

    date_dict = {}
    current_date = start_date

    # Erstelle für jeden Tag von start_date bis heute ein Dict-Eintrag
    while current_date <= today:
        # Füge den aktuellen Tag als 'dd.mm.yyyy' ein
        date_dict[current_date.strftime("%Y-%m-%d")] = None
        current_date += timedelta(days=1)

    return date_dict

def get_todays_price_changes():
    results = []
    now = datetime.now().strftime("%Y-%m-%d")


    conn = sqlite3.connect(SQLITE_DB_NAME)
    cursor = conn.cursor()
    query = f"""
        SELECT *
        FROM {TABLE_PRICE_CHANGES}
        WHERE Date = ?
    """
    cursor.execute(query, (now,))  # Übergabe des Datums als Parameter
    rows = cursor.fetchall()

    for row in rows:
        results.append(row)
    conn.close()
    
    return results

def get_price_data(city, provider) -> dict:
    
    start_date = get_start_date(city, provider)
    now = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(SQLITE_DB_NAME)
    cursor = conn.cursor()

    query = f"""
    SELECT Tariff, Date, Price
    FROM {TABLE_PRICE_CHANGES}
    WHERE City = ? AND Provider = ?
    """
    cursor.execute(query, (city, provider))
    rows = cursor.fetchall()
    data_dict = {}
    last_price_dict = {}

    for row in rows:
        tariff, date, price = row
        date_dict_for_tariff = create_date_dict(start_date)

        if tariff not in data_dict:
            data_dict[tariff] = date_dict_for_tariff
            last_price_dict[tariff] = 0
        
        data_dict[tariff][date] = price
        last_price_dict[tariff] = price

    for tariff, data in data_dict.items()    :
        if data[now] == None:
            data[now] = last_price_dict[tariff]
    conn.close()
    
    return data_dict