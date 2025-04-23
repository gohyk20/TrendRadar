
# Setup

## For tiktok:

1. Install TikTok Api (https://github.com/davidteather/TikTok-Api/tree/main)

2. download the code (tiktok_scrape.py and proxy.py)

3. go to proxy.py and enter your proxy api on line 5 (i use the free proxies from webshare: https://www.webshare.io/, just make an account and click download in the proxy list page)

## For instagram:

1. Install instagrapi (https://github.com/subzeroid/instagrapi/tree/master)

2. download the code (instagram_scrape.py and proxy.py and database_config.py if you plan to use database)

3. If you want to use database set up by installing postgresql and pip install asyncpg. Then enter the database info inside database_config.py

4. If you dont want to use database make sure to set DB to False in instagram_scrape.py (line 323). I would recommend using a database incase your code fails halfway your posts are still stored somewhere.

5. go to proxy.py and enter proxy api


# How to use

## tiktok

run tiktok_scrape.py

it should get your proxies and test them, then get ms_tokens(tiktok session token) based on your proxies. By default it created only 4 separate sessions but this can be changed (line 219 and 256)

then you will have to enter a bunch of stuff related to how you want to scrape (eg. scrape count, tags, video sort key etc.)

It will then launch sessions sequentially and print the session info. Afterwards it starts to scrape till it hits scrape count or 5minutes is up.

The final report will be created as report.txt in your current directory

## instagram

create instagram accounts preferabbly with a vpn

add your accounts by adding the account and password, uncomment line 310. You only need to do this once, make sure to comment out 310 afterwards. This will create an accounts.txt file

The code should hopefully login to the account and use a proxy to start scraping

The final report will be created as report.txt in your current directory


# Errors and How to fix

code is quite spaghetti so any changes is appreciated

## tik tok
Probably tiktok has a soft rate limit applied to an ip address, when you scrape too many videos at one go, they block you for a bit. I think this refreshes in several hours.
keep scrape count low and rotate ip among proxies

TUNNEL_CONNECTION failed = proxy failed, bandwidth expired probably

TIKTOK error status code 10201 = tiktok blocked you probably because you are scraping too much

'TikTokApi' object has no attribute 'num_sessions' = not sure how to fix this, i think its a problem with the api when trying to do concurrent scraping, create separate sessions for each instance

TikTok returning empty page - headless=False, proxies, make sure to sync the tokens to the ip and add random delays

timeout error - sometimes you just need to retry

ValueError: I/O operation on closed pipe - idk what this means but its not an issue since it doesnt affect the main code

## instagram

login required = this should be fixed automatically by re login

Challenge required = my fix does not work, idk how to fix this. After too many scrapes instagram flags the account and makes you do a challenge. Prob need to read the instagrapi documentation carefully and figure out how to handle. 

current / future workarounds:
- the scrape count is very low with a long delay to maybe reduce detection but after a certain amount of scrapes instagram catches on anyway\
- using a database is a good way to make sure you can at least get some posts even if the code fails
- better proxies would probably help that requires $$$
- maybe try "warming up" accounts by doing things like scrolling feed, making a bio and waiting 24 hours before trying to scrape
- do more account rotation (requires more accounts)

Making accounts:
- you can create maybe ten gmail accounts if you use your mobile app
- try https://mail.tm/
- maybe use a vpn so your ip doesn't get flagged



