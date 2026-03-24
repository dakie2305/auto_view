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
from PIL import Image
import io
import requests
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


MAIN_URL="https://moetruyen.net/manga/147-arika-cua-toi"
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
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, ".reader-title h1")
        )
    )
    return sanitize_filename(title_el.text.strip())

def get_manga_title(driver):
    el = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.CSS_SELECTOR,
            ".reader-title .reader-meta span:first-child"
        ))
    )
    title = el.text.strip()
    print(title)
    return sanitize_filename(title)

def get_next_button(driver):
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH, '//a[@aria-label="Chương sau"]'
            ))
        )
        return btn
    except:
        return None

def download_images(folder, driver):
    os.makedirs(folder, exist_ok=True)

    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, ".reader-pages img.page-media")
        )
    )

    images = driver.find_elements(By.CSS_SELECTOR, ".reader-pages img.page-media")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": driver.current_url
    }

    image_list = []

    print(f"Total images detected: {len(images)}")

    for img in images:
        try:
            index = int(img.get_attribute("data-page-index"))
            # Scroll into view (centered)
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", img
            )
            # Wait until real src is loaded (not empty / not lazy)
            WebDriverWait(driver, 10).until(
                lambda d: img.get_attribute("src") and "data:image" not in img.get_attribute("src")
            )
            url = img.get_attribute("src") or img.get_attribute("data-src")
            if url:
                image_list.append((index, url))
                print(f"Loaded page {index}")

            time.sleep(1)  # small delay to stabilize lazy load

        except Exception as e:
            print(f"Scroll/load failed: {e}")
            continue

    # Sort images
    image_list.sort(key=lambda x: x[0])

    # Download
    for i, (_, url) in enumerate(image_list, start=1):
        try:
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()
            file_path = os.path.join(folder, f"{i:03}.jpg")
            img = Image.open(io.BytesIO(res.content)).convert("RGB")
            img.save(
                file_path,
                "JPEG",
                quality=100,
                subsampling=0,
                optimize=True
            )
            print(f"Saved page {i}")
        except Exception as e:
            print(f"Failed page {i}: {e}")

    print(f"Done. Total: {len(image_list)}")
    

def save_as_jpg(webp_bytes, output_path):
    img = Image.open(io.BytesIO(webp_bytes)).convert("RGB")

    img.save(
        output_path,
        "JPEG",
        quality=100,          # max quality
        subsampling=0,        # disable chroma subsampling
        optimize=True
    )
    
import os
import re

def get_latest_chapter_folder(manga_folder):
    try:
        if not os.path.exists(manga_folder):
            print(f"Path does not exist: {manga_folder}")
            return None

        # Get all subdirectories
        all_subfolders = [
            d for d in os.listdir(manga_folder)
            if os.path.isdir(os.path.join(manga_folder, d))
        ]

        # Only keep folders that contain a number (e.g., "Chương 16", "Ch. 5")
        chapter_folders = [
            f for f in all_subfolders 
            if re.search(r'\d+', f)
        ]

        if not chapter_folders:
            print("No folders containing numbers found.")
            return None

        # Sort the filtered list by Modified Time (Newest First)
        chapter_folders.sort(
            key=lambda x: os.path.getmtime(os.path.join(manga_folder, x)), 
            reverse=True
        )

        latest_name = chapter_folders[0]
        print(f"Latest actual chapter found: {latest_name}")
        return latest_name

    except Exception as e:
        print(f"Error in get_latest_chapter_folder: {e}")
        return None

def extract_chapter_number(text):
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    return float(match.group(1)) if match else None

def find_chapter_url(driver, latest_chapter):
    try:
        target_num = extract_chapter_number(latest_chapter)
        print(f"Targeting Chapter Number: {target_num}")
        current_page_num = 1 # Start at page 1
        while True:
            wait_for_page_load(driver)
            time.sleep(1)
            chapters = driver.find_elements(By.CSS_SELECTOR, "ul.chapter-list li.chapter")
            print(f"Found {len(chapters)} chapters on Page {current_page_num}.")

            if not chapters:
                print("No chapters found on this page. Stopping.")
                break

            for chap in chapters:
                try:
                    num_el = chap.find_element(By.CSS_SELECTOR, "span.chapter-num")
                    current_num = extract_chapter_number(num_el.text.strip())

                    if current_num == target_num:
                        link = chap.find_element(By.CSS_SELECTOR, "a.chapter-link").get_attribute("href")
                        print(f"Match found: Ch. {current_num} -> {link}")
                        return link
                except:
                    continue

            # If not found, go to the NEXT page (e.g., from page 1 to page 2)
            current_page_num += 1
            if not navigate_to_page(driver, current_page_num):
                print(f"Could not navigate to Page {current_page_num}. Ending search.")
                break
        return None
    except Exception as e:
        print(f"Error finding chapter URL: {e}")
        return None
    
def navigate_to_page(driver, page_num):
    try:
        target_url = f"{MAIN_URL}?chapterPage={page_num}#chapters"
        print(f"Searching further... Moving to {target_url}")
        driver.get(target_url)
        # Verify page loaded
        wait_for_page_load(driver)
        # Check if the list is empty
        chapters = driver.find_elements(By.CSS_SELECTOR, "ul.chapter-list li.chapter")
        return len(chapters) > 0
    except Exception as e:
        print(f"Navigation error: {e}")
        return False

def get_first_chapter_url(driver):
    try:
        base_url = MAIN_URL

        # get pagination links
        pagination_links = driver.find_elements(
            By.CSS_SELECTOR, ".admin-pagination__numbers a"
        )

        page_urls = []

        for link in pagination_links:
            href = link.get_attribute("href")
            if href:
                page_urls.append(href)

        # Always include page 1
        page_urls.append(base_url)

        # Remove duplicates
        page_urls = list(set(page_urls))

        # Sort -> go to LAST page (highest number)
        def extract_page_num(url):
            match = re.search(r'chapterPage=(\d+)', url)
            return int(match.group(1)) if match else 1

        page_urls.sort(key=extract_page_num, reverse=True)

        last_page = page_urls[0]
        print(f"Go to last page: {last_page}")

        driver.get(last_page)
        wait_for_page_load(driver)
        time.sleep(2)

        # Step 2: get all chapters
        chapters = driver.find_elements(By.CSS_SELECTOR, ".chapter-list .chapter")

        if not chapters:
            print("No chapters found")
            return None

        # Step 3: last chapter in list = OLDEST = Ch.1
        first_chapter = chapters[-1]

        link = first_chapter.find_element(
            By.CSS_SELECTOR, "a.chapter-link"
        ).get_attribute("href")

        print(f"First chapter URL: {link}")
        return link

    except Exception as e:
        print(f"Error getting first chapter: {e}")
        return None

def main():
    kill_existing_edge()
    driver = setup_driver()
    visited = set()
    try:
        driver.get(MAIN_URL)
        wait_for_page_load(driver)
        # Get manga title
        manga_title = sanitize_filename(
            driver.find_element(By.CSS_SELECTOR, "h1.manga-detail-title").text.strip()
        )
        print(f"Manga Title: {manga_title}")
        manga_folder = os.path.join(BASE_DIR, manga_title)
        os.makedirs(manga_folder, exist_ok=True)
        #Get latest chapter from folder
        latest_chapter = get_latest_chapter_folder(manga_folder)
        print(f"Latest local chapter: {latest_chapter}")
        if latest_chapter:
            found_url = find_chapter_url(driver, latest_chapter)
            if found_url:
                print(f"Start from: {found_url}")
            else:
                print("Could not find chapter, start from main page")
                found_url = get_first_chapter_url(driver)
        else:
            print("No local chapters, start from beginning")
            found_url = get_first_chapter_url(driver)
        
        if not found_url:
            raise Exception("Cannot determine starting chapter URL")
        
        driver.get(found_url)
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
            chapter_title = get_chapter_title(driver)

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
