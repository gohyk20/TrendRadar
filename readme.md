
TIK TOK ISSUES:
Probably tiktok has a soft rate limit applied to an ip address, when you scrape too many videos at one go, they block you for a bit. I think this refreshes in several hours.
keep scrape count low and rotate ip among proxies

TUNNEL_CONNECTION failed = proxy failed, bandwidth expired probably
TIKTOK error status code 10201 = tiktok blocked you probably because you are scraping too much
'TikTokApi' object has no attribute 'num_sessions' = not sure how to fix this, i think its a problem with the api when trying to do concurrent scraping, create separate sessions for each instance
TikTok returning empty page - headless=False, proxies, make sure to sync the tokens to the ip and add random delays
timeout error - sometimes you just need to retry
ValueError: I/O operation on closed pipe - idk what this means but its not an issue since it doesnt affect the main code

TODO:
- figure out how to do concurrent scraping for tiktok
    - why would there be no attribute (check the source code)
    - Might have to rewrite the api
- start instagram scraping (if tired of working on tiktok)

