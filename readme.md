
## Setup

1. Install TikTok Api (https://github.com/davidteather/TikTok-Api/tree/main)

2. download the code (tiktok_scrape.py and proxy.py)

3. go to proxy.py and enter your proxy api on line 5 (i use the free proxies from webshare: https://www.webshare.io/, just make an account and click download in the proxy list page)


## How to use

run tiktok_scrape.py

it should get your proxies and test them, then get ms_tokens(tiktok session token) based on your proxies. By default it created only 4 separate sessions but this can be changed (line 219 and 256)

then you will have to enter a bunch of stuff related to how you want to scrape (eg. scrape count, tags, video sort key etc.)

It will then launch sessions sequentially and print the session info. Afterwards it starts to scrape till it hits scrape count or 5minutes is up.

The final report will be created as report.txt in your current directory


## Errors and How to fix
Probably tiktok has a soft rate limit applied to an ip address, when you scrape too many videos at one go, they block you for a bit. I think this refreshes in several hours.
keep scrape count low and rotate ip among proxies

TUNNEL_CONNECTION failed = proxy failed, bandwidth expired probably

TIKTOK error status code 10201 = tiktok blocked you probably because you are scraping too much

'TikTokApi' object has no attribute 'num_sessions' = not sure how to fix this, i think its a problem with the api when trying to do concurrent scraping, create separate sessions for each instance

TikTok returning empty page - headless=False, proxies, make sure to sync the tokens to the ip and add random delays

timeout error - sometimes you just need to retry

ValueError: I/O operation on closed pipe - idk what this means but its not an issue since it doesnt affect the main code

code is quite spaghetti


