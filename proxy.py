import requests

def get_proxies():
    #get link from webshare download button
    proxy_api = "" #ENTER YOUR API HERE
    ret = requests.get(proxy_api).text #returns lines of text with proxy info

    #parse response
    proxies = []
    for line in ret.split("\n"):
        parts = line.strip().split(":")
        if len(parts) != 4:
            continue
        PROXY_ADDRESS = parts[0]
        PROXY_PORT = parts[1]
        PROXY_USERNAME = parts[2]
        PROXY_PASSWORD = parts[3]
        proxy = {
            "server": f"{PROXY_ADDRESS}:{PROXY_PORT}",
            "username": PROXY_USERNAME,
            "password": PROXY_PASSWORD,
        }
        proxies.append(proxy)

    return proxies

def test_proxies(proxies):
    working = []
    for proxy in proxies:
        proxy_dict = {
            "http": f"http://{proxy["username"]}:{proxy["password"]}@{proxy["server"]}",
            "https": f"https://{proxy["username"]}:{proxy["password"]}@{proxy["server"]}",
        }
        try:
            response = requests.get("http://httpbin.org/ip", proxies=proxy_dict, timeout=10)
        except Exception as e:
            print(f"Proxy {proxy["server"]} failed: {e}")
            continue
        if response.status_code == 200:
            print(f"Proxy {proxy["server"]} is working")
            working.append(proxy)
        else:
            print(f"Proxy {proxy["server"]} failed with status code {response.status_code}")
    return working

if __name__ == "__main__":
    proxies = get_proxies()
    print(proxies)
    working_proxies = test_proxies(proxies)