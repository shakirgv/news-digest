from dotenv import load_dotenv
import feedparser
from google import genai
import sys
import os
import requests
import re

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

FEEDS = [
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "http://www.aljazeera.com/xml/rss/all.xml",
]

FEEDS = {
    "World": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "Region": [
        "https://en.trend.az/feeds/index.rss",
        "https://www.azernews.az/feed.php",
        "https://jam-news.net/feed/",
    ],
}

items = []

for category, urls in FEEDS.items():
    for url in urls:
        try:
            rss_response = requests.get(
                url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}
            )
            feed = feedparser.parse(rss_response.content)
        except requests.RequestException as error:
            print("Failed:", url, error)
            continue
        if not feed.entries:
            print("No entries:", url, rss_response.status_code)
            continue
        print("OK:", url, len(feed.entries))
        for entry in feed.entries[:5]:
            items.append(f"[{category}] {entry.title} | {entry.link}")

client = genai.Client()

prompt = (
    "You are a news analyst assistant for an International Relations student "
    "focused on Azerbaijan and the South Caucasus.\n"
    "Below are news items in the format: [category] title | link.\n"
    "Importance means: geopolitics, diplomacy, security, energy, trade and "
    "regional stability. Ignore routine announcements (tenders, minor "
    "appointments, statistics releases), sports, crime, market price updates "
    "and generic roundup pages.\n"
    "Write a digest in Azerbaijani, plain text only (no markdown, no asterisks), "
    "under 3000 characters:\n"
    "1) First section (title translated to Azerbaijani: TOP 3): the three most "
    "important stories from any category. For each: one sentence on what "
    "happened, one sentence on why it matters, and the link.\n"
    "2) Second section (title translated to Azerbaijani: BY TOPIC): other stories "
    "grouped under these themes, skipping empty ones: Region, Diplomacy, "
       "Economy, Technology. Max 2 items per theme, with links. Never repeat a "
    "story from the first section or from another theme.\n"
    "At most two of the TOP 3 may be about the same conflict or country. "
"In 'why it matters', stay close to the facts in the headline and clearly "
"mark any inference with the Azerbaijani words 'ehtimal ki'; if the link to Azerbaijan or "
"the South Caucasus is weak, say so instead of forcing one. \n"
    "Use only the items below and only links that appear in them. "
    "Do not invent details or links.\n\n"
    + "\n".join(items)
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)

print(response.text)

all_items_text = "\n".join(items)

for link in re.findall(r"https?://\S+", response.text):
    link = link.rstrip(".,)")
    if link not in all_items_text:
        print("UNKNOWN LINK:", link)

token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

result = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data={"chat_id": chat_id, "text": response.text},
)    

print("Telegram status:", result.status_code)