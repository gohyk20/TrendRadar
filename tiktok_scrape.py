from TikTokApi import TikTokApi
import asyncio
from datetime import datetime, timedelta
from proxy import get_proxies, test_proxies
import random
from playwright.async_api import async_playwright
import sys

async def get_ms_tokens(proxies=[]):
    #get ms_token using the proxy server with playwright
    #proxy ip and ms_token DOES NOT need to match, so just spam create
    ms_tokens = []
    tasks = [_get_ms_token(proxy) for proxy in proxies]
    ms_tokens = await asyncio.gather(*tasks)
    return ms_tokens


async def _get_ms_token(proxy={}):
    ms_token = None
    async with async_playwright() as p:
        if proxy == {}:
            browser = await p.chromium.launch(headless=False) #no proxy
        else:
            browser = await p.chromium.launch(headless=False, proxy=proxy)
        page = await browser.new_page()
        await page.goto("https://www.tiktok.com/", wait_until="load")
        await page.mouse.wheel(0, 500) # simulate scroll or interaction to trigger full JS execution
        await page.wait_for_timeout(5000)
        cookies = await page.context.cookies()
        for c in cookies:
            if c["name"] == "msToken":
                ms_token = c["value"]
                break
        await browser.close()
    return ms_token


async def trending_videos(api, session_index, count=10):
    #get trending videos, from fyp
    videos = []
    async for video in api.trending.videos(count=count, session_index=session_index):
        if video == None or video.stats == None:
            continue
        videos.append(video)
    return videos


async def tag_videos(api, session_index, tag, count=10):
    #random delay to throw off bot detection
    await asyncio.sleep(random.uniform(3,5))
    #get videos based on a specific hashtag
    videos = []
    async for video in api.hashtag(name=tag).videos(count=count, session_index=session_index):
        if video == None or video.stats == None:
            continue
        videos.append(video)
    return videos



async def get_videos_chunked(tags, count, num_sessions=2, chunk_size=30, proxies=[], ms_tokens=[], timeout=timedelta(minutes=5)):
    #to avoid rate limit need to call the get video functions in chunks of 30
    collected_videos = []

    #create the sessions first, one for each proxy / token pair
    async with TikTokApi() as api:
        # asyncio.gather(
        #     *[api.create_sessions(headless=False, ms_tokens=ms_tokens[i], num_sessions=1, proxies=[proxies[i]], suppress_resource_load_types=["image", "media", "font", "stylesheet", "other"])
        #       for i in range(num_sessions)]
        # )
        for i in range(num_sessions): #try create sequentially first
            await api.create_sessions(headless=False, num_sessions=1, ms_tokens=ms_tokens[i], proxies=[proxies[i]], suppress_resource_load_types=["image", "media", "font", "stylesheet", "other"])
        for session in api.sessions: #print sesions for debugging
            print(session)

        #create initial tasks for each session
        if tags != []: #tag cannot be blank
            tasks = [(i, asyncio.create_task(tag_videos(api, i, tags[i%len(tags)], chunk_size))) for i in range(num_sessions)] #stores both session id and task
        else:
            tasks = [(i, asyncio.create_task(trending_videos(api, i, chunk_size))) for i in range(num_sessions)]
        
        #set tag_id to be used to rotate through tags
        if tags != []:
            tag_id = (num_sessions-1)%len(tags)

        #collect videos
        start = datetime.now()
        while len(collected_videos) < count and (datetime.now() - start) < timeout:
            print(f"Collected {len(collected_videos)} videos")

            #wait for tasks to be completed and add the videos
            completed, pending = await asyncio.wait([task for i,task in tasks], return_when=asyncio.FIRST_COMPLETED)
            free_sessions = []
            for i,task in tasks:
                if task in completed:
                    tasks.remove((i,task))
                    free_sessions.append(i)
                    for v in task.result(): #add results
                        if not v.id in [x.id for x in collected_videos]: #check for duplicates
                            collected_videos.append(v)

            #refresh task list to use free sessions
            for i in free_sessions:
                if tags != []:
                    tag_id = (tag_id+1)%len(tags) #update tag_id to cycle to next tag
                    tasks.append((i, asyncio.create_task(tag_videos(api, i, tags[tag_id], chunk_size))))
                else:
                    tasks.append((i, asyncio.create_task(trending_videos(api, i, chunk_size))))

        #cleanup
        for i,task in tasks:
            task.cancel()

    return collected_videos



def print_video_info(video):
    #format with video info
    print(f"Video ID: {video.id}")
    try:
        print(f"URL1: {video.as_dict["video"]["bitrateInfo"][0]["PlayAddr"]["UrlList"][-1]}") #using this mp4 from the dict
    except Exception as e:
        print(f"URL1: {e}")
    print(f"URL2: https://www.tiktok.com/@{video.author.username}/video/{video.id} ") #generate based on tiktok format
    print(f"Author: {video.author.username}")
    print(f"stats: {video.stats}")
    print(f"hashtags: {[x.name for x in video.hashtags]}")
    try:
        print(f"sound: {video.sound.title}, original: {video.sound.original}")
    except Exception as e:
        print(f"sound: {e}")
    print(f"date created: {video.create_time}")
    print("-" * 40)



def sort_videos(videos, key="diggCount", afterDate=None):
    #sort based on collectCount, playCount, diggCount(likes), commentCount. Descending order. Filter by date if needed.
    #afterDate shld be datetime object, default None
    if key not in ["collectCount", "playCount", "diggCount", "commentCount"]:
        raise ValueError("Invalid key. Must be one of: collectCount, playCount, diggCount, commentCount")
    if afterDate:
        return list(filter(lambda x:x.create_time > afterDate, sorted(videos, key=lambda x:int(x.stats[key]), reverse=True)))
    else:
        return sorted(videos, key=lambda x:int(x.stats[key]), reverse=True)


def get_music(videos):
    #get the music (non original audio) from the videos and calculate stats
    music = {}
    for video in videos:
        if video.sound.original == False:
            if video.sound.title in music: #every appearance adds to the stats
                music[video.sound.title]["appearances"] += 1
                music[video.sound.title]["likes"] += int(video.stats["diggCount"])
                music[video.sound.title]["plays"] += int(video.stats["playCount"])
                music[video.sound.title]["collects"] += int(video.stats["collectCount"])
                music[video.sound.title]["comments"] += int(video.stats["commentCount"])
            else:
                music[video.sound.title] = {"appearances":1, "likes":int(video.stats["diggCount"]), "plays":int(video.stats["playCount"]), "collects":int(video.stats["collectCount"]), "comments":int(video.stats["commentCount"])}
    return music


def sort_music(music, key="appearances"):
    #sort music based on appearances, likes, plays, collects or comments, or avg of these. descending order.
    possible = ["appearances", "likes", "plays", "collects", "comments", "avg_likes", "avg_plays", "avg_collects", "avg_comments"]
    if key not in possible:
        raise ValueError(f"Invalid key. Must be one of: {possible}")
    if "avg" in key:
        key = key.split("_")[1] #get the key after avg
        return sorted(music.items(), key=lambda x:x[1][key]/x[1]["appearances"], reverse=True) #divide by appearances
    return sorted(music.items(), key=lambda x:x[1][key], reverse=True)


def print_music_info(music, scrape_count):
    #music is the sorted item (tuple) from sort_music, use scrape count and appearances to give average info
    print(f"Music: {music[0]}")
    print(f"Appearances: {music[1]["appearances"]} in {scrape_count} videos scraped")
    print(f"Total likes: {music[1]["likes"]}, Average Likes: {music[1]["likes"]/music[1]["appearances"]}")
    print(f"Total plays: {music[1]["plays"]}, Average Plays: {music[1]["plays"]/music[1]["appearances"]}")
    print(f"Total collects: {music[1]["collects"]}, Average Collects: {music[1]["collects"]/music[1]["appearances"]}")
    print(f"Total comments: {music[1]["comments"]}, Average Comments: {music[1]["comments"]/music[1]["appearances"]}")
    print("-" * 40)


def generate_report(results, video_key, after_date, music_key, scrape_count, show, tags, output_file):
    #all prints is transferred to the output file
    sys.stdout = open(output_file, "w", encoding="utf-8")

    #print general info
    print(f"{scrape_count} videos scraped")
    print(f"videos after {after_date}")
    print(f"tags: {tags}")
    print(f"videos sorted by {video_key}")
    print(f"music sorted by {music_key}. Note: original music is filtered out")
    
    #sort the videos and print top
    results = sort_videos(results, key=video_key, afterDate=after_date)
    print("TRENDING POSTS")
    print("-"*40)
    for video in results[:show]: #show top ten results
        print_video_info(video)

    #get music and stats from videos
    music = get_music(results)

    #sort the music and print top 10
    music = sort_music(music, key=music_key)
    print("TRENDING MUSIC")
    print("-"*40)
    for music in music[:10]:
        print_music_info(music, scrape_count)


def generate_report_simplified(results, video_key, after_date, music_key, scrape_count, show, tags, output_file):
    #all prints is transferred to the output file
    sys.stdout = open(output_file, "w", encoding="utf-8")

    #print general info
    print(f"{scrape_count} videos scraped")
    print(f"videos after {after_date}")
    print(f"tags: {tags}")
    
    #sort the videos and print top
    results = sort_videos(results, key=video_key, afterDate=after_date)
    print("TRENDING POSTS")
    print("-"*40)
    for i, video in enumerate(results[:show]): #show top results
        print(f"{i+1}. https://www.tiktok.com/@{video.author.username}/video/{video.id} ")



if __name__ == "__main__":

    #get session proxies
    proxies = test_proxies(get_proxies())[:4] #get proxies from webshare, returns list of dicts, test for good ones
    print(proxies)

    #get tokens, make sure to match with proxies
    ms_tokens = asyncio.run(get_ms_tokens(proxies))
    print(ms_tokens)

    #user input
    # SCRAPE_COUNT = int(input("Enter scrape count: "))
    # after_date = datetime.strptime((input("Enter date to filter by (YYYY-MM-DD):")), "%Y-%m-%d")
    # video_key = input("Enter key to sort videos by (collectCount, playCount, diggCount, commentCount): ")
    # music_key = input("Enter key to sort music by (appearances, likes, plays, collects, comments, or add avg_ to front eg.avg_likes): ")
    # print("NOTE: adding more tags would reduce duplicate videos scraped and allow for a higher scrape count ultimately")
    # tags = []
    # tag=""
    # while tag != "q":
    #     tag = input("Enter tags to scrape (enter q to stop): ")
    #     if tag != "q":
    #         tags.append(tag)
    # show = int(input("Enter amount of posts to show: "))

    #default values
    SCRAPE_COUNT = 1000
    after_date = datetime(2025,4,6,0,0,0)
    video_key = "diggCount"
    music_key = "likes"
    CAELI_TAGS =  ["sustainablefashion", "slowfashion", "quietluxury", "minimalstyle",
    "neutraloutfits", "timelessstyle", "sgfashion", "madeinsingapore",
    "effortlessstyle", "ecofriendlyfashion", "fashionstartup",
    "chicstyle", "modernwoman", "capsulewardrobe", "fashiontok"]
    MACRO_TAGS = ["alevels", "olevels", "sgstudents", "studytips", "studywithme",
    "studymotivation", "sgtuition", "tuitioncentre", "education",
    "academicgoals", "studyhacks", "studentlife", "examseason",
    "learnontiktok", "studyvlog"]
    tags = []
    show = 30

    #get the results of scraping
    results = asyncio.run(get_videos_chunked(tags, SCRAPE_COUNT, num_sessions=4, chunk_size=30, proxies=proxies, ms_tokens=ms_tokens))

    #generate report
    generate_report_simplified(results, video_key, after_date, music_key, SCRAPE_COUNT, show, tags, "report.txt")
    print("report generated as report.txt")


