from tiktok_scrape import trending_videos
from proxy import get_proxies
import asyncio

proxies = get_proxies()
proxy = proxies[0] #use first proxy for testing
print(f"testing rate limit with proxy: {proxy}\n")

#gradually increase scrape count to failure
total_scrapes = 0
session = 0
for scrape_count in range(10, 1000, 10):
    session += 1
    print(f"session {session}: scraping {scrape_count} videos, total scrapes: {total_scrapes}")
    try:
        videos = asyncio.run(trending_videos(scrape_count, proxies=[proxy]))
        total_scrapes += scrape_count
    except Exception as e:
        print(f"Error scraping videos: {e}")
        break
    print(f"successfully scraped {len(videos)} videos")
    print("-"*40)


#CONCLUSION: limit is about 30 in a go, not gonna go further cuz might get softbanned