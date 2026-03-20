from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
import subprocess
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
import os



MAIN_URL="https://cuutruyen.net/mangas/3411"
BASE_DIR = r"E:\Manga"

def setup_driver():
    """Set up Edge WebDriver with user profile and logging disabled."""
    options = webdriver.EdgeOptions()
    options.use_chromium = True
    options.add_argument(r'user-data-dir=C:\Users\Admin\AppData\Local\Microsoft\Edge\User Data')
    options.add_argument(r'--profile-directory=Profile 1')
    options.add_argument("--log-level=3")
    options.add_argument("--disable-logging")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Edge(options=options)
    return driver



def kill_existing_edge():
    """Kill all running Edge processes using Windows taskkill."""
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe'], check=False)
        print("Attempted to kill all Edge processes.")
    except Exception as e:
        print("Could not kill Edge processes:", e)
        
def wait_for_page_load(driver, timeout=10):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def get_chapter_title(driver):
    title_el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
    )
    return sanitize_filename(title_el.text)

def get_manga_title(driver):
    el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.CSS_SELECTOR,
            'div.flex.justify-between.mb-12 > a.flex.items-center'
        ))
    )
    title = el.text.strip()
    print(title)
    return sanitize_filename(title)

def get_next_button(driver):
    try:
        btn = driver.find_element(By.XPATH, '//a[contains(text(), "Chương sau")]')
        return btn
    except:
        return None

def download_images(folder, driver):
    os.makedirs(folder, exist_ok=True)
    # 1. Zoom out or set a massive window size to ensure the whole canvas fits
    # This helps avoid 'stitching' errors in screenshots
    driver.set_window_size(1920, 3000) 
    pages = driver.find_elements(By.CSS_SELECTOR, 'div[id^="page-"]')
    image_index = 1
    for index, page in enumerate(pages):
        try:
            # Scroll to the page
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", page)
            time.sleep(2) # Vital: give the canvas time to swap from 'blurry' to 'HD'

            # 2. Find the target canvas
            try:
                target_canvas = page.find_elements(By.TAG_NAME, "canvas")[1]
                if target_canvas is None:
                    print(f"Canvas not found for page {index}")
                    continue
            except Exception as e:
                print(f"Page {index}: exception {e}.")
                continue

            # 3. JAVASCRIPT TRICK: 
            # Force the canvas to show its TRUE internal resolution on the screen
            # and remove any CSS limits (like max-width) temporarily.
            driver.execute_script("""
                const canvas = arguments[0];
                canvas.style.width = canvas.width + 'px';
                canvas.style.height = canvas.height + 'px';
                canvas.style.maxWidth = 'none';
                canvas.style.position = 'fixed'; // Bring it to the top layer
                canvas.style.top = '0';
                canvas.style.left = '0';
                canvas.style.zIndex = '10000';
            """, target_canvas)

            # 4. Take the screenshot now that it's at 1:1 scale
            file_path = os.path.join(folder, f"{image_index:03}.png")
            target_canvas.screenshot(file_path)

            # 5. RESET: Put it back so the page doesn't break for the next scroll
            driver.execute_script("""
                const canvas = arguments[0];
                canvas.style.width = '';
                canvas.style.height = '';
                canvas.style.maxWidth = '';
                canvas.style.position = '';
                canvas.style.zIndex = '';
            """, target_canvas)

            print(f"Saved full-res page {image_index}")
            image_index += 1

        except Exception as e:
            print(f"Error on page {index}: {e}")

    print(f"Done. Total: {image_index - 1}")

def expand_all_chapters(driver):
    print("Expanding chapter list...")
    while True:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((
                    By.XPATH, '//button[.//div[contains(text(), "Xem thêm")]]'
                ))
            )
            # Check if hidden (display: none)
            if not btn.is_displayed():
                print("No more chapters to load.")
                break

            # Scroll into view (important)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(1)

            # Click
            driver.execute_script("arguments[0].click();", btn)
            print("Clicked 'Xem thêm'")

            # Wait for new content to load
            time.sleep(2)

        except Exception as e:
            print("No more 'Xem thêm' button or error:", e)
            break

def extract_chapter_number(text):
    try:
        return float(text)
    except:
        return 0

def get_all_chapters(driver):
    print("Scanning virtual scroller for chapters...")
    
    # Target the virtual scroller container
    scroller_selector = ".vue-recycle-scroller"
    try:
        scroller = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, scroller_selector))
        )
    except:
        print("Could not find the scroller container.")
        return []

    chapters_dict = {}
    last_height = 0
    
    # Loop and scroll
    while True:
        # Extract what's currently visible
        elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/chapters/"]')
        for el in elements:
            try:
                url = el.get_attribute("href")
                if url not in chapters_dict:
                    # Extract the Number (last span in the first flex div)
                    num_el = el.find_element(By.CSS_SELECTOR, "div.font-bold span:last-child")
                    number = num_el.text.strip()

                    # Extract the Subtitle
                    try:
                        subtitle_el = el.find_element(By.CSS_SELECTOR, "div.truncate.text-left span")
                        subtitle = subtitle_el.text.strip()
                    except:
                        subtitle = ""

                    # Format the full title
                    if subtitle and subtitle != "Không có tiêu đề":
                        full_title = f"Chương {number} - {subtitle}"
                    else:
                        full_title = f"Chương {number}"

                    if number:
                        num_val = extract_chapter_number(number)
                        chapters_dict[url] = {
                            "num": num_val,
                            "title": sanitize_filename(full_title), # Sanitize the whole string
                            "url": url
                        }
            except Exception as e:
                continue

        # Scroll down a bit inside the div
        driver.execute_script("arguments[0].scrollTop += 500;", scroller)
        time.sleep(0.5) # Wait for Vue to swap elements

        # Check if we've reached the bottom
        current_scroll = driver.execute_script("return arguments[0].scrollTop;", scroller)
        if current_scroll == last_height:
            # Try one more time just in case of slow loading
            time.sleep(1)
            current_scroll = driver.execute_script("return arguments[0].scrollTop;", scroller)
            if current_scroll == last_height:
                break
        last_height = current_scroll

    # Convert dict to sorted list
    chapters = list(chapters_dict.values())
    chapters.sort(key=lambda x: x["num"])
    
    print(f"Successfully indexed {len(chapters)} chapters.")
    return chapters

def get_latest_downloaded_chapter(manga_folder):
    if not os.path.exists(manga_folder):
        return None

    existing = set(os.listdir(manga_folder))

    return existing  # return all folders instead of max

def find_starting_chapter(chapters, existing_folders):
    if not existing_folders:
        print("No existing chapters → start from first")
        return chapters[0]

    for chap in chapters:
        if chap["title"] not in existing_folders:
            print(f"Next missing chapter: {chap['title']}")
            return chap

    return None

def main():
    kill_existing_edge()
    driver = setup_driver()
    visited = set()
    try:
        driver.get(MAIN_URL)
        wait_for_page_load(driver)
        # Expand all chapters
        expand_all_chapters(driver)
        # Get manga title
        manga_title = sanitize_filename(
            driver.find_element(By.CSS_SELECTOR, "h1").text
        )
        manga_folder = os.path.join(BASE_DIR, manga_title)
        os.makedirs(manga_folder, exist_ok=True)
        # Get all chapters from list
        chapters = get_all_chapters(driver)
        print(f"Found {len(chapters)} chapters in total:\n {chapters}")
        # Map URL and title
        chapter_map = {chap["url"]: chap["title"] for chap in chapters}
        # Check existing folders
        existing = get_latest_downloaded_chapter(manga_folder)
        # Find where to start
        start_chap = find_starting_chapter(chapters, existing)
        if not start_chap:
            print("All chapters already downloaded.")
            return
        print(f"Starting from: {start_chap['title']}")
        driver.get(start_chap["url"])

        # LOOP chapters
        while True:
            wait_for_page_load(driver)
            time.sleep(4)

            current_url = driver.current_url

            if current_url in visited:
                print("Already visited, stopping.")
                break
            visited.add(current_url)

            # Get chapter title
            chapter_title = chapter_map.get(current_url)

            if not chapter_title:
                print("Fallback to h1 (unexpected)")
                chapter_title = get_chapter_title(driver)
            folder = os.path.join(BASE_DIR, manga_title, chapter_title)
            # Skip if already downloaded
            if os.path.exists(folder):
                print(f"Skipped: {chapter_title}")
            else:
                print(f"Downloading: {chapter_title}")
                download_images(folder, driver)

            # Next chapter
            next_btn = get_next_button(driver)

            if not next_btn:
                print("No next chapter. Done.")
                break

            next_url = next_btn.get_attribute("href")

            if not next_url:
                print("Next has no URL. Done.")
                break

            print(f"➡ Moving to next: {next_url}")
            driver.get(next_url)

            time.sleep(2)
    except Exception as e:
        print("Error during processing loop:", e)
    finally:
        print("Finished.")
        input("Press Enter to exit...")
        driver.quit()


if __name__ == "__main__":
    main()
