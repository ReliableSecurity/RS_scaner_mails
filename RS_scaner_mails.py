# Advanced Email Crawler with JS Rendering, Deep Recursion, and Spam Filtering (Optimized)

import asyncio
from requests_html import AsyncHTMLSession
from urllib.parse import urljoin, urlparse
import re
import os
from collections import deque
from colorama import init, Fore
import argparse

init(autoreset=True)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
SPAM_TRASH = ["example.com", "tempmail", "10minutemail", "mailinator", "yopmail"]
VISITED = set()
EMAILS = set()
URL_QUEUE = deque()
MAX_PAGES = 5000
OUTPUT_FILE = "emails_found.txt"
DOMAIN = ""
CONCURRENT_TASKS = 5


async def fetch_and_parse(session, url):
    try:
        print(Fore.CYAN + f"[+] Crawling: {url}")
        response = await session.get(url, timeout=20)
        await response.html.arender(timeout=10, sleep=0.5)
        return response
    except Exception as e:
        print(Fore.RED + f"[!] Error fetching {url}: {e}")
        return None


def extract_emails(text):
    return {
        match.lower() for match in EMAIL_REGEX.findall(text)
        if not any(spam in match.lower() for spam in SPAM_TRASH)
    }


def extract_links(base_url, html):
    links = set()
    try:
        anchors = html.find("a")
        for tag in anchors:
            href = tag.attrs.get("href")
            if href:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if parsed.netloc.endswith(DOMAIN):
                    links.add(full_url.split("#")[0])
    except Exception as e:
        print(Fore.RED + f"[!] Error parsing links: {e}")
    return links


async def worker(session):
    while URL_QUEUE and len(VISITED) < MAX_PAGES:
        url = URL_QUEUE.popleft()
        if url in VISITED:
            continue

        VISITED.add(url)
        response = await fetch_and_parse(session, url)
        if not response:
            continue

        html = response.html
        emails = extract_emails(html.text)
        if emails:
            for email in emails:
                if email not in EMAILS:
                    print(Fore.GREEN + f"  [email found] {email}")
                    with open(OUTPUT_FILE, 'a') as f:
                        f.write(f"{email} -> {url}\n")
            EMAILS.update(emails)

        links = extract_links(url, html)
        print(Fore.BLUE + f"[~] Found {len(links)} links")
        for link in links:
            if link not in VISITED:
                URL_QUEUE.append(link)

        print(Fore.YELLOW + f"[Status] Processed: {len(VISITED)}, Emails: {len(EMAILS)}, Queue: {len(URL_QUEUE)}\n")


async def crawl():
    session = AsyncHTMLSession()
    tasks = [asyncio.create_task(worker(session)) for _ in range(CONCURRENT_TASKS)]
    await asyncio.gather(*tasks)
    await session.close()


async def main(start_url, threads):
    global DOMAIN, CONCURRENT_TASKS
    DOMAIN = urlparse(start_url).netloc
    URL_QUEUE.append(start_url)
    CONCURRENT_TASKS = threads

    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    await crawl()


if __name__ == "__main__":
    

    parser = argparse.ArgumentParser(description="Async Email Crawler")
    parser.add_argument("url", help="Start URL")
    parser.add_argument("-t", "--threads", type=int, default=5, help="Number of concurrent threads")
    args = parser.parse_args()

    asyncio.run(main(args.url, args.threads))
