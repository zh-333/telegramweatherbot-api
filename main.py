import os
import telebot
import requests
import logging, logging.config
from flask import Flask, request
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from datetime import datetime

load_dotenv()

BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEATHER_TOKEN = os.environ.get('WEATHER_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')  # URL for setting webhook
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Logging configuration
config = {
    'disable_existing_loggers': False,
    'version': 1,
    'formatters': {
        'short': {
            'format': '%(asctime)s %(levelname)s %(message)s',
        },
        'long': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'formatter': 'short',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
logging.config.dictConfig(config)
logger = logging.getLogger(__name__)

# Convert wind degrees to cardinal direction
def get_wind_direction(degrees):
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(degrees / 45) % 8
    return directions[index]

# Command: /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, 'Hello! Welcome to ZiWeatherBot. Use commands like /weather, /hourly, /4day, or /airquality to get weather information.')

# Command: /weather
@bot.message_handler(commands=['weather'])
def send_weather(message):
    sent_message = bot.send_message(message.chat.id, "Please enter the location for which you want the current weather:")
    bot.register_next_step_handler(sent_message, fetch_weather)

# Get coordinates from location
def location_handler(location_name):
    geolocator = Nominatim(user_agent="weather_bot")
    try:
        location_data = geolocator.geocode(location_name)
        latitude = round(location_data.latitude, 2)
        longitude = round(location_data.longitude, 2)
        logger.info("Latitude '%s' and Longitude '%s' found for location '%s'", latitude, longitude, location_name)
        return latitude, longitude
    except AttributeError:
        logger.error('Location not found for "%s"', location_name)
        return None, None

# Loop until valid location is provided
def prompt_for_valid_location(message, next_step_function):
    latitude, longitude = location_handler(message.text)
    if latitude is None or longitude is None:
        sent_message = bot.send_message(message.chat.id, 'Location not found. Please try again with a valid location.')
        bot.register_next_step_handler(sent_message, next_step_function)
    else:
        next_step_function(message, latitude, longitude)

# Get weather data
def get_weather(latitude, longitude):
    url = f'https://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&units=metric&appid={WEATHER_TOKEN}'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return None

# Fetch current weather
def fetch_weather(message, latitude=None, longitude=None):
    if latitude is None or longitude is None:
        prompt_for_valid_location(message, fetch_weather)
        return

    weather = get_weather(latitude, longitude)
    try:
        description = weather['list'][0]['weather'][0]['description']
        temperature = round(weather['list'][0]['main']['temp'], 1)
        humidity = weather['list'][0]['main']['humidity']
        wind_speed = round(weather['list'][0]['wind']['speed'] * 3.6, 1)  # Convert m/s to km/h
        wind_direction = get_wind_direction(weather['list'][0]['wind']['deg'])
        weather_message = (
            f"🌦️ *Weather:* {description.capitalize()}\n"
            f"🌡️ *Temperature:* {temperature}°C\n"
            f"💧 *Humidity:* {humidity}%\n"
            f"🌬️ *Wind Speed:* {wind_speed} km/h\n"
            f"🧭 *Wind Direction:* {wind_direction}\n"
        )
        bot.send_message(message.chat.id, "Here's the current weather:", parse_mode='Markdown')
        bot.send_message(message.chat.id, weather_message, parse_mode='Markdown')
    except (IndexError, KeyError):
        bot.send_message(message.chat.id, 'Unable to fetch weather information. Please try again later.')

# Command: /hourly for hourly weather forecast
@bot.message_handler(commands=['hourly'])
def hourly_forecast(message):
    sent_message = bot.send_message(message.chat.id, "Please enter the location for an hourly weather forecast:")
    bot.register_next_step_handler(sent_message, fetch_hourly_forecast)

# Fetch hourly forecast
def fetch_hourly_forecast(message, latitude=None, longitude=None):
    if latitude is None or longitude is None:
        prompt_for_valid_location(message, fetch_hourly_forecast)
        return

    weather = get_weather(latitude, longitude)
    if 'list' not in weather:
        bot.send_message(message.chat.id, "Could not fetch weather data. Please try again later.")
        return

    current_time = datetime.utcnow()  # Current time in UTC
    hourly_forecast_message = "*12-Hour Weather Forecast:*\n"

    # Find the forecast closest to the current time
    forecasts = weather['list']
    for forecast in forecasts:
        forecast_time = datetime.utcfromtimestamp(forecast['dt'])
        if forecast_time >= current_time:
            # Found the first forecast after the current time
            for i in range(4):  # Show the next 4 forecasts (12 hours)
                forecast = forecasts[i]
                forecast_time = datetime.utcfromtimestamp(forecast['dt']).strftime('%H:%M %d-%m-%Y')
                temperature = round(forecast['main']['temp'], 1)
                description = forecast['weather'][0]['description'].capitalize()
                wind_speed = round(forecast['wind']['speed'] * 3.6, 1)  # Convert m/s to km/h
                wind_direction = get_wind_direction(forecast['wind']['deg'])
                hourly_forecast_message += (
                    f"Time: {forecast_time}\n"
                    f"🌡️ Temperature: {temperature}°C\n"
                    f"🌦️ Weather: {description}\n"
                    f"🌬️ Wind Speed: {wind_speed} km/h\n"
                    f"🧭 Wind Direction: {wind_direction}\n\n"
                )
            break

    bot.send_message(message.chat.id, hourly_forecast_message, parse_mode='Markdown')
# Command: /4day for 4-day weather outlook
@bot.message_handler(commands=['4day'])
def four_day_forecast(message):
    sent_message = bot.send_message(message.chat.id, "Please enter the location for the 4-day weather outlook:")
    bot.register_next_step_handler(sent_message, fetch_four_day_forecast)

# Fetch 4-day forecast
def fetch_four_day_forecast(message, latitude=None, longitude=None):
    if latitude is None or longitude is None:
        prompt_for_valid_location(message, fetch_four_day_forecast)
        return

    weather = get_weather(latitude, longitude)
    if 'list' not in weather:
        bot.send_message(message.chat.id, "Could not fetch weather data. Please try again later.")
        return

    four_day_forecast = "*4-Day Weather Forecast:*\n"
    for i in range(0, 32, 8):  # 1 forecast every 8 intervals (24 hours) for the next 4 days
        forecast = weather['list'][i]
        forecast_date = datetime.utcfromtimestamp(forecast['dt']).strftime('%d-%m-%Y')
        temperature = round(forecast['main']['temp'], 1)
        description = forecast['weather'][0]['description'].capitalize()
        wind_speed = round(forecast['wind']['speed'] * 3.6, 1)  # Convert m/s to km/h
        wind_direction = get_wind_direction(forecast['wind']['deg'])
        four_day_forecast += (
            f"Date: {forecast_date}\n"
            f"🌡️ Temperature: {temperature}°C\n"
            f"🌦️ Weather: {description}\n"
            f"🌬️ Wind Speed: {wind_speed} km/h\n"
            f"🧭 Wind Direction: {wind_direction}\n\n"
        )

    bot.send_message(message.chat.id, four_day_forecast, parse_mode='Markdown')

# Command: /airquality
@bot.message_handler(commands=['airquality'])
def air_quality(message):
    sent_message = bot.send_message(message.chat.id, "Please enter the location for air quality information:")
    bot.register_next_step_handler(sent_message, fetch_air_quality)

# Fetch air quality
def fetch_air_quality(message, latitude=None, longitude=None):
    if latitude is None or longitude is None:
        prompt_for_valid_location(message, fetch_air_quality)
        return

    url = f'http://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={WEATHER_TOKEN}'
    response = requests.get(url)
    if response.status_code != 200:
        bot.send_message(message.chat.id, 'Unable to fetch air quality information. Please try again later.')
        return

    try:
        data = response.json()
        aqi = data['list'][0]['main']['aqi']
        air_quality_index = {
            1: 'Good',
            2: 'Fair',
            3: 'Moderate',
            4: 'Poor',
            5: 'Very Poor'
        }
        air_quality_message = f"*Air Quality Index (AQI):* {air_quality_index.get(aqi, 'Unknown')}\n"
        bot.send_message(message.chat.id, air_quality_message, parse_mode='Markdown')
    except (IndexError, KeyError):
        bot.send_message(message.chat.id, 'Unable to fetch air quality information. Please try again later.')

# Flask webhook route for Telegram updates
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Flask route to set webhook
@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    webhook_url = WEBHOOK_URL + BOT_TOKEN
    success = bot.set_webhook(url=webhook_url)
    if success:
        return "Webhook set successfully!", 200
    else:
        return "Failed to set webhook!", 400

# Flask app to run the webhook listener
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))