# -*- coding: utf-8 -*-

import os
import time

from datetime import datetime
from typing import List, Tuple
from selenium import webdriver


from selenium.common.exceptions import (
    UnexpectedAlertPresentException,
    NoAlertPresentException,
)

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains

def cancel_alert(logger, driver):
    try:
        alert = driver.switch_to_alert()
        if logger:
            logger.info("Alert text: " + alert.text)
        alert.dismiss()
        return True
    except UnexpectedAlertPresentException:
        return False
    except NoAlertPresentException:
        return False
    except:
        return False


def accept_alert(logger, driver):
    try:
        alert = driver.switch_to_alert()
        if logger:
            logger.info("Alert text: " + alert.text)
        alert.accept()
        return True
    except UnexpectedAlertPresentException:
        return False
    except NoAlertPresentException:
        return False
    except:
        return False


def find_element_by_name_or_id(driver, name):
    try:
        elem = driver.find_element_by_name(name)
    except:
        elem = driver.find_element_by_id(name)
    return elem


def scroll_to_bottom(driver):
    while True:
        start_time = datetime.now()
        _scroll_to_bottom(driver)
        passed_time = (datetime.now() - start_time).total_seconds()
        if passed_time < 4:
            break


def _scroll_to_bottom(driver):
    len_of_page = driver.execute_script(
        "window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;"
    )
    match = False
    scroll_count = 0
    while not match:
        last_count = len_of_page
        time.sleep(1)
        len_of_page = driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;"
        )
        scroll_count += 1
        if (last_count == len_of_page) or scroll_count > 500:
            match = True


def find_visible_element(
    driver, by: str, possible_values: List[str], timeout=60
) -> Tuple[WebElement, str]:
    start_at = datetime.now()
    found_element = None
    found_value = None
    while (datetime.now() - start_at).total_seconds() < timeout and not found_element:
        for value in possible_values:
            try:
                tmp_elem = WebDriverWait(driver, 1).until(
                    EC.visibility_of_element_located((by, value))
                )
                if tmp_elem:
                    found_element = tmp_elem
                    found_value = value
            except KeyboardInterrupt:
                break
            except:
                pass
    if not found_element:
        return None, None
    return found_element, found_value


def find_clickable_element(
    driver, by: str, possible_values: List[str], timeout=60
) -> Tuple[WebElement, str]:
    start_at = datetime.now()
    found_element = None
    found_value = None
    while (datetime.now() - start_at).total_seconds() < timeout and not found_element:
        for value in possible_values:
            try:
                tmp_elem = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((by, value))
                )
                if tmp_elem:
                    found_element = tmp_elem
                    found_value = value
            except KeyboardInterrupt:
                break
            except:
                pass
    if not found_element:
        return None, None
    return found_element, found_value


def capture_for_debug(driver: webdriver.Chrome, name=None):
    now = datetime.now()
    if not name:
        name = "screenshot"
    png_filename = "%s_%s.png" % (name, now.strftime("%Y%m%d%H%M%S"))
    html_filename = "%s_%s.html" % (name, now.strftime("%Y%m%d%H%M%S"))
    try:
        alert_accepted = accept_alert(None, driver)
        while alert_accepted:
            time.sleep(0.5)
            alert_accepted = accept_alert(None, driver)

        screenshot_saved = driver.get_screenshot_as_file(png_filename)
        with open(html_filename, "wt") as file:
            s = "%s\n%s" % (driver.current_url, driver.page_source)
            file.write(s)
        return screenshot_saved
    except:
        pass


def wait_until_urls_prefixes(
    driver: webdriver.Chrome, urls: List[str], wait_timeout=120
) -> str:
    current_url = driver.current_url
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < wait_timeout:
        current_url = driver.current_url
        for url in urls:
            if current_url.startswith(url):
                return url
        time.sleep(0.2)
    return None


def click(driver: webdriver.Chrome, elem: WebElement):
    builder = ActionChains(driver)
    builder.move_to_element(elem).click(elem).perform()
