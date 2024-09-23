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
#chrome_options.add_argument("--headless")
chrome_options.add_experimental_option("detach", True)
driver = webdriver.Chrome(options=chrome_options)

def extract_date_range(driver):
    def extract_from_text(text):
        date_pattern = r'([A-Za-z]+ \d{1,2}, \d{4})'
        dates = re.findall(date_pattern, text)
        if len(dates) == 2:
            checkin_date = dates[0].split()
            checkout_date = dates[1].split()
            return (checkin_date[1].strip(","), checkin_date[0]), (checkout_date[1].strip(","), checkout_date[0])
        else:
            raise ValueError("Unable to find valid date range in provided text.")

    try:
        event_info = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        ).text
        return extract_from_text(event_info)
    except ValueError:
        print("Failed to extract dates from body text, trying backup method...")
        try:
            date_element = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.ID, 'info_eventDates'))
            )
            return extract_from_text(date_element.text)
        except (ValueError, TimeoutException, NoSuchElementException) as e:
            raise ValueError(f"Unable to find valid date range using both methods: {str(e)}")

def select_date(day, date_type, expected_month):
    expected_month_number = {
        'January': 0, 'February': 1, 'March': 2, 'April': 3,
        'May': 4, 'June': 5, 'July': 6, 'August': 7,
        'September': 8, 'October': 9, 'November': 10, 'December': 11
    }[expected_month]
    
    try:
        WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.ID, f"{date_type}-date"))
        ).click()

        # Construct the id based on date_type, month, and day
        element_id = f"dp_{'in' if date_type == 'check-in' else 'out'}_{expected_month_number}_{day}"
        
        date_element = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.ID, element_id))
        )

        # Highlight the selected element for debugging
        #driver.execute_script("arguments[0].style.border='3px solid red'", date_element)

        # Get the parent <td> element to check month
        month_number = date_element.get_attribute("data-month")

        # Check if the month matches
        if int(month_number) == expected_month_number:
            # If the month matches, click the date element
            date_element.click()
            return True
        else:
            print(f"Month mismatch: found {month_number}, expected {expected_month_number}")
            raise ValueError("Month mismatch")

    except TimeoutException:
        print(f"Timeout occurred while trying to select {date_type} date: {day}")
        raise
    except Exception as e:
        print(f"Error in select_date for {date_type} date {day}: {e}")
        raise

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

def check_hotel_availability(total_hotels):
    fully_booked_hotels = None
    try:
        single_hotel = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='legend-selected']/span[@class='selected']"))
        )
        return {"status": "hotels_available", "message": "1"}
    
    except TimeoutException:
        try:
            hotels_count_element = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.ID, "hotels-count"))
            )
            available_hotels = hotels_count_element.text
            available_hotels_count = int(available_hotels.split()[0])

            if total_hotels is not None:
                fully_booked_hotels = total_hotels - available_hotels_count

            return {"status": "hotels_available", "message": available_hotels_count, "fully_booked_hotels": fully_booked_hotels}
        
        except TimeoutException:
            try:
                no_lodging_message = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, "//h3[@class='message-room' and contains(text(), 'No lodging matches your search criteria')]"))
                )
                if total_hotels is not None:
                    fully_booked_hotels = total_hotels
                return {"status": "fully_booked", "message": "Yes", "fully_booked_hotels": fully_booked_hotels}
            
            except TimeoutException:
                try:
                    fully_booked_message = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "message-room"))
                    )
                    if total_hotels is not None:
                        fully_booked_hotels = total_hotels
                    return {"status": "fully_booked", "message": "Yes", "fully_booked_hotels": fully_booked_hotels}
                
                except TimeoutException:
                    return {"status": "error", "message": "Unexpected page state"}

def make_reservation_page():
    try:
        try:
            dropdown = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.ID, "groupTypeId"))
            )
            try:
                select = Select(dropdown)
                select.select_by_index(1)
                print("Dropdown found and first option selected")
            except:
                print("Proceeding to 'Make Reservation' button")
        except TimeoutException:
            print("Dropdown not found, proceeding to find 'Make Reservation' button")

        make_reservation_button = WebDriverWait(driver, 1).until(
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
    
def check_calendar_exists():
    try:
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.ID, "check-in-date"))
        )
        return True
    except TimeoutException:
        return False
    
def check_view_all_hotels_link():
    try:
        view_all_hotels_link = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'item') and contains(@href, '/hotels/all')]"))
        )
        view_all_hotels_link.click()
        return True
    except TimeoutException:
        print("'View all hotels' link not found")
        return False

def get_total_hotels_count():
    try:
        hotels_count_element = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.ID, "hotels-count"))
        )
        total_hotels = hotels_count_element.text.split()[0]
        return int(total_hotels)
    except (TimeoutException, ValueError):
        print("Unable to get total hotels count")
        return None

def process_url(url):
    driver.get(url)
    
    try:
        accept_cookies()
        driver.execute_script("window.scrollTo(0, 0);")

        if check_calendar_exists():
            print("Calendar found, proceeding with date selection")
        else:
            print("Calendar not found, checking for dropdown or 'Make Reservation' button")
            if make_reservation_page():
                print("Handled dropdown page, proceeding with regular flow")

        if not check_calendar_exists():
            return {"status": "reservations_closed", "message": "No"}
        
        total_hotels = None
        if check_view_all_hotels_link():
            total_hotels = get_total_hotels_count()
            driver.back()  # Go back to the main page
            time.sleep(2)
        
        (checkin_day, checkin_month), (checkout_day, checkout_month) = extract_date_range(driver)
        print(f"check-in day: {checkin_day}, Month: {checkin_month}")
        print(f"check-out day: {checkout_day}, Month: {checkout_month}")
        
        select_date(checkin_day, "check-in", checkin_month)
        select_date(checkout_day, "check-out", checkout_month)
        
        WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.ID, "submitQuickBook"))
        ).click()

        availability = check_hotel_availability(total_hotels)

        return availability
        
    except Exception as e:
        print(f"Error processing {url}: {e}")
        driver.save_screenshot("error_processing_url.png")
        error_message = extract_error_message(e)
        return {"status": "error", "message": str(error_message), "fully_booked_hotels": None}

def main():
    start_time = time.time()
    with open('passkey_urls.csv', 'r', newline='') as input_file, \
        open('updated_passkey_urls.csv', 'w', newline='') as output_file:
        
        reader = csv.DictReader(input_file)
        fieldnames = reader.fieldnames + ['Reservations Open', 'Fully Booked', 'Available Hotels', 'Fully Booked Hotels', 'Error Message']
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()

        total_urls = sum(1 for row in reader)
        input_file.seek(0)
        next(reader)  # Skip header row

        for index, row in enumerate(reader, 1):
            url = row['URLs']
            print(f"Processing URL {index} of {total_urls}: {url}")
            
            result = process_url(url)
            
            status_mapping = {
                'reservations_closed': {'Reservations Open': f'{result['message']}'},
                'fully_booked': {'Reservations Open': 'Yes', 'Fully Booked': f'{result['message']}', 'Fully Booked Hotels': f'{result['fully_booked_hotels']}'},
                'hotels_available': {'Reservations Open': 'Yes', 'Fully Booked': 'No', 'Available Hotels': f'{result['message']}', 'Fully Booked Hotels': f'{result['fully_booked_hotels']}'},
                'error': {'Reservations Open': 'Error', 'Fully Booked': 'Error', 'Available Hotels': 'Error', 'Fully Booked Hotels': 'Error', 'Error Message': f'{result['message']}'}
            }

            if result['status'] in status_mapping:
                row.update(status_mapping[result['status']])

            writer.writerow(row)
            print(f"Completed processing URL {index} of {total_urls}")

    end_time = time.time()
    total_time = end_time - start_time

    print("All URLs have been processed. Results saved in 'updated_passkey_urls.csv'.")
    print(f"Total execution time: {total_time:.2f} seconds")
    driver.quit()

if __name__ == "__main__":
    main()