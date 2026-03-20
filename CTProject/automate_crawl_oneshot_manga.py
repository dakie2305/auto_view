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



MAIN_URL="https://cuutruyen.net/mangas/152/chapters/32743"


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
    el = driver.find_element(By.CSS_SELECTOR, 'a[href^="/mangas/"]')
    title = el.text.strip()
    print(title)
    return sanitize_filename(title)


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


def main():
    kill_existing_edge()
    driver = setup_driver()
    try:
        driver.get(MAIN_URL)
        wait_for_page_load(driver)
        time.sleep(5)  # let JS render fully
        # 1. Get title
        manga_title = get_manga_title(driver)
        print("Manga:", manga_title)
        chapter_title = get_chapter_title(driver)
        print("Chapter:", chapter_title)
        folder = f"{manga_title}/{chapter_title}"
        # 2. Attempt to download image
        download_images(folder, driver)
            
    finally:
        print("Automation finished. Keep browser open for inspection.")
        input("Press Enter to exit Python and leave the browser open...")
        driver.quit()


if __name__ == "__main__":
    main()
