import os
import httpx

class WeatherService:
    def __init__(self):
        # Securely load the API key from environment variables
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    async def get_current_weather(self, city: str) -> str:
        """Fetch real-time weather data for a specific city asynchronously."""
        if not self.api_key:
            return "⚠️ Weather service configuration error: OPENWEATHER_API_KEY is missing."

        try:
            params = {
                "q": city,
                "appid": self.api_key,
                "units": "metric"  # Use 'imperial' for Fahrenheit
            }
            
            # Use httpx for non-blocking asynchronous network calls
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                temp = round(data["main"]["temp"])
                desc = data["weather"][0]["description"].capitalize()
                weather_id = data["weather"][0]["id"]
                humidity = data["main"]["humidity"]
                
                # Dynamically map the weather condition to an emoji
                emoji = self._get_weather_emoji(weather_id)
                
                return f"Weather in {city.title()}: {emoji} {temp}°C, {desc}. Humidity: {humidity}%."
                
            elif response.status_code == 404:
                return f"Weather data for '{city}' is currently unavailable (City not found)."
            else:
                return f"Weather service error: Received status code {response.status_code}"
                
        except httpx.TimeoutException:
            return "Weather service timeout: The API took too long to respond."
        except httpx.RequestError as e:
            return f"Failed to connect to weather service: {e}"

    def _get_weather_emoji(self, weather_id: int) -> str:
        """Map OpenWeatherMap condition IDs to dynamic emojis."""
        if 200 <= weather_id <= 232:
            return "⛈️"  # Thunderstorm
        elif 300 <= weather_id <= 321:
            return "🌦️"  # Drizzle
        elif 500 <= weather_id <= 531:
            return "🌧️"  # Rain
        elif 600 <= weather_id <= 622:
            return "❄️"  # Snow
        elif 700 <= weather_id <= 781:
            return "🌫️"  # Atmosphere (fog, mist, sand, etc.)
        elif weather_id == 800:
            return "☀️"  # Clear
        elif 801 <= weather_id <= 804:
            return "☁️"  # Clouds
        return "🌡️"   # Default fallback