import os
import sys
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import json
from datetime import datetime
import time


def load_cookies_from_file(file_path):
    """Load cookies from a JSON file."""
    with open(file_path, "r") as f:
        cookies = json.load(f)
    return cookies


def stopping_condition(
    driver, last_height, target_href, timeout_seconds, scroll_count, max_scrolls
):
    """
    Repeatedly evaluate stopping conditions until one of them is met or the timeout expires.
    Conditions evaluated in this order:
      1. Timeout expires (resets each time the function is called).
      2. Maximum number of scrolls is reached.
      3. An 'a' element with the target href is found.

    If new content is loaded (scrollHeight > last_height) and the 'a' element
    with the target href is not found, we continue to the next iteration.
    """
    start_time = time.time()

    while True:
        # Check if timeout is reached.
        if time.time() - start_time >= timeout_seconds:
            sys.stderr.write("Stopping condition met: Timeout expired.\n")
            return True, "timeout"

        # Check if the maximum number of scrolls has been reached.
        if max_scrolls:
            if scroll_count >= max_scrolls:
                sys.stderr.write(
                    "Stopping condition met: Maximum scroll count reached.\n"
                )
                return True, "max_scrolls_reached"

        # Check if new content is loaded.
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height > last_height:
            sys.stderr.write(f"New content loaded.\n")

            # Check if target href is found on the page.
            if target_href:
                try:
                    driver.find_element(By.XPATH, f"//a[@href='{target_href}']")
                    sys.stderr.write(
                        f"Stopping condition met: Target href '{target_href}' found.\n"
                    )
                    return True, "target_href_found"
                except Exception:
                    pass

            sys.stderr.write("Stopping condition met: New content loaded.\n")
            return False, "new_content_loaded"

        # Small sleep to prevent excessive CPU usage in the loop.
        time.sleep(0.1)


def save_response_bodies_from_logs(driver, request_ids_cache):
    # Get performance logs.
    logs = driver.get_log("performance")

    # URL prefix to filter.
    url_prefix = "https://x.com/i/api/graphql/-SxYPSmLFV7fnFq_-Q-UVg/Likes"

    output_dir = "response_bodies/"
    os.makedirs(output_dir, exist_ok=True)

    # Iterate over performance logs.
    for log in logs:
        try:
            message = json.loads(log["message"])

            # Check if it's a 'Network.responseReceived' event.
            if message["message"]["method"] == "Network.responseReceived":
                response_data = message["message"]["params"]["response"]
                request_id = message["message"]["params"]["requestId"]

                if request_id in request_ids_cache:
                    continue

                url = response_data.get("url", "")

                if url.startswith(url_prefix):
                    # Get the response body using `Network.getResponseBody`.
                    response_body = driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": request_id}
                    )

                    # Parse the body field, assuming it is JSON.
                    if "body" in response_body:
                        body_json = json.loads(response_body["body"])

                        # Save prettified JSON to a file.
                        filename = os.path.join(
                            output_dir, f"response_{request_id}.json"
                        )
                        with open(filename, "w") as f:
                            json.dump(body_json, f, indent=2)

                        print(f"Saved response body for URL: {url} to {filename}")
                        request_ids_cache.append(request_id)

        except Exception as e:
            # Log detailed information about the error.
            import traceback

            sys.stderr.write(f"Error processing log entry: {e}\n")
            sys.stderr.write(f"Traceback:\n{traceback.format_exc()}\n")
            sys.stderr.write(
                f"Log entry that caused the error: {json.dumps(log, indent=2)}\n"
            )

    # Return updated cache.
    return request_ids_cache


def capture_network_traffic(
    url, cookie_file, timeout_seconds, max_scrolls, target_href, headless=False
):
    chrome_options = webdriver.ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless")

    # Enable Chrome DevTools Protocol for network monitoring.
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Network.enable", {})

    try:
        # Load the page initially.
        driver.get(url)

        # Load cookies from file.
        cookies = load_cookies_from_file(cookie_file)
        for cookie in cookies:
            driver.add_cookie(cookie)

        # Refresh the page to apply cookies.
        # We don't use `refresh` because they may have redirected us to a
        # different page for not being logged in.
        driver.get(url)

        # Initialize scrolling
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        request_ids_cache = []

        # Scroll until stopping condition is met.
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Check the stopping condition.
            should_stop, reason = stopping_condition(
                driver,
                last_height,
                target_href,
                timeout_seconds,
                scroll_count,
                max_scrolls,
            )
            if should_stop:
                break

            # Update last height for the next iteration.
            last_height = driver.execute_script("return document.body.scrollHeight")

            scroll_count += 1

            request_ids_cache = save_response_bodies_from_logs(
                driver, request_ids_cache
            )

    finally:
        driver.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download liked tweets by capturing network traffic with Selenium"
    )
    parser.add_argument(
        "cookie_file", type=str, help="Path to the JSON file containing cookies."
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run Chrome in headless mode."
    )
    parser.add_argument("profile_name", type=str, help="Twitter profile name")
    parser.add_argument(
        "--timeout_seconds", type=int, default=5, help="Timeout in seconds."
    )
    parser.add_argument(
        "--max_scrolls", type=int, help="Maximum number of scrolls before stopping."
    )
    parser.add_argument(
        "--target_href", type=str, help="Target href to stop when found."
    )
    args = parser.parse_args()

    # Ensure that either max_scrolls or target_href is set, but not both.
    if args.max_scrolls is not None and args.target_href is not None:
        sys.stderr.write(
            "Error: You cannot set both --max_scrolls and --target_href.\n"
        )
        sys.exit(1)
    if args.max_scrolls is None and args.target_href is None:
        sys.stderr.write("Error: You must set either --max_scrolls or --target_href.\n")
        sys.exit(1)

    url = f"https://x.com/{args.profile_name}/likes"

    capture_network_traffic(
        url,
        cookie_file=args.cookie_file,
        timeout_seconds=args.timeout_seconds,
        max_scrolls=args.max_scrolls,
        target_href=args.target_href,
        headless=args.headless,
    )
