# X-Post-Scraper

A Python script to find a specific X (Twitter) post by fuzzy text matching and grab its ID using Selenium.

## Requirements

- Python 3.12+
- Selenium (`pip install selenium`)
- ChromeDriver (matches your Chrome version)
- Chrome browser

## Setup

1. Clone the repo: `git clone <repo-url>`
2. Install deps: `pip install -r requirements.txt` (or just `pip install selenium`)
3. Run locally to generate `cookies.json`: Delete any old one, then `python main.py` and log in manually.

## Usage

- Edit `TARGET_TEXT` in `main.py` to your post text.
- Run: `python main.py`
- It scrolls the profile (`/with_replies`), finds ~90% similar text, clicks, and extracts `/status/ID`.

## Notes

- Handles fuzzy matches (ignores minor punctuation diffs).
- May need more scrolls for old posts; adjust `MAX_SCROLLS`.
- Cookies expire; relog if auth fails.
