import csv
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=chrome_options)

def extract_date_range(driver):
    def extract_from_text(text):
        date_pattern = r'([A-Za-z]+ \d{1,2}, \d{4})'
        dates = re.findall(date_pattern, text)
        if len(dates) == 2:
            checkin_day = dates[0].split()[1].strip(",")
            checkout_day = dates[1].split()[1].strip(",")
            return checkin_day, checkout_day
        else:
            raise ValueError("Unable to find valid date range in provided text.")

    try:
        # First, try to extract from the entire body
        event_info = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        ).text
        return extract_from_text(event_info)
    except ValueError:
        print("Failed to extract dates from body text, trying backup method...")
        try:
            # Backup method: try to extract from the specific element
            date_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'info_eventDates'))
            )
            return extract_from_text(date_element.text)
        except (ValueError, TimeoutException, NoSuchElementException) as e:
            raise ValueError(f"Unable to find valid date range using both methods: {str(e)}")

def select_date(day, date_type):
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, f"{date_type}-date"))
        ).click()

        time.sleep(5)
        
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[@class='ui-state-default' and @data-date='{day}']"))
        ).click()

        time.sleep(5)

        print(f"Successfully selected {date_type} date: {day}")
        return True

    except TimeoutException:
        print(f"Timeout occurred while trying to select {date_type} date: {day}")
        raise
    except Exception as e:
        print(f"Error in select_date for {date_type} date {day}: {e}")
        raise

def check_reservations_closed():
    reservations_closed = False
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Reservations are closed')]"))
        )
        reservations_closed = True
    except TimeoutException:
        pass

    try:
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'The group rate is no longer available')]"))
        )
        reservations_closed = True
    except TimeoutException:
        pass

    return reservations_closed

def accept_cookies():
    try:
        accept_button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.ID, "acceptEssentialBtn"))
        )
        accept_button.click()
    except TimeoutException:
        print("'Accept Essential Cookies' button not found or not clickable.")

def extract_error_message(error):
    error_lines = str(error).split('\n')
    main_error = error_lines[0].strip()
    
    if main_error == "" or main_error == "Message:":
        main_error = error_lines[1].strip() if len(error_lines) > 1 else "Unknown error"
    
    if main_error.startswith("Message:"):
        main_error = main_error[8:].strip()
    
    return main_error        

def check_hotel_availability():
    return {"status": "hotels_available", "message": 0}

def make_reservation_page():
    try:
        # Check if the dropdown is present
        try:
            dropdown = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "groupTypeId"))
            )
            # If dropdown is found, select the first option
            try:
                select = Select(dropdown)
                select.select_by_index(1)
                print("Dropdown found and first option selected")
            except:
                print("Proceeding to 'Make Reservation' button")
        except TimeoutException:
            print("Dropdown not found, proceeding to find 'Make Reservation' button")

        # Look for the "Make Reservation" button
        make_reservation_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Make Reservation') or @id='submit-btn']"))
        )
        make_reservation_button.click()

        return True
    except TimeoutException:
        print("Neither dropdown nor 'Make Reservation' button found within the timeout period")
        return False
    except Exception as e:
        print(f"Error handling initial page: {e}")
        return False

def process_url(url):
    driver.get(url)
    
    try:
        accept_cookies()

        driver.execute_script("window.scrollTo(0, 0);")

        if make_reservation_page():
            print("Handled dropdown page, proceeding with regular flow")

        if check_reservations_closed():
            print(f"Reservations are closed for {url}")
            return {"status": "reservations_closed", "message": "No"}
        
        checkin_day, checkout_day = extract_date_range(driver)
        
        select_date(checkin_day, "check-in")
        select_date(checkout_day, "check-out")
        
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "submitQuickBook"))
        ).click()
        
        availability = check_hotel_availability()
        return availability
        
    except Exception as e:
        print(f"Error processing {url}: {e}")
        driver.save_screenshot("error_processing_url.png")
        error_message = extract_error_message(e)
        return {"status": "error", "message": str(error_message)}

def main():
    with open('passkey_urls.csv', 'r', newline='') as input_file, \
        open('updated_passkey_urls.csv', 'w', newline='') as output_file:
        
        reader = csv.DictReader(input_file)
        fieldnames = reader.fieldnames + ['Reservations Open', 'Fully Booked', 'Available Hotels', 'Error Message']
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()

        count = 0 

        for row in reader:
            if count >= 20:
               break

            url = row['URLs']
            result = process_url(url)
            
            status_mapping = {
                'reservations_closed': {'Reservations Open': f'{result['message']}'},
                'fully_booked': {'Reservations Open': 'Yes', 'Fully Booked': f'{result['message']}'},
                'hotels_available': {'Reservations Open': 'Yes', 'Fully Booked': 'No', 'Available Hotels': f'{result['message']}'},
                'error': {'Reservations Open': 'Error', 'Fully Booked': 'Error', 'Available Hotels': 'Error', 'Error Message': f'{result['message']}'}
            }

            if result['status'] in status_mapping:
                row.update(status_mapping[result['status']])

            writer.writerow(row)

            count += 1

    input("Press Enter to close the browser...")
    driver.quit()

if __name__ == "__main__":
    main()