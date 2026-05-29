import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

class NewsService:
    def get_top_news(self, category: str) -> str:
        """Fetch live news headlines using Google News RSS."""
        
        # URL encode the category (e.g., "artificial intelligence" -> "artificial+intelligence")
        encoded_category = urllib.parse.quote(category)
        url = f"https://news.google.com/rss/search?q={encoded_category}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            # We use a standard User-Agent so the request isn't blocked
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req) as response:
                xml_data = response.read()
                
            # Parse the XML response
            root = ET.fromstring(xml_data)
            headlines = []
            
            # Grab the top 5 articles from the RSS feed
            for item in root.findall('./channel/item')[:5]:
                title = item.find('title').text
                headlines.append(f"- {title}")
                
            if not headlines:
                return f"No breaking news found for the topic: {category}."
                
            return f"Top 5 recent headlines for {category}:\n" + "\n".join(headlines)
            
        except Exception as e:
            return f"Error fetching news for {category}: {str(e)}"