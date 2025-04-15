from TikTokApi import TikTokApi
import asyncio
from tiktok_scrape import get_ms_tokens, trending_videos, tag_videos
from playwright.async_api import async_playwright
from proxy import get_proxies
import sys
import random

async def test():
    #test proxies
    proxies = get_proxies()
    print(proxies)
    #test ms_tokens, align tokens and proxies
    ms_tokens = []
    for i in range(2):
        token = await get_ms_tokens(1, proxy=proxies[i+1])
        ms_tokens.append(token[0])
    print(ms_tokens)
    #test session creation, create multiple sessions
    async with TikTokApi() as api:
        await api.create_sessions(headless=False, num_sessions=1, ms_tokens=[ms_tokens[0]], proxies=[proxies[1]], suppress_resource_load_types=["image", "media", "font", "stylesheet", "other"])
        await api.create_sessions(headless=False, num_sessions=1, ms_tokens=[ms_tokens[1]], proxies=[proxies[2]], suppress_resource_load_types=["image", "media", "font", "stylesheet", "other"])
        for session in api.sessions:
            print(session, "\n")
        #test asynchronous scraping of trending videos
        total = []
        task1 = asyncio.create_task(tag_videos(api, session_index=0, tag="education", count=30))
        task2 = asyncio.create_task(tag_videos(api, session_index=1, tag="education", count=30))
        tasks = [(0, task1), (1,task2)]
        while len(total) < 100:
            done, pending = await asyncio.wait([x[1] for x in tasks], return_when=asyncio.FIRST_COMPLETED)
            free = []
            for t in tasks:
                if t[1] in done:
                    free.append(t[0])
                    tasks.remove(t)
                    total.extend(t[1].result())
            for i in free:
                tasks.append((i, asyncio.create_task(tag_videos(api, session_index=i, tag="education", count=30))))
        for task in tasks:
            task[1].cancel()
        print(total)
        
        
async def test2():
    proxies = get_proxies()
    ms_token1 = await get_ms_tokens(1, proxy=proxies[1])
    ms_token2 = await get_ms_tokens(1, proxy=proxies[2])
    async with TikTokApi() as api:
        await api.create_sessions(num_sessions=1, headless=False, ms_tokens=ms_token1, proxies=[proxies[3]], suppress_resource_load_types=["image", "media", "font", "stylesheet", "other"])
        await api.create_sessions(num_sessions=1, headless=False, ms_tokens=ms_token2, proxies=[proxies[4]], suppress_resource_load_types=["image", "media", "font", "stylesheet", "other"])
        print(api.sessions)
        videos = await asyncio.gather(tag_videos(api, 0, "education"), tag_videos(api, 1, "fashion"))
        await api.close_sessions()
    print(videos)


asyncio.run(test())