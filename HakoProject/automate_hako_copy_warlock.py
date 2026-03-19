from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyperclip
import re
import time
import subprocess
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.ui import WebDriverWait


MAIN_URL_CREATE_CHAPTER_ASURA_TEAM="https://asura.com.vn/my-group/novel/con-trai-ut-nha-ba-tuoc-la-mot-warlock/create-chapter"
MAIN_URL_LIST_HAKO="https://docln.net/truyen/13089-con-trai-ut-cua-ba-tuoc-la-mot-warlock"
MAIN_ASURA_TAB_WINDOW_HANDLE = None
MAIN_HAKO_LIST_TAB_WINDOW_HANDLE = None


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

def get_asura_chapter_title(driver):
    """Get the previous chapter title from Asura input, only load page if needed."""
    global MAIN_ASURA_TAB_WINDOW_HANDLE

    # If we don't know the tab handle, open a new one
    if MAIN_ASURA_TAB_WINDOW_HANDLE is None or MAIN_ASURA_TAB_WINDOW_HANDLE not in driver.window_handles:
        driver.get(MAIN_URL_CREATE_CHAPTER_ASURA_TEAM)
        time.sleep(2)
        MAIN_ASURA_TAB_WINDOW_HANDLE = driver.current_window_handle
    else:
        # Switch to the existing tab
        driver.switch_to.window(MAIN_ASURA_TAB_WINDOW_HANDLE)
        # Check if the current URL matches the Asura create chapter page
        if driver.current_url != MAIN_URL_CREATE_CHAPTER_ASURA_TEAM:
            driver.get(MAIN_URL_CREATE_CHAPTER_ASURA_TEAM)
            time.sleep(2)
    # Get previous chapter title
    input_elem = driver.find_element(By.NAME, "previous_chapter_name")
    chapter_title = input_elem.get_attribute("value")
    print("Detected chapter title:", chapter_title)
    pyperclip.copy(chapter_title)
    return chapter_title


def open_docln_and_click(driver):
    """Open docln.net in a new tab and click 'Xem tiếp' slowly if needed."""
    global MAIN_HAKO_LIST_TAB_WINDOW_HANDLE
    # Check if Docln tab is already open
    if MAIN_HAKO_LIST_TAB_WINDOW_HANDLE is None or MAIN_HAKO_LIST_TAB_WINDOW_HANDLE not in driver.window_handles:
        # Open new tab
        old_tabs = driver.window_handles
        driver.execute_script("window.open('');")
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(old_tabs))
        new_tab = [tab for tab in driver.window_handles if tab not in old_tabs][0]
        driver.switch_to.window(new_tab)
        time.sleep(1)
        driver.get(MAIN_URL_LIST_HAKO)
        MAIN_HAKO_LIST_TAB_WINDOW_HANDLE = driver.current_window_handle
    else:
        # Switch to existing Docln tab
        driver.switch_to.window(MAIN_HAKO_LIST_TAB_WINDOW_HANDLE)
    wait_for_page_load(driver)
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.F5)
    driver.refresh()
    # driver.execute_script("location.reload(true);")
    try:
        # Wait until at least one 'Xem tiếp' button is visible
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.see_more span"))
        )

        # Find all 'Xem tiếp' buttons
        see_more_buttons = driver.find_elements(By.CSS_SELECTOR, "div.see_more span")
        print(f"Found {len(see_more_buttons)} 'Xem tiếp' buttons.")
        
        for i, btn in enumerate(see_more_buttons, 1):
            print(f"Clicking button {i} in 2 seconds...")
            try:
                btn.click()
                print(f"Clicked button {i}!")
                time.sleep(0.5)  # slight delay between clicks
            except Exception as e: pass
    except Exception as e:
        print("No 'Xem tiếp' buttons found or error:", e)



def get_next_chapter_url(driver, current_title):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "ul.list-chapters li div.chapter-name a")
        )
    )

    chapter_links = driver.find_elements(
        By.CSS_SELECTOR,
        "ul.list-chapters li div.chapter-name a"
    )

    current_version = extract_chapter_version(current_title)
    if current_version is None:
        print("❌ Cannot extract chapter version from current title")
        return None

    current_title_norm = normalize_text(current_title)
    start_index = None

    # 1️⃣ Find index of current chapter (your logic, but safer)
    for i, a in enumerate(chapter_links):
        title = a.get_attribute("title") or a.text
        if title and current_title_norm in normalize_text(title):
            start_index = i
            break

    if start_index is None:
        print("❌ Current chapter not found in list")
        return None

    # 2️⃣ Scan FORWARD only, skip junk
    for a in chapter_links[start_index + 1:]:
        title = a.get_attribute("title") or a.text
        version = extract_chapter_version(title)

        # skip non-chapter items (ngoại truyện, pinned, etc.)
        if not version:
            continue

        # must be a REAL next chapter
        if version > current_version:
            next_url = a.get_attribute("href")
            print(f"✅ Next chapter detected: {title}")
            return next_url

    print("❌ No valid next chapter found")
    return None


def go_next_chapter_url_and_work_up(driver, url):
    """Open new chapter in new tab to copy the title and content."""
    old_tabs = driver.window_handles
    driver.execute_script("window.open('');")
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(old_tabs))
    new_tab = [tab for tab in driver.window_handles if tab not in old_tabs][0]
    driver.switch_to.window(new_tab)
    time.sleep(1)
    driver.get(url)
    page_handle = driver.current_window_handle
    wait_for_page_load(driver)  # wait for page to load slowly
    try:
        title_elem  = driver.find_element(By.CSS_SELECTOR, "h4.title-item.text-base")
        new_chapter_title = title_elem.text.strip()
        #Select all <p> under #chapter-content and copy to clipboard like manual selection.
        
        container = driver.find_element(By.ID, "chapter-content")
        paragraphs = container.find_elements(By.TAG_NAME, "p")
        visible_html = "".join([p.get_attribute("outerHTML") for p in paragraphs if p.is_displayed()])

        driver.switch_to.window(MAIN_ASURA_TAB_WINDOW_HANDLE)
        input_elem = driver.find_element(By.XPATH, "//input[@name='chapter_title']")
        input_elem.clear()
        input_elem.send_keys(new_chapter_title)
        
        editor_id = "ckeditor_chapter_content"
        driver.execute_script(f"""
        CKEDITOR.instances['{editor_id}'].setData(`{visible_html}`);
        CKEDITOR.instances['{editor_id}'].fire('change');
        """)
        time.sleep(2) #wait 2s
        
        button = driver.find_element(By.CSS_SELECTOR, "button.px-8.py-3.rounded-xl.bg-blue-600")
        button.click()
        
        #close old tab
        driver.switch_to.window(page_handle)
        driver.close()
        print(f"Successfully uploaded new chapter: {new_chapter_title}")
        
        return
    except Exception as e: 
        print(f"Exception in go_next_chapter_url_and_work_up: {e}")
        pass


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

def extract_chapter_version(title: str):
    """
    Extract chapter version as a tuple of ints.
    Examples:
      Chương 40        -> (40,)
      Chương 40.1      -> (40, 1)
      Chương 40.10     -> (40, 10)
      Chapter 40.1.2   -> (40, 1, 2)
    Returns None if not a chapter.
    """
    if not title:
        return None

    match = re.search(
        r'(?:chương|chapter)\s*([\d\.]+)',
        title,
        re.IGNORECASE
    )

    if not match:
        return None

    version_str = match.group(1)
    return tuple(int(x) for x in version_str.split('.') if x.isdigit())


def normalize_text(s):
    return " ".join(s.strip().lower().split())  # lowercase and collapse all whitespace


def main():
    kill_existing_edge()
    driver = setup_driver()
    MAX_CHAPTERS = 30
    count = 0
    try:
        while count < MAX_CHAPTERS:
            chapter_title = get_asura_chapter_title(driver)
            open_docln_and_click(driver)
            next_url = get_next_chapter_url(driver=driver, current_title=chapter_title)
            if not next_url:
                print("No next chapter found. Stopping.")
                break
            go_next_chapter_url_and_work_up(driver=driver, url=next_url)
            count += 1
            time.sleep(2)
            
    finally:
        print("Automation finished. Keep browser open for inspection.")
        input("Press Enter to exit Python and leave the browser open...")
        driver.quit()


if __name__ == "__main__":
    main()
