from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyperclip
import time
import subprocess
from selenium.webdriver.support.ui import WebDriverWait


MAIN_URL_CREATE_CHAPTER_ASURA_TEAM="https://asura.com.vn/my-group/novel/vinh-thoai-hiep-si/create-chapter"
MAIN_URL_LIST_HAKO="https://docln.net/truyen/21180-vinh-thoai-hiep-si"


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
    """Get the previous chapter title from asura.com.vn and copy to clipboard."""
    driver.get(MAIN_URL_CREATE_CHAPTER_ASURA_TEAM)
    time.sleep(2)  # wait for page to load slowly
    input_elem = driver.find_element(By.NAME, "previous_chapter_name")
    chapter_title = input_elem.get_attribute("value")
    print("Detected chapter title:", chapter_title)
    pyperclip.copy(chapter_title)
    print("Copied to clipboard!")
    return chapter_title

def open_docln_and_click(driver):
    """Open docln.net in a new tab and click 'Xem tiếp' slowly."""
    old_tabs = driver.window_handles
    driver.execute_script("window.open('');")
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(old_tabs))
    new_tab = [tab for tab in driver.window_handles if tab not in old_tabs][0]
    driver.switch_to.window(new_tab)
    time.sleep(1)
    driver.get(MAIN_URL_LIST_HAKO)
    wait_for_page_load(driver)  # wait for page to load slowly
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
            except Exception as e: pass
    except Exception as e: pass


def get_next_chapter_url(driver, current_title):
    # Wait for chapter list to appear
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.list-chapters li a"))
    )

    # Get all chapter links
    chapter_links = driver.find_elements(By.CSS_SELECTOR, "ul.list-chapters li div.chapter-name a")
    
    next_url = None
    for i, a in enumerate(chapter_links):
        title = a.get_attribute("title").strip()
        if title.lower() == current_title.strip().lower():  # normalize
            if i + 1 < len(chapter_links):
                next_url = chapter_links[i + 1].get_attribute("href")
            break
    pyperclip.copy(next_url)
    print(f"Copied next url to clipboard: {next_url}")
    return next_url

def go_next_chapter_url(driver, url):
    """Open new chapter in new tab to copy the title and content."""
    old_tabs = driver.window_handles
    driver.execute_script("window.open('');")
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(old_tabs))
    new_tab = [tab for tab in driver.window_handles if tab not in old_tabs][0]
    driver.switch_to.window(new_tab)
    time.sleep(1)
    driver.get(MAIN_URL_LIST_HAKO)
    wait_for_page_load(driver)  # wait for page to load slowly
    try:
        title_elem  = driver.find_element(By.CSS_SELECTOR, "h4.title-item.text-base")
        new_chapter_title = title_elem.text.strip()
        main_tab = [tab for tab in driver.window_handles if tab.current_url == MAIN_URL_CREATE_CHAPTER_ASURA_TEAM]
        if not main_tab:
            print("Main tab is not found! Aborting")
            return
        driver.switch_to.window(main_tab)
        input_elem = driver.find_element(By.XPATH, "//input[@name='chapter_title']")
        input_elem.clear()
        input_elem.send_keys(new_chapter_title)
        return


    except Exception as e: pass










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


def main():
    kill_existing_edge()
    driver = setup_driver()
    try:
        chapter_title = get_asura_chapter_title(driver)
        open_docln_and_click(driver)
        next_url = get_next_chapter_url(driver=driver, current_title=chapter_title)
    finally:
        print("Automation finished. Keep browser open for inspection.")
        input("Press Enter to exit Python and leave the browser open...")
        driver.quit()


if __name__ == "__main__":
    main()
