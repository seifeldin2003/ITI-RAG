from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1000, "height": 750})
    page.goto("http://127.0.0.1:8501", wait_until="networkidle")
    time.sleep(1.5)
    page.screenshot(path="docs/screenshots/01_landing.png")
    print("saved 01_landing.png")

    # Ask a real question through the real UI
    chat_input = page.get_by_placeholder("e.g. my BMW X6 can't put on drive mode")
    chat_input.click()
    chat_input.fill("my BMW X6 can't put on drive mode, what's wrong")
    chat_input.press("Enter")

    # Wait for the spinner to appear and then disappear (real generation takes ~45-50s)
    page.wait_for_selector("text=Looking through recall", timeout=10000)
    print("spinner appeared, waiting for answer (real LLM generation, ~45-50s)...")
    page.wait_for_selector("text=Looking through recall", state="detached", timeout=90000)
    time.sleep(1)
    page.screenshot(path="docs/screenshots/02_answer.png", full_page=True)
    print("saved 02_answer.png")

    browser.close()
