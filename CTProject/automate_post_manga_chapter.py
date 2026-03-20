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



MAIN_URL="https://asura.com.vn/my-group/manga/spy-x-family/create-chapter"
BASE_DIR = r"E:\Manga\Spy x Family (FULL HD)"
MAX_TABS = 3

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

def get_previous_chapter_title(driver):
    el = driver.find_element(
        By.NAME, "previous_chapter_name"
    )
    return el.get_attribute("value").strip()

def get_next_chapter_folder(base_dir, previous_title):
    folders = [
        f for f in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, f))
    ]
    folders = sorted(
        folders,
        key=lambda x: extract_chapter_number(x)
    )
    print("Folders:", folders)
    if previous_title not in folders:
        raise Exception(f"Previous chapter not found in folders: {previous_title}")
    index = folders.index(previous_title)
    if index + 1 >= len(folders):
        print("No next chapter.")
        return None
    next_folder = folders[index + 1]
    print(f"Next chapter: {next_folder}")
    return next_folder

def extract_chapter_number(title):
    match = re.search(r'(\d+(\.\d+)?)', title)
    if match:
        return float(match.group(1))
    return -1

def fill_chapter_title(driver, title):
    input_el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "chapter_title"))
    )
    input_el.clear()
    input_el.send_keys(title)
    print(f"Filled: {title}")
    
def get_sorted_image_paths(folder_path):
    """Get all image paths from the folder, sorted alphabetically."""
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
    files = [
        os.path.abspath(os.path.join(folder_path, f)) 
        for f in os.listdir(folder_path) 
        if f.lower().endswith(valid_extensions)
    ]
    # Sort naturally (so 2.png comes before 10.png)
    files.sort(key=lambda f: [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', f)])
    return files

def upload_images(driver, folder_path):
    """Finds the file input and sends all image paths to it."""
    print(f"Preparing to upload images from: {folder_path}")
    
    # Get the list of files
    image_paths = get_sorted_image_paths(folder_path)
    if not image_paths:
        print("No images found in the folder!")
        return

    all_files_string = "\n".join(image_paths)

    file_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
    )

    # 4. Upload
    file_input.send_keys(all_files_string)
    print(f"Successfully sent {len(image_paths)} images to the upload zone.")

def click_submit_button(driver):
    btn = driver.find_element(
        By.XPATH,
        '//button[@type="submit" and .//span[contains(text(), "Đăng Chương Mới")]]'
    )
    btn.click()

def wait_until_upload_done(driver):
    # Increase timeout to 600
    wait = WebDriverWait(driver, 600)
    # Wait for the progress bar to hit 100%
    wait.until(
        lambda d: "100%" in d.find_element(By.CSS_SELECTOR, 'div.bg-green-600').get_attribute("style")
    )
    print("Upload confirmed at 100%.")
    
    
def get_all_local_folders(base_dir):
    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    folders.sort(key=lambda x: extract_chapter_number(x))
    return folders

def process_tab(driver, folder_name):
    try:
        driver.get(MAIN_URL)
        # Fill Title
        fill_chapter_title(driver, folder_name)
        # Upload Images
        full_path = os.path.join(BASE_DIR, folder_name)
        upload_images(driver, full_path)
        # Submit
        click_submit_button(driver)
        print(f"Started upload for: {folder_name}")
        return True
    except Exception as e:
        print(f"Error starting {folder_name}: {e}")
        return False
    
def main():
    kill_existing_edge()
    driver = setup_driver()
    # Check the website once to see where we left off
    driver.get(MAIN_URL)
    web_previous_title = get_previous_chapter_title(driver)
    print(f"Website last finished: {web_previous_title}")
    # Get all local folders naturally sorted
    all_folders = get_all_local_folders(BASE_DIR)
    try:
        # find the index of what the website HAS finished, and start from the next one
        current_idx = all_folders.index(web_previous_title) + 1
    except ValueError:
        print(f"Error: Folder '{web_previous_title}' not found in {BASE_DIR}")
        return

    active_uploads = {} # {window_handle: folder_name}

    # ORCHESTRATION LOOP
    while current_idx < len(all_folders) or active_uploads:
        # A. Fill empty slots up to MAX_TABS
        while len(active_uploads) < MAX_TABS and current_idx < len(all_folders):
            next_folder = all_folders[current_idx]
            current_idx += 1 # Increment immediately so the next tab gets the NEXT folder
            
            # Open new tab and switch to it
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            
            print(f"Assigning {next_folder} to a new tab...")
            if process_tab(driver, next_folder):
                active_uploads[driver.current_window_handle] = next_folder
            else:
                # If tab failed to initialize, close it and step back
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                current_idx -= 1 

        # B. Monitor active tabs for the 100% green bar
        handles = list(active_uploads.keys())
        for handle in handles:
            try:
                driver.switch_to.window(handle)
                # Your 100% check logic
                progress_bar = driver.find_element(By.CSS_SELECTOR, 'div.bg-green-600')
                if "100%" in progress_bar.get_attribute("style"):
                    print(f"Finished: {active_uploads[handle]}")
                    del active_uploads[handle]
                    driver.close()
                    # Keep driver focus on a valid handle
                    if driver.window_handles:
                        driver.switch_to.window(driver.window_handles[0])
            except Exception:
                # Tab might have closed or element not found yet
                continue
        time.sleep(5) # Poll every 5 seconds

    print("All available local folders have been processed.")
    driver.quit()

if __name__ == "__main__":
    main()
