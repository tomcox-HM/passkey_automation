import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=chrome_options)

def extract_date_range(event_text):
    import re
    date_pattern = r'([A-Za-z]+ \d{1,2}, \d{4})'
    dates = re.findall(date_pattern, event_text)
    if len(dates) == 2:
        checkin_day = dates[0].split()[1].strip(",")
        checkout_day = dates[1].split()[1].strip(",")
        return checkin_day, checkout_day
    else:
        raise ValueError("Unable to find valid date range in event info.")

def select_date(day, date_type):
    try:
        # Focus on the correct date input field
        date_input = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, f"{date_type}-date"))
        )
        date_input.click()
        
        time.sleep(1)  # Wait for the calendar to open
        
        # Find the date element using JavaScript to interact with it
        date_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//a[@role='button' and @data-date='{day}']"))
        )
        
        # Scroll into view if necessary
        driver.execute_script("arguments[0].scrollIntoView(true);", date_element)
        
        # Click the date element using JavaScript
        driver.execute_script("arguments[0].click();", date_element)
        
        # Optionally, set the date directly to avoid focus issues
        # This part assumes the date format in the input field is 'MM/DD/YYYY'
        formatted_date = f"09/{day}/2024"  # Adjust format if needed
        driver.execute_script(f"document.getElementById('{date_type}-date').value = '{formatted_date}';")

        return True
    except TimeoutException:
        driver.save_screenshot(f"error_{date_type}_{day}.png")
        raise
    except Exception as e:
        print(f"Error in select_date: {e}")
        driver.save_screenshot(f"error_{date_type}_{day}.png")
        raise

with open('passkey_urls.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        url = row['URLs']
        driver.get(url)
        
        try:
            # Check for and click the "Accept Essential Cookies" button if it exists
            try:
                accept_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "acceptEssentialBtn"))
                )
                accept_button.click()
            except TimeoutException:
                print("'Accept Essential Cookies' button not found or not clickable.")

            # Extract the event details block
            event_info = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            ).text
            
            checkin_day, checkout_day = extract_date_range(event_info)
            
            # Select the check-in date
            #select_date(checkin_day, "check-in")
            
            # Select the check-out date
            select_date(checkout_day, "check-out")
            
            # Submit the search form
            submit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "submitQuickBook"))
            )
            submit_button.click()
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
            driver.save_screenshot("error_processing_url.png")
        
        break  # Remove this line to process all URLs

# Keep the browser open for inspection
input("Press Enter to close the browser...")
driver.quit()
