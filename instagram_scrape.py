from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
import os
from datetime import timedelta, datetime, timezone
from proxy import get_proxies, test_proxies
import asyncio
import sys, random
import asyncpg
from instagrapi.mixins.challenge import ChallengeChoice
from database_config import USER, PASSWORD, HOST, DATABASE

def _first_login(user, passw):

    #generates settings.json and returns client
    cl = Client()
    cl.login(user, passw)
    cl.get_timeline_feed() #test

    #dump settings
    cl.dump_settings(f"{user}_settings.json")

    return cl


def login(user, passw, proxy=""):
    cl = Client()
    cl.challenge_code_handler = challenge_code_handler #handle challenges??
    cl.delay_range = [2,5] #reduce bot detection

    #set proxy if possible
    if proxy != "":
        cl.set_proxy(proxy)

    #check if settings exists
    settings = f"{user}_settings.json"
    if os.path.isfile(settings):

        try:
            #try and load session
            cl.load_settings(settings)
            cl.login(user, passw)
            cl.get_timeline_feed()
            return cl
        
        except LoginRequired:
            #if login required session is no longer valid (they sus) but can try to relogin
            print("login required, attempting relogin")
            old_session = cl.get_settings()
            cl.set_settings({}) #clear settings
            cl.set_uuids(old_session["uuids"]) #can use the same uuid? idk what that is
            cl.login(user, passw)
            cl.dump_settings(f"{user}_settings.json")
            return cl
        
        except ChallengeRequired:
            #challenge required cuz they sus?
            print("Challenge required, attempting to resolve")
            try:
                cl.challenge_resolve(cl.last_json)
            except:
                print("failed")
                raise
            cl.dump_settings(f"{user}_settings.json")
            return cl
    
    #settings don't exist means it is first time logging in
    else:
        print("first login")
        return _first_login(user, passw)


def get_code_from_sms(username):
    while True:
        code = input(f"Enter code (6 digits) for {username} from sms: ").strip()
        if code and code.isdigit():
            return code
    return None


def get_code_from_email(username):
    while True:
        code = input(f"Enter code (6 digits) for {username} from email: ").strip()
        if code and code.isdigit():
            return code
    return None


def challenge_code_handler(username, choice):
    #challenge code handler, imma just use inputs becuz its kinda hard to automate
    print(f"Challenge: {choice}")
    if choice == ChallengeChoice.SMS:
        return get_code_from_sms(username)
    elif choice == ChallengeChoice.EMAIL:
        return get_code_from_email(username)
    print("Unsupported challenge type, skipping")
    return False


async def tag_posts(account, tag, chunk=random.randrange(7,15)): #try very low count to reduce detection possibly
    #login and get the posts asynchronously
    cl = await asyncio.to_thread(login, *account)
    posts =  await asyncio.to_thread(cl.hashtag_medias_top, tag, amount=chunk)
    await asyncio.sleep(random.uniform(10, 20)) #very long delay
    return posts


async def insert_posts(pool, post):
    #insert posts into the postgressql database
    async with pool.acquire() as conn:
        await conn.execute("""INSERT INTO instaposts (id, code, likes, plays, taken_at, date_scraped) VALUES($1, $2, $3, $4, $5, $6)
                 ON CONFLICT (id) DO UPDATE SET likes = EXCLUDED.likes, plays = EXCLUDED.plays""", 
                 str(post.pk), post.code, post.like_count, post.play_count, post.taken_at, datetime.now())


async def get_posts_chunked(total, accounts, tags, after_date, timeout=timedelta(minutes=5)):
    start = datetime.now()
    posts = []

    #create initial tasks, store as [acount,task] to track the free acounts
    tasks = [[accounts[i], asyncio.create_task(tag_posts(accounts[i], tags[i%len(tags)]))] for i in range(len(accounts))]
    tag_id = (len(accounts)-1)%len(tags) #track the current tag and loop through tags

    #add posts until total
    while len(posts) < total and (datetime.now()-start)<timeout:
        print(f"{len(posts)} posts scraped")

        #wait for a task to be done
        free_accounts = []
        done, pending = await asyncio.wait([t for a,t in tasks], return_when=asyncio.FIRST_COMPLETED)
        for a,t in tasks:
            if t in done:
                tasks.remove([a,t])
                free_accounts.append(a)
                for post in t.result():
                    if post not in posts and post.taken_at >= after_date: #filter for date and avoid duplicates
                        posts.append(post)
                #just insert into table
                pool = await asyncpg.create_pool(user=USER, password=PASSWORD, host=HOST, database=DATABASE) #default values is 10 connections
                await asyncio.gather(*(insert_posts(pool, post) for post in t.result()))
                await pool.close()

        #give tasks to free accounts
        for a in free_accounts:
            tag_id = (tag_id+1)%len(tags)
            tasks.append([a, asyncio.create_task(tag_posts(a, tags[tag_id]))])
    
    #cleanup
    for a,t in tasks:
        t.cancel()   

    return posts

        
def print_post_info(media):
    #print media info
    print(f"Video ID: {media.pk}")
    print(f"URL: https://www.instagram.com/p/{media.code} ")
    print(f"like count: {media.like_count}")
    print(f"play count: {media.play_count}")
    print(f"date created: {media.taken_at}")
    print("-" * 40)


def sort_posts(posts, key="like_count"):
    #sort based on like_count or play_count. Descending order.
    #Note that photos have zero play_count
    if key not in ["play_count", "like_count"]:
        raise ValueError("Invalid key. Must be one of: play_count, like_count")
    elif key == "like_count":
        return sorted(posts, key=lambda x:int(x.like_count), reverse=True)
    else:
        return sorted(posts, key=lambda x:int(x.play_count), reverse=True)


def add_accounts(new_accounts:list[list[str]], no_proxy=False):
    #every account should be paired with an ip address, store account pairs in accounts.txt
    #get proxies as dict
    proxies = test_proxies(get_proxies()) 

    #add a new proxy to each account
    if not no_proxy:
        for i in range(len(new_accounts)):
            
            #cycle through proxies
            used_proxies = [p for user,pw,p in get_accounts()] + [p for user,pw,p in new_accounts[:i+1]]
            chosen_proxy = ""
            while chosen_proxy == "":
                for proxy in proxies: #loop through possible proxies
                    proxy = f"http://{proxy["username"]}:{proxy["password"]}@{proxy["server"]}"
                    if proxy not in used_proxies: #found unused
                        chosen_proxy = proxy
                        break
                    used_proxies.remove(proxy) #remove one occurence

            #get proxy randomly (maybe figure out a better way to cycle through proxies one day)
            p = chosen_proxy

            #test logging in with the proxy
            cl = login(*new_accounts[i], p)
            new_accounts[i].append(p)

    #write to accounts.txt
    with open("accounts.txt", "a") as f:
        for a in new_accounts:
            f.write("\n") #newline
            if not no_proxy:
                f.write(f"{a[0]},{a[1]},{a[2]}")
            else:
                f.write(f"{a[0]},{a[1]}")

    print("accounts added")


def get_accounts():
    accounts = []

    #attempt to read the file
    if os.path.isfile("accounts.txt"):
        with open("accounts.txt", "r") as f:
            for line in f:
                line = line.strip().split(",") #user, pass, proxy
                if len(line) > 1:
                    accounts.append(line)
    else:
        print("no accounts")
    
    return accounts


def test_accounts():
    #get accounts and and test them, run this perodically
    if os.path.isfile("accounts.txt"):
        accounts = get_accounts()
        working = []

        #try to login and get timeline
        for a in accounts:
            print(f"Testing account: {a}")
            try:
                cl = login(*a)
                cl.get_timeline_feed()
                print("account passed")
                working.append(a)
            except Exception as e:
                print(f"Error - {e}")
                print("please remove this account from the list")

        #return working accounts
        print(f"working accounts: {working}")
        return working

    else:
        print("no accounts")


def generate_report_simplified(posts, scrape_count, after_date, tags, show=30, DB=False):

    #sort posts by likes
    if not DB:
        posts = sort_posts(posts)

    #send report to report.txt
    sys.stdout = open("report.txt", "w", encoding="utf-8") #send to report.txt

    #print general info
    if not DB:
        print(f"{scrape_count} videos scraped")
    else:
        print(f"from {len(posts)} videos in DB")
    print(f"videos after {after_date}")
    print(f"tags: {tags}")

    #print posts
    print("\nTRENDING POSTS")
    print("-"*40)
    for i, p in enumerate(posts[:show]):
        if not DB:
            print(f"{i+1}. https://www.instagram.com/p/{p.code} ")
        else:
            print(f"{i+1}. https://www.instagram.com/p/{p['code']} ")

    #message
    sys.stdout = sys.__stdout__
    print("report generated")


async def setup_DB():
    conn = await asyncpg.connect(user=USER, password=PASSWORD, host=HOST, database=DATABASE)
    await conn.execute("""CREATE TABLE IF NOT EXISTS instaposts(
        id TEXT PRIMARY KEY,
        code TEXT,
        likes INT,
        plays INT,
        taken_at TIMESTAMP,
        date_scraped TIMESTAMP)""")
    await conn.close()


async def fetch_DB(after_date):
    conn = await asyncpg.connect(user=USER, password=PASSWORD, host=HOST, database=DATABASE)
    posts = await conn.fetch("SELECT * FROM instaposts WHERE taken_at > $1 ORDER BY likes DESC", after_date) #list of tuples
    await conn.close()
    for post in posts:
        post = dict(post) #convert to dictionary for easier use
    return posts


if __name__ == "__main__":
    #get acounts
    #add_accounts([[user, pass], [user, pass]])
    accounts = test_accounts()

    #params
    caeli_instagram_tags = [
        "sustainablefashion", "slowfashion", "quietluxury",
        "neutraloutfits", "timelesswardrobe", "ethicalfashion", "effortlessstyle",
        "capsulewardrobe", "modernfemininity", "madeinsingapore", "sgfashion",
        "outfitinspo", "ootd", "fashion"
    ]
    show = 30
    scrape_count = len(accounts)*100 #each account scrape volume cannot be too high
    after_date = datetime(2025, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
    DB = True

    #set up db
    asyncio.run(setup_DB())

    #scrape media
    try:
        posts = asyncio.run(get_posts_chunked(scrape_count, accounts, caeli_instagram_tags, after_date))

    #get posts from db instead
    except Exception as e:
        print(f"STOPPED SCRAPING: {e}")
        DB = True

    if DB:
        posts = asyncio.run(fetch_DB(after_date))
        scrape_count = len(posts)
        
    #print media info after sorting
    generate_report_simplified(posts, scrape_count, after_date, caeli_instagram_tags, show, DB)
