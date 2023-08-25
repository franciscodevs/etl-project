import re
import os
import random
import psycopg2

from geopy.geocoders import GoogleV3
import requests.exceptions

import time
import requests
import numpy as np
import pandas as pd
from time import time
from tqdm import tqdm
from selenium import webdriver
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from sqlalchemy import create_engine
from selenium.webdriver.common.by import By
from prefect import flow, task, get_run_logger
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, InvalidSelectorException, NoSuchElementException, ElementNotVisibleException, InvalidElementStateException

def locate_click(driver, xpath, timeout=10):
    """
    Locates an element by its XPath and waits for it to be clickable

    Args:
        driver (webdriver): The Selenium WebDriver instance
        xpath (str): The XPath of the element to locate
        timeout (int): Maximum time (in seconds) to wait for the element to be clickable 
    
    Returns:
        WebElement: The located and clickable Element
    """
    try:
        resolved = WebDriverWait(driver, timeout=timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        return resolved
    except (TimeoutException,) as ex:
        get_run_logger().error(f'Unable to locate element: {xpath} within {timeout} seconds.')
        raise ex
    except (InvalidSelectorException, ) as ex:
        raise ex
    except (NoSuchElementException, ElementNotVisibleException, InvalidElementStateException, ) as ex:
        raise ex

def wait_table_loaded(driver, xpath):
    """
    Waits until a new table is fully loaded on the web page

    Args:
        driver (webdriver): The Selenium WebDriver instance
        xpath (str): The XPath of the table's first row

    Returns:
        None
    """
    first_row_id_old = WebDriverWait(driver, timeout=10).until(EC.visibility_of_element_located((By.XPATH, xpath))).text
    first_row_id_new = first_row_id_old
    while first_row_id_new == first_row_id_old:
        try:
            first_row_id_new = WebDriverWait(driver, timeout=10).until(EC.visibility_of_element_located((By.XPATH, xpath))).text
        except StaleElementReferenceException:
            continue
    

@task(name='Connect to webdriver', retries=3, retry_delay_seconds=30)
def initialize_driver() -> webdriver:
    """
    Initializes a Chrome WebDriver instance

    Returns:
        webdriver: The Chrome WebDriver instance
    """
    # Configure Chrome Options
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors') 
    options.add_argument("--no-sandbox")
    options.add_argument('--window-size=1366,768')
    options.add_argument('--headless=new') # run in 'headless' mode
    options.add_argument("--disable-extensions") # disable extensions
    options.add_argument("--disable-dev-shm-usage") # overcome limited resource problems
    
    # Create remote WebDriver instance
    driver = webdriver.Remote(
    command_executor='http://chrome:4444/wd/hub', #chrome from container host: 'chrome'
    options=options
)
    return driver

@task(name='Load page')
def get_headers(driver, url):
    """
    Loads a web page and extracts table headers

    Args: 
        driver (webdriver): The Selenium WebDriver instance
        url (str): The URL of the web page
    
    Returns:
        Tuple[webdriver, dict, list]: The WebDriver instance, data dictionary, and table headers
    """
    # Navigate web page
    driver.get(url)
    # Wait till table loads
    WebDriverWait(driver, timeout=10).until(EC.presence_of_element_located((By.CLASS_NAME, 'row-border')))
    #Extract headers to a list
    table_header = driver.find_elements(By.XPATH, '//table[@id]//th')
    headers = [th.text for th in table_header[4:]]
    #Create a dict to save data 
    data = {key:[] for key in headers}

    return driver, data, headers


@task(name='Extracting table data')
def extract_table(driver, data, headers) -> pd.DataFrame:
    """
    Extracts table data from a web page using Webdriver

    Args:
        driver(webdriver): The Selenium WebDriver instance
        data (dict): A dictionary to store extracted data
        headers (list): List of table headers

    ReturnsL:
        pd.DataFrame: Extracted table data as a DAtaFrame
    """
    # # Navigate web page
    # driver.get("https://www.bancoprovincia.com.ar/cuentadni/buscadores/carniceriasymas")
    # # Wait till table loads
    # # WebDriverWait(driver, timeout=10).until(EC.presence_of_element_located((By.CLASS_NAME, 'row-border')))
    WebDriverWait(driver,timeout=10).until(EC.visibility_of_element_located((By.XPATH, '//table[@id]/tbody/tr[1]'))).text
    # Number of records on table
    text = driver.find_element(By.XPATH, '//*[@id="table_id_info"]')
    num = int(re.findall(r'\d[\d\.]*', text.text)[-1].replace('.', ''))
    # Progress bar
    e_start = time()
    with tqdm(total=num, unit_scale=True, desc=f'Extracting {num} records...', 
    bar_format="{l_bar}{bar} [time left: {remaining}, time spent: {elapsed}]") as pbar:
    #Loop
        while True:

            for idx in range(1,5):
            # Looping through every column in table (way faster than row looping) and extracting data to a dict
                raw_data = driver.execute_script(
                    "var result = [];" + f"var all = document.querySelectorAll('tbody>tr>td:nth-child({idx})');" +
                    "for (var i=0; i<all.length; i++) {" +
                    "    var cell = all[i]; " +
                    "    var idx = cell.cellIndex + 1; " +
                    "    if (idx === all[all.length-1].cellIndex+1 && cell.querySelector('.boton_ir')) { " +
                    "        var match = cell.querySelector('.boton_ir').getAttribute('onclick').match(/\(([-+]?\d+\.\d+),\s*([-+]?\d+\.\d+)/);" +
                    "        if (match) { " +
                    "            var lat = match[1];" +
                    "            var lng = match[2];" +
                    "            result.push(lat+ ',' +lng);" +
                    "        }else { " +
                    "            result.push('')" +
                    "        }" +
                    "    }else{ " +
                    "        result.push(cell.innerText.trim());" +
                    "    } " +
                    "}" +   
                    "return result;")
                data[headers[idx-1]] += raw_data
            pbar.update(len(raw_data))
            # Create button for next_click
            next_button = locate_click(driver, xpath='//*[@id="table_id_next"]')
            #Click on next button
            if 'disabled' not in next_button.get_attribute('class'):
                next_button.click()
            else:
                print("\nNo more records to extract")
                break
            #Wait to next table
            wait_table_loaded(driver, xpath='//table[@id]/tbody/tr[1]')
        e_end = time()
    get_run_logger().info(f"Data extracting lasts {e_end - e_start:.2f} seconds.")
    #Close Browser
    # driver.close()
    # driver.quit()
    #Create DataFrame with data
    df = pd.DataFrame(data)

    return df


@task(name='transform')
def geocode_dataframe(df):
    """
    Geocodes adresses in the DataFrame using the GoogleV3 geocoder

    Args:
        df (pd.DataFrame): Input DataFrame containing adress information

    Returns:
        pd.DataFrame: DataFrame with geocoded coordinates
    """
    # Create a GoogleV3 geolocator instance with your API key
    geolocator = GoogleV3(api_key='YOUR_API_KEY')

    # Initialize variables for geocoding attempts and limits
    attempt = 1
    max_attempts = 5
    timeout = 2

    # Iterate over rows in the DataFrame
    for index, row in df.iterrows():
        # Check if 'Localizar' column value is 'No disponible'
        if row['Localizar'] == 'No disponible':
            # Extract address components from the DataFrame
            direccion = row['Dirección']
            localidad = row['Localidad']
            coordinates = None
            
            # Retry geocoding a limited number of times
            while attempt <= max_attempts:
                try:
                    # Geocode the address using GoogleV3 with a timeout
                    location = geolocator.geocode(f'{direccion}, {localidad}, ARGENTINA', timeout=timeout)
                    coordinates = f"{location.latitude},{location.longitude}"
                    break # Break out of the retry loop on successful geocode
                except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                    get_run_logger().info(f"Timeout, retrying in {timeout} seconds...")
                    time.sleep(timeout)
                    timeout *= 2
                    attempt += 1
                except GeocoderTimedOut:
                    get_run_logger().info(f"Timeout, retrying in {timeout} seconds...")
                    time.sleep(timeout)
                    timeout *= 2
                    attempt += 1
                except AttributeError:
                    # Handle cases where geocoding information is not found and logs
                    get_run_logger().info(f"Could not found location for {direccion}, {localidad}")
                    break

            # Reset timeout for the next attempt
            timeout = 2
            # Update the 'Localizar' column in the DataFrame with coordinates
            df.loc[index, 'Localizar'] = coordinates
   
    # Return the DataFrame with geocoded data
    return df

@task(name='create DB')
def create_db(df):
    """
    Create a PostgreSQL table and ingests data from DataFrame

    Args:
        df(pd.DataFrame): DataFrame containing data to be ingested

    Returns:
        None
    """
    #Create table
    engine = create_engine(f'postgresql://postgres:postgres@database:5432/project')
    df.head(n=0).to_sql(name='table', con=engine, if_exists='replace')
    get_run_logger().info("Table created succesfuly")

    #Ingesting data
    chunksize = 50_00 # Chunksize 
    max_size = len(df.index) # Lenght of DataFrame
    last_run = False # Run condition
    start = 0
    current = chunksize
    overage = 0

    #Progress bar 
    l_start = time()
    with tqdm(total=max_size, unit_scale=True, desc=f'Inserting {max_size} rows...', 
    bar_format="{l_bar}{bar} [time left: {remaining}, time spent: {elapsed}]") as pbar:
        while last_run == False:
            if current > max_size:
                overage = current - max_size
                current = max_size
                chunksize -= overage
                last_run = True
            # Inserting data per chunks (5.000  each)    
            df.iloc[start:current].to_sql(name='table', con=engine, if_exists='append', method='multi')
            
            start = current
            current += chunksize
            pbar.update(chunksize)
        pbar.update(overage)
    l_end = time()
    get_run_logger().info(f'Data ingesting on database lasts {l_end - l_start:.2f} seconds')
            

@flow()
def flow_run():
    """
    Defines a Prefect flow to extract, transform, and load data
    """
    #Extract
    driver = initialize_driver()

     # Carnicerias y mas
    c1 = get_headers(driver, 'https://www.bancoprovincia.com.ar/cuentadni/buscadores/carniceriasymas')
    df1 = extract_table(driver, c1[1], c1[2])
    # Comercios de barrio
    c2 = get_headers(driver, 'https://www.bancoprovincia.com.ar/cuentadni/buscadores/comerciosdebarrio')
    df2 = extract_table(driver, c2[1], c2[2])
    # Concatenate
    result = pd.concat([df1, df2], ignore_index=True).drop_duplicates().reset_index(drop=True)
    # Transform
    df = geocode_dataframe(result)
    #Load
    create_db(df)

if __name__ == '__main__':
    flow_run()


