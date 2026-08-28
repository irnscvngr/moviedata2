import json
from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox
from curl_cffi import requests

target_url = "https://www.medimops.de/produkte-C0/?fcIsSearch=1&searchparam=conclave+blu+ray"

# Step 1: Open browser once to pass Cloudflare challenge & grab cookies
print("Solving Cloudflare challenge in background...")
with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto(target_url, wait_until="networkidle")
    
    # Extract resolved cookies and User-Agent from browser session
    cookies = {c['name']: c['value'] for c in page.context.cookies()}
    user_agent = page.evaluate("navigator.userAgent")

print("Challenge passed! Transferring tokens to curl_cffi...")

# Step 2: Use captured cookies for lightning-fast HTTP requests
headers = {"User-Agent": user_agent}

response = requests.get(
    target_url,
    headers=headers,
    cookies=cookies,
    impersonate="chrome124"
)

print("\n-------------- RESPONSE START ------------------\n")
print(response.text)
print("\n-------------- RESPONSE END ------------------\n")

print(f"Conclave appears in response: {"conclave" in response.text.lower()}")
print(f"9,69 appears in response: {"9,69" in response.text}")
print(f"9.69 appears in response: {"9.69" in response.text}")

# Step 3: Extract the product data from full SSR HTML
soup = BeautifulSoup(response.text, "html.parser")
next_data = soup.find("script", id="__NEXT_DATA__")

if next_data:
    data = json.loads(next_data.string)
    print("Successfully fetched full SSR page data!")
    # Products live inside Next.js pageProps dictionary
    # print(data['props']['pageProps'])
else:
    print("Failed to find __NEXT_DATA__ script tag.")
