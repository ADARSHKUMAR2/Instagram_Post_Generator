import urllib.parse
import xml.etree.ElementTree as ET
import httpx

class NewsService:
    async def get_top_news(self, category: str) -> str:
        """Fetch live news headlines asynchronously."""
        
        encoded_category = urllib.parse.quote(category)
        url = f"https://news.google.com/rss/search?q={encoded_category}&hl=en-US&gl=US&ceid=US:en"
        
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                # Add broader headers to look like a real browser
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/rss+xml, application/xml, text/xml'
                }
                response = await client.get(url, headers=headers, timeout=10.0)
                response.raise_for_status()
                xml_data = response.text
                
            # Safely check if Google returned HTML instead of XML (Bot block)
            if "<html" in xml_data.lower() and "<rss" not in xml_data.lower():
                return f"SYSTEM STOP: Google News blocked the request. Do not retry. Proceed to generate the post with general knowledge about {category}."

            # Parse the XML response
            root = ET.fromstring(xml_data)
            headlines = []
            
            for item in root.findall('./channel/item')[:5]:
                title = item.find('title').text
                headlines.append(f"- {title}")
                
            if not headlines:
                return f"SYSTEM STOP: No breaking news found for: {category}. Do not retry. Generate a speculative or general post."
                
            return f"Top 5 recent headlines for {category}:\n" + "\n".join(headlines)
            
        except ET.ParseError:
             return "SYSTEM STOP: Data formatting error from news source. Do not retry."
        except Exception as e:
            return f"SYSTEM STOP: Network error - {str(e)}. Do not retry."