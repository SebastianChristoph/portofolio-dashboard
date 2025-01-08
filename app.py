from flask import Flask, render_template, request
import pandas as pd
import json
import os
import energywatch_handler
import datetime
from datetime import datetime, timedelta
from dateutil import parser 
import requests

cwd = os.getcwd()
def load_json_data():

    if "Desktop" in cwd:
        headers = {'user-agent':'Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 105.0.0.11.118 (iPhone11,8; iOS 12_3_1; en_US; en-US; scale=2.00; 828x1792; 165586599)'}
        URL = "https://sebastianchristoph.pythonanywhere.com/bildwatch-api"
        source = requests.get(URL, headers = headers).text
        context = json.loads(source)
    
    else:
        file_path = "/home/SebastianChristoph/tasks/bildwatch/bildwatch_plus_article.json"
    
        with open(file_path) as json_file:
            context = json.load(json_file)
    
    context.pop("lastUpdated", None)
    return context
    
def get_bildwatch_keyfacts(context):
    keysfacts = {}

    # Articles TOTAL
    keysfacts["articles_total"] = len(context)

    # Articles CONVERTED
    count_articles_converted = 0
    for article_id, article_info in context.items():
        try:
            if article_info.get("timeBetween") is not None:
                count_articles_converted += 1
        except:
            continue
    keysfacts["articles_converted"] = count_articles_converted

    # Articles TOTAL
    published_dates = []
    for article_id, article_info in context.items():
        if article_id == "lastUpdated": continue
        
        try:
            published_str = article_info.get("published")
            if published_str:
                # Verwende den parser, um das ISO-Datum zu parsen
                published_date = parser.parse(published_str)
                published_dates.append(published_date)
        except Exception as e:
            print(e)
            continue

    # ANALYZED SINCE
    first_published = min(published_dates)
    today = datetime.now()
    diff_in_days = (today - first_published).days
    keysfacts["difference_in_days"] = diff_in_days

    # AVERAGE CONVERT TIME
    minutes = 0
    articles = 0
    for article_id, article_info in context.items():
        if article_id == "lastUpdated":
            continue

        time = article_info.get("timeBetween")
        if time:
            articles += 1
            data = time.split(",")
            minutes += int(data[1])
            minutes += 60 * int(data[0])

    # Berechnung des Durchschnitts
    if articles > 0:  # Sicherstellen, dass es Artikel gibt
        minutes = minutes / articles
    else:
        minutes = 0  # Falls keine Artikel vorhanden sind

    hours = int(minutes // 60)  # Ganze Stunden berechnen und als int umwandeln
    mins = int(minutes % 60)      # Verbleibende Minuten berechnen und als int umwandeln

    # Formatierung des Outputs
    if hours > 0 and mins > 0:
        keysfacts["average_convert_time"] = f"{hours}h {mins}min"
    elif hours > 0:
        keysfacts["average_convert_time"] = f"{hours}h"
    else:
        keysfacts["average_convert_time"] = f"{mins}min"

    return keysfacts

def convert_to_hours(time_str):
    try:
        hours, minutes = map(int, time_str.split(','))
        return hours + minutes / 60
    except:
        return None

def get_time_between_histogram(time_between_hours, num_bins=5):
    if len(time_between_hours) > 0:
        cut_data, bin_edges = pd.cut(time_between_hours, bins=num_bins, retbins=True)
        bin_counts = cut_data.value_counts()
        
        # Intervall-Labels und Zählungen in ein Dictionary umwandeln
        time_between_histogram = {}
        for i in range(len(bin_edges) - 1):
            interval = f"{int(bin_edges[i])}-{int(bin_edges[i+1])}h"
            time_between_histogram[interval] = int(bin_counts.iloc[i])  # Umwandlung in native int
        
        return time_between_histogram, bin_edges
    
    return {}, 0

def get_category_data(context):
    category_data = {}
    for key, value in context.items():
        if key == "lastUpdated":
            continue
        if value.get('timeBetween') is not None:
            category_data[value['category']] = category_data.get(value['category'], 0) + 1
    return category_data

def get_articles_per_day(df):
    return {str(date): count for date, count in df.groupby('publishedToNormal').size().items()}

def get_unconverted_per_day(articles_per_day_dict, data):
    unconverted_dict = {}

    for current_date, value in articles_per_day_dict.items():
        unconverted_articles = 0
        current_date = datetime.fromisoformat(str(current_date))

        for article, article_data in data.items():
            published_date = datetime.fromisoformat(article_data["published"])


            if published_date > current_date:
                continue
            
            if article_data["publishedToNormal"] == None:
                unconverted_articles += 1
                continue

            published_to_normal_date = datetime.fromisoformat(article_data["publishedToNormal"])
            
            if published_to_normal_date > current_date:
                unconverted_articles += 1

        unconverted_dict[str(current_date)] = unconverted_articles
    return unconverted_dict
 



app = Flask(__name__)

@app.route("/", methods=["GET"] )
def dashboard():
    return render_template("dashboard.html")

@app.route("/bildwatch", methods=["GET", "POST"])
def bildwatch():
    global cwd
    context = load_json_data()
    keyfacts = get_bildwatch_keyfacts(context)
    
    # Pandas DataFrame erstellen
    df = pd.DataFrame.from_dict(context, orient='index')
    df['publishedToNormal'] = pd.to_datetime(df['publishedToNormal']).dt.date
    df = df.dropna(subset=['publishedToNormal'])

    if request.method == "GET":
        yesterday = datetime.now() - timedelta(days=1)
        target_date = yesterday.date()  
    else:
        # Das Datum vom Formular erhalten
        date_str = request.form.get("date")
        if date_str:
            # Umwandeln des String-Datums in ein datetime.date Objekt
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    filtered_df = df[df['publishedToNormal'] == target_date]
    # Zeit in Dezimalstunden umwandeln
    filtered_df['hours'] = filtered_df['timeBetween'].dropna().apply(convert_to_hours)
    time_between_hours = filtered_df['hours'].dropna().tolist()

    # Zeitintervall-Histogramm erstellen
    time_between_histogram, bin_edges = get_time_between_histogram(time_between_hours)

    # Kategoriedaten und Artikel pro Tag berechnen
    category_data = get_category_data(context)
    articles_per_day = get_articles_per_day(df)


    time_between_histogram_json = json.dumps(time_between_histogram)
    category_data_json = json.dumps(category_data)
    articles_per_day_json = json.dumps(articles_per_day)
    days = articles_per_day

    unconverted_data = get_unconverted_per_day(articles_per_day, context)
    unconverted_data_json = json.dumps(unconverted_data)


    return render_template(
        "bildwatch.html",
        data=context,
        keyfacts=keyfacts,
        category_data=category_data_json,
        articles_per_day=articles_per_day_json,
        time_between_histogram=time_between_histogram_json,
        days = days,
        target_date = target_date,
        default_date= target_date,
        unconverted_data = unconverted_data_json
    )
@app.route("/bildwatch-api")
def bildwatch_api():
    with open("/home/SebastianChristoph/tasks/bildwatch/bildwatch_plus_article.json") as json_file:
        content = json_file.read()
        context = json.loads(content)
    formatted_json = json.dumps(context, indent=4)
    return formatted_json

@app.route("/energywatch")
def energywatch():
    global cwd

    cities = energywatch_handler.get_cities()
    todays_price_changes = energywatch_handler.get_todays_price_changes()
    return render_template("energywatch.html", cities=cities, city = None, provider = None, todays_price_changes = todays_price_changes)

@app.route("/energywatch_data_handling", methods=["POST"])
def energy_watch_handling():

    city = request.form.get("city")
    provider = request.form.get("provider")
    providers = None
    results = {}
    dates = []
    results_json = {}
    dates_json = {}

    if city != None:
        providers =  energywatch_handler.get_poviders(city)
    
    # GET PRICE CHANGES AND DATES FOR CHART
    if city != None and provider != None:
        results = energywatch_handler.get_price_data(city, provider)
        results_json = json.dumps(results)
    
    return render_template("energywatch.html", city=city, provider = provider, providers=providers, results_json=results_json)

if __name__ == "__main__":
    app.run(debug=True)