# ZiWeatherBot

ZiWeatherBot is a weather and air quality Telegram bot built using Python, Flask, and the OpenWeatherMap API. It provides real-time weather information, a 12-hour hourly forecast, a 4-day forecast, and air quality index data for any user-specified location.

## Features

- `/start` - Start interacting with the bot and get an introduction message.
- `/weather` - Get the current weather information for a specified location.
- `/hourly` - Get a 12-hour weather forecast in 3-hour intervals for a specified location.
- `/4day` - Get a 4-day weather forecast for a specified location.
- `/airquality` - Get the current Air Quality Index (AQI) for a specified location.

The bot uses OpenWeatherMap to fetch weather and air quality data and geopy to handle location inputs from users.

## How to Use

After starting the bot with `/start`, you can use the commands mentioned above to get weather and air quality information. After sending a command like `/weather`, the bot will prompt you for a location, and then it will provide you with the requested information.

## Project Setup

### Prerequisites

- Python 3.x
- Telegram Bot Token (obtained from [BotFather](https://t.me/botfather))
- OpenWeatherMap API key (obtained from [OpenWeatherMap](https://openweathermap.org/api))