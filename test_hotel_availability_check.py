import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Initialize the WebDriver (Make sure to have the correct path for your ChromeDriver)
driver = webdriver.Chrome()

def check_hotel_availability():
    time.sleep(20)
    # Wait for the new page to load and check for available hotels or fully booked status
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "hotels-count"))
        )
        # If this element is present, hotels are available
        available_hotels = driver.find_element(By.ID, "hotels-count").text
        available_hotels_count = available_hotels.split()[0]
        return {"status": "hotels_available", "message": available_hotels_count}
    
    except TimeoutException:
        # Check for the fully booked message if the hotels count is not found
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "message-room"))
            )
            return {"status": "fully_booked", "message": "Yes"}
        except TimeoutException:
            return {"status": "error", "message": "Unexpected page state."}

def test_check_hotel_availability(url):
    driver.get(url)
    
    # Allow some time for the page to load
    time.sleep(5)  # Adjust this sleep as necessary for your specific page load time
    
    result = check_hotel_availability()
    print(result)

# Replace 'your_test_url_here' with the actual URL you want to test
test_url = 'https://book.passkey.com/event/50856363/owner/1482103/list/hotels'
test_check_hotel_availability(test_url)

# Close the driver after the test
driver.quit()
