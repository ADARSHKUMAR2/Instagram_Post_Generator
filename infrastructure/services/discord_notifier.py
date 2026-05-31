import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscordManager:
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        
        if not self.webhook_url:
            logger.warning("⚠️ DISCORD_WEBHOOK_URL is missing. Notifications are disabled.")

    def send_success_notification(self, caption: str, image_url: str):
        """Fires a rich embed notification to Discord."""
        if not self.webhook_url:
            return
            
        payload = {
            "content": "🚀 **New Post Successfully Published to Instagram!**",
            "embeds": [
                {
                    "description": f"**Caption:**\n{caption}",
                    "color": 13773097, # Instagram Pink/Purple hex color
                    "image": {"url": image_url}
                }
            ]
        }
        
        try:
            logger.info("🔔 Pinging Discord webhook...")
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info("✅ Discord notification delivered.")
        except Exception as e:
            logger.error(f"⚠️ Discord Webhook silently failed: {e}")