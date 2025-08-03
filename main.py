# main.py
# A single script to handle authentication, find a specific post, and extract its ID.

import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --- Configuration ---
TARGET_URL = "https://x.com/StoicFaithDad"
# The exact text of the post to find.
TARGET_TEXT = "People often think that Honor and Deception cannot be combined, but this is not true. The greatest men possess both"
AUTH_FILE_PATH = "auth.json"
# Safety limit to prevent infinite scrolling.
MAX_SCROLLS = 100
# A common, realistic User-Agent string to avoid bot detection.[6, 7]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


def main():
    """
    Main function to run the automation.
    Handles a one-time login to create an auth file, then uses it for subsequent runs.
    """
    # --- Part 1: Handle Authentication if auth file does not exist ---
    if not os.path.exists(AUTH_FILE_PATH):
        print(f"Authentication file '{AUTH_FILE_PATH}' not found.")
        print("A browser window will open. Please log in to X.com.")
        print("If you see a CAPTCHA or 'robot' check, solve it manually in the browser window.")
        print("After you have successfully logged in, press ENTER here to continue.")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--start-maximized",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="en-US"
            )
            page = context.new_page()
            page.goto("https://x.com/login")
            input("After you have logged in and see your X.com home page, press ENTER here to continue...")
            import time
            print("Waiting 3 seconds before saving authentication state (to ensure cookies are set)...")
            time.sleep(3)
            try:
                # Save the authentication state (cookies, local storage) to the file.
                context.storage_state(path=AUTH_FILE_PATH)
                print(f"Authentication state successfully saved to '{AUTH_FILE_PATH}'.")
                print("You can now run the script again to find the post.")
            except Exception as e:
                print(f"Error: Could not save authentication state: {e}")
            finally:
                browser.close()
        return  # End the script after creating the auth file.

    # --- Part 2: Find the Post and Extract ID using the auth file ---
    print(f"\nAuthentication file found. Starting the search on {TARGET_URL}.")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--start-maximized",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            storage_state=AUTH_FILE_PATH,
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US"
        )
        page = context.new_page()
        try:
            print(f"Navigating to {TARGET_URL}...")
            page.goto(TARGET_URL, wait_until="domcontentloaded")
            # Wait for posts to load
            page.wait_for_timeout(2000)
            post_locator = page.get_by_text(TARGET_TEXT, exact=True)
            print("Scrolling to find the target post...")
            scroll_count = 0
            while not post_locator.is_visible() and scroll_count < MAX_SCROLLS:
                page.mouse.wheel(0, 1500)
                scroll_count += 1
                print(f"Scroll attempt {scroll_count}/{MAX_SCROLLS}...")
                try:
                    page.wait_for_load_state('networkidle', timeout=5000)
                except PlaywrightTimeoutError:
                    pass
                page.wait_for_timeout(1000)
            if not post_locator.is_visible():
                print("\nCould not find the post after maximum scroll attempts.")
                print("The post may have been deleted or the text may have changed.")
                return
            print("Post found. Clicking to navigate to its dedicated page...")
            post_locator.click()
            print("Waiting for URL to update...")
            page.wait_for_url("**/status/**", timeout=30000)
            final_url = page.url
            print(f"Navigated to new URL: {final_url}")
            match = re.search(r"/status/(\d+)", final_url)
            if match:
                status_id = match.group(1)
                print(f"\n--- SUCCESS ---")
                print(f"Extracted Status ID: {status_id}")
            else:
                print("\nCould not extract status ID from the final URL.")
        except PlaywrightTimeoutError as e:
            print(f"\nA timeout error occurred: {e}")
            print("This could mean the element was not found, navigation failed, or the page took too long to load.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
        finally:
            try:
                context.storage_state(path=AUTH_FILE_PATH)
                print(f"Updated authentication state saved to '{AUTH_FILE_PATH}'.")
            except Exception as e:
                print(f"Warning: Could not update authentication state: {e}")
            print("Closing browser.")
            browser.close()


if __name__ == "__main__":
    # It's a good idea to delete the old auth.json file if it exists,
    # as it was created with a browser that was getting blocked.
    if os.path.exists(AUTH_FILE_PATH):
        print(
            f"An old '{AUTH_FILE_PATH}' was found. For the best results, consider deleting it and logging in again with the updated script.")
    main()