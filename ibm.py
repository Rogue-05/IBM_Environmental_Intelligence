import requests
import matplotlib.pyplot as plt
import datetime
import configparser
import pandas as pd
import seaborn as sns
from io import StringIO

# Load credentials from secrets.ini
config = configparser.ConfigParser()
config.read('secrets.ini')

API_KEY   = config.get('EI', 'api_key')
TENANT_ID = config.get('EI', 'tenant_id')
ORG_ID    = config.get('EI', 'org_id')

EI_AUTH_ENDPOINT = "https://api.ibm.com/saascore/run/authentication-retrieve"
EI_API_BASE_URL  = "https://api.ibm.com/geospatial/run/v3/wx"
EI_API_ENDPOINT  = f"{EI_API_BASE_URL}/observations/historical/analytical/ext"

EI_AUTH_CLIENT_ID = 'saascore-' + TENANT_ID
EI_CLIENT_ID      = 'geospatial-' + TENANT_ID

def get_jwt_token():
    """Authenticate and return a JWT token."""
    auth_request_headers = {
        "X-IBM-Client-Id": EI_AUTH_CLIENT_ID,
        "X-API-Key": API_KEY
    }
    auth_url = f"{EI_AUTH_ENDPOINT}/api-key?orgId={ORG_ID}"
    response = requests.get(url=auth_url, headers=auth_request_headers)
    if response.status_code == 200:
        print("✅ Authentication Successful")
        return response.text.strip()
    else:
        print("❌ Authentication Failed:", response.status_code, response.text)
        exit()

def get_weather_data(lat, lon, start_date, end_date, jwt_token):
    """Retrieve IBM weather data for the specified date range."""
    all_data = []
    headers = {
        "X-IBM-Client-Id": EI_CLIENT_ID,
        "Authorization": f"Bearer {jwt_token}"
    }
    # Retrieve data in monthly chunks
    current_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt  = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    while current_date <= end_date_dt:
        next_month = (current_date + datetime.timedelta(days=32)).replace(day=1)
        chunk_end_date = min(next_month - datetime.timedelta(days=1), end_date_dt)
        params = {
            "geocode": f"{lat},{lon}",
            "startDate": current_date.strftime('%Y%m%d'),
            "endDate": chunk_end_date.strftime('%Y%m%d'),
            "format": "csv",
            "units": "s",  # SI units
            "language": "en-US"
        }
        request = requests.Request('GET', EI_API_ENDPOINT, params=params, headers=headers)
        session = requests.Session()
        response = session.send(request.prepare())
        if response.status_code == 200 and response.text.strip():
            csv_data = StringIO(response.text)
            df = pd.read_csv(csv_data)
            all_data.append(df)
            print(f"✅ Data Retrieved for {current_date.strftime('%Y-%m-%d')} to {chunk_end_date.strftime('%Y-%m-%d')}")
        else:
            print(f"❌ Failed to retrieve data: {response.status_code}")
            print(response.text)
        current_date = next_month

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

def classify_rain(precipitation):
    """Classify rain based on precipitation amount."""
    return 'Light Rain' if precipitation < 2.5 else 'Moderate/Heavy Rain'

def process_data(df):
    """Identify rainy days based on the criteria and build a DataFrame of rain events."""
    print("Columns in DataFrame:", df.columns)

    rain_days = []
    rain_intensity = {'Light Rain': 0, 'Moderate/Heavy Rain': 0}
    rain_records = []  # For building a DataFrame of daily rain events

    for _, row in df.iterrows():
        temp = row.get('TemperatureLocalDayAvg', 0)
        # Using the updated precipitation field
        precip = row.get('PrecipAmountLocalDayMax', 0)
        humidity = row.get('RelativeHumidityLocalDayAvg', 0)
        dew_point = row.get('DewpointLocalDayAvg', 0)
        valid_time = row.get('date')
        if not valid_time:
            print("⚠️ Missing date, skipping row.")
            continue
        try:
            valid_time_str = str(valid_time)
            date = datetime.datetime.strptime(valid_time_str, '%Y%m%d').date()
        except ValueError as e:
            print(f"❌ Date parsing error for value {valid_time}: {e}")
            continue

        print(f"📊 Date: {date}, Temp: {temp}, Precip: {precip}, Humidity: {humidity}, Dew Point: {dew_point}")

        # Criteria for a rainy day
        if temp > 0 and precip >= 0 and humidity >= 70 and dew_point > 0:
            rain_days.append(date)
            rain_type = classify_rain(precip)
            rain_intensity[rain_type] += 1
            rain_records.append({"date": date, "rain_type": rain_type})
        else:
            print(f"❌ Conditions not met for date: {date}")

    return rain_days, rain_intensity, pd.DataFrame(rain_records)

def plot_rainfall(rain_days, rain_intensity):
    """
    Plot monthly aggregated rainy days (left subplot)
    and rain intensity distribution (right subplot).
    """
    # Convert daily date list into a DataFrame for monthly grouping
    df_rain = pd.DataFrame({'date': pd.to_datetime(rain_days)})
    # Create a 'month' column (year-month period)
    df_rain['month'] = df_rain['date'].dt.to_period('M')
    # Count how many rainy days per month
    monthly_counts = df_rain.groupby('month').size()

    plt.figure(figsize=(12, 6))

    # Left subplot: monthly rainy days
    plt.subplot(1, 2, 1)
    monthly_counts.plot(kind='bar', color='orangered', edgecolor='black')
    plt.title('Monthly Rainy Days in Seattle (Apr-Sep 2023)', fontsize=14, color='darkred')
    plt.xlabel('Month', fontsize=12, color='darkred')
    plt.ylabel('Frequency', fontsize=12, color='darkred')

    # Right subplot: bar chart of rain intensity distribution
    plt.subplot(1, 2, 2)
    plt.bar(rain_intensity.keys(), rain_intensity.values(), color=['tomato', 'darkorange'])
    plt.title('Rain Intensity Distribution', fontsize=14, color='darkred')
    plt.ylabel('Number of Days', fontsize=12, color='darkred')

    plt.tight_layout()
    plt.show()

def plot_monthly_rain_types(rain_df):
    """
    Create a stacked bar chart of Light Rain vs. Moderate/Heavy Rain days for each month.
    """
    if 'date_dt' not in rain_df.columns:
        # parse the date if not already parsed
        rain_df['date_dt'] = pd.to_datetime(rain_df['date'])

    # Create a 'month' column (year-month period)
    rain_df['month'] = rain_df['date_dt'].dt.to_period('M')

    # Count how many Light Rain vs. Moderate/Heavy Rain days per month
    monthly_types = rain_df.groupby(['month', 'rain_type']).size().unstack(fill_value=0)

    # Plot a stacked bar chart
    monthly_types.plot(kind='bar', stacked=True, figsize=(10, 6), color=['tomato', 'darkorange'], edgecolor='black')
    plt.title("Monthly Rain Type Distribution (Apr-Sep 2023)", fontsize=14, color='darkred')
    plt.xlabel("Month", fontsize=12, color='darkred')
    plt.ylabel("Number of Days", fontsize=12, color='darkred')
    plt.legend(title="Rain Type")
    plt.tight_layout()
    plt.show()

def generate_rain_type_heatmap(rain_df, start_date, end_date):
    """Create a heat map of rain type (0=none, 1=light, 2=moderate/heavy) by month/day."""
    # Create a complete date range DataFrame for the period
    all_dates = pd.date_range(start=start_date, end=end_date)
    df_all = pd.DataFrame({"date": all_dates})

    # Convert the 'date' column in rain_df to datetime
    rain_df["date_dt"] = pd.to_datetime(rain_df["date"])
    # Merge so that days with no rain become NaN
    df_merged = pd.merge(df_all, rain_df, left_on="date", right_on="date_dt", how="left")

    # Map rain type to numeric
    mapping = {"Light Rain": 1, "Moderate/Heavy Rain": 2}
    df_merged["rain_numeric"] = df_merged["rain_type"].map(mapping).fillna(0)

    # Extract month/day
    df_merged["month"] = df_merged["date"].dt.month
    df_merged["day"] = df_merged["date"].dt.day

    # Create pivot table
    pivot = df_merged.pivot(index="month", columns="day", values="rain_numeric")

    plt.figure(figsize=(14, 6))
    sns.heatmap(pivot, cmap="OrRd", annot=True, fmt=".0f",
                cbar_kws={'label': 'Rain Type (0=None, 1=Light, 2=Mod/Heavy)'})
    plt.title("Heat Map of Rain Type in Seattle (Apr-Sep 2023)", fontsize=16, color='darkred')
    plt.xlabel("Day of Month", fontsize=12, color='darkred')
    plt.ylabel("Month", fontsize=12, color='darkred')
    plt.show()

if __name__ == '__main__':
    jwt_token = get_jwt_token()
    # Seattle's latitude and longitude
    latitude = 47.6062
    longitude = -122.3321
    start_date = '2023-04-01'
    end_date   = '2023-09-30'

    df = get_weather_data(latitude, longitude, start_date, end_date, jwt_token)
    if df.empty:
        print("❌ No weather data retrieved.")
    else:
        # Identify rainy days and intensities
        rain_days, rain_intensity, rain_df = process_data(df)

        # 1) Plot aggregated monthly rainy days + overall intensity distribution
        plot_rainfall(rain_days, rain_intensity)

        # 2) Stacked bar chart: Light vs. Moderate/Heavy Rain per month
        if not rain_df.empty:
            plot_monthly_rain_types(rain_df)

        # 3) Heat map of rain type
        generate_rain_type_heatmap(rain_df, start_date, end_date)
