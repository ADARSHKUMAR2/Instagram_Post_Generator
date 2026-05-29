class WeatherService:
    def get_current_weather(self, city: str) -> str:
        """Fetch real-time weather data for a specific city."""
        # TODO: Replace with actual OpenWeatherMap API call
        mock_database = {
            "meerut": "☀️ 42°C, Sunny and highly humid. Heatwave warning in effect.",
            "london": "🌧️ 14°C, Light rain and overcast.",
            "new york": "⛅ 22°C, Partly cloudy."
        }
        
        city_lower = city.lower()
        if city_lower in mock_database:
            return f"Weather in {city}: {mock_database[city_lower]}"
        
        return f"Weather data for {city} is currently unavailable."