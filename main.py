# main.py
# Script to handle authentication, find a specific post using fuzzy matching, and extract its ID using Selenium.

import os
import json
import re
import time
from difflib import SequenceMatcher
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Configuration ---
TARGET_URL = "https://x.com/StoicFaithDad/with_replies"
TARGET_TEXT = "Trust's icebreaker: Small talk breaks barriers, fosters comfort. Start with 'How are you?' or 'What's new?' to spark authentic connections and deeper conversations."
AUTH_FILE_PATH = "cookies.json"
MAX_SCROLLS = 100
SIMILARITY_THRESHOLD = 0.90  # 90% similarity threshold
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


def normalize_text(text):
    """Normalize text for better matching by removing extra whitespace and converting to lowercase."""
    return ' '.join(text.lower().strip().split())


def calculate_similarity(text1, text2):
    """Calculate similarity ratio between two texts."""
    normalized_text1 = normalize_text(text1)
    normalized_text2 = normalize_text(text2)
    return SequenceMatcher(None, normalized_text1, normalized_text2).ratio()


def find_similar_text_elements(driver, target_text, threshold=0.90):
    """Find elements with text similar to target_text above the threshold."""
    # Get all text elements that might contain tweets
    potential_elements = driver.find_elements(By.XPATH, "//div[@data-testid='tweetText']")

    # Also check span elements that might contain tweet text
    potential_elements.extend(driver.find_elements(By.XPATH, "//span[string-length(text()) > 50]"))

    best_match = None
    best_similarity = 0

    for element in potential_elements:
        try:
            element_text = element.text.strip()
            if len(element_text) < 20:  # Skip very short texts
                continue

            similarity = calculate_similarity(target_text, element_text)

            if similarity >= threshold and similarity > best_similarity:
                best_match = element
                best_similarity = similarity
                print(f"Found potential match (similarity: {similarity:.2f}): {element_text[:100]}...")

        except Exception as e:
            continue  # Skip elements that can't be processed

    return best_match, best_similarity


def save_cookies(driver, path):
    cookies = driver.get_cookies()
    with open(path, 'w') as f:
        json.dump(cookies, f)


def load_cookies(driver, path):
    with open(path, 'r') as f:
        cookies = json.load(f)
    for cookie in cookies:
        driver.add_cookie(cookie)


def main():
    # Set up Chrome options
    options = Options()
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Assume ChromeDriver is in PATH or specify path
    driver = webdriver.Chrome(options=options)

    try:
        # Part 1: Handle Authentication if auth file does not exist
        if not os.path.exists(AUTH_FILE_PATH):
            print(f"Authentication file '{AUTH_FILE_PATH}' not found.")
            print("Browser will open. Log in to X.com manually.")
            print("After login, press ENTER here to continue.")
            driver.get("https://x.com/login")
            input("Press ENTER after successful login...")
            time.sleep(3)  # Ensure cookies set
            save_cookies(driver, AUTH_FILE_PATH)
            print(f"Cookies saved to '{AUTH_FILE_PATH}'.")
            driver.quit()
            return

        # Part 2: Load cookies and find post
        print(f"\nUsing cookies to search on {TARGET_URL}.")
        print(f"Looking for text similar to: {TARGET_TEXT}")
        print(f"Similarity threshold: {SIMILARITY_THRESHOLD * 100}%")

        driver.get("https://x.com")  # Load base to add cookies
        load_cookies(driver, AUTH_FILE_PATH)
        driver.get(TARGET_URL)

        # Wait for page load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        print("Scrolling to find the target post...")
        scroll_count = 0
        last_height = driver.execute_script("return document.body.scrollHeight")
        best_overall_match = None
        best_overall_similarity = 0

        while scroll_count < MAX_SCROLLS:
            # Check for similar text on current page
            match_element, similarity = find_similar_text_elements(driver, TARGET_TEXT, SIMILARITY_THRESHOLD)

            if match_element and similarity > best_overall_similarity:
                best_overall_match = match_element
                best_overall_similarity = similarity

                # If we found a very good match (95%+), we can stop searching
                if similarity >= 0.95:
                    print(f"Excellent match found (similarity: {similarity:.2f})!")
                    break

            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            scroll_count += 1
            print(f"Scroll attempt {scroll_count}/{MAX_SCROLLS}... (Best match so far: {best_overall_similarity:.2f})")
            time.sleep(2)  # Initial wait
            start_time = time.time()
            while time.time() - start_time < 8:  # Up to additional 8s (total 10s)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height > last_height:
                    break
                time.sleep(1)  # Check every second
            last_height = new_height if new_height > last_height else last_height

        if not best_overall_match:
            print(f"\nNo post found with similarity >= {SIMILARITY_THRESHOLD * 100}% after {MAX_SCROLLS} scrolls.")
            print("Try lowering the SIMILARITY_THRESHOLD or increasing MAX_SCROLLS.")
            return

        print(f"\nBest match found with similarity: {best_overall_similarity:.2f}")
        print(f"Matched text: {best_overall_match.text[:200]}...")
        print("Clicking to navigate...")

        # Scroll to element and click
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", best_overall_match)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", best_overall_match)

        # Wait for URL update
        WebDriverWait(driver, 30).until(EC.url_contains("/status/"))

        final_url = driver.current_url
        print(f"Navigated to: {final_url}")

        match = re.search(r"/status/(\d+)", final_url)
        if match:
            status_id = match.group(1)
            print(f"\n--- SUCCESS ---")
            print(f"Extracted Status ID: {status_id}")
            print(f"Final similarity score: {best_overall_similarity:.2f}")
        else:
            print("\nCould not extract ID from URL.")

    except TimeoutException as e:
        print(f"\nTimeout: {e}")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Update cookies
        save_cookies(driver, AUTH_FILE_PATH)
        print(f"Updated cookies saved to '{AUTH_FILE_PATH}'.")
        driver.quit()


if __name__ == "__main__":
    if os.path.exists(AUTH_FILE_PATH):
        print(f"Old '{AUTH_FILE_PATH}' found. Consider deleting for fresh login.")
    main()