# -*- coding: utf-8 -*-

import os
import logging
import requests
from enum import Enum
from abc import ABC, abstractmethod

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from PIL import Image
import pyinputplus as pyip

from ..util import selenium

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36"


class BotState(Enum):
    INIT = 0
    SIGNED_IN = 1
    WAITING_TO_BET = 2
    BET_PLACED = 4
    INSUFFICIENT_FUND = 5
    OUT_OF_FUND = 6
    PROFIT_REACHED = 7


class BaseBot(ABC):
    def __init__(self, headless: bool = True, download_dir: str = None):
        if not download_dir:
            download_dir = os.getcwd()
        options = Options()
        options.add_argument(f"--user-agent={USER_AGENT}")
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
            },
        )
        options.add_argument("no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-dev-shm-usage")
        options.headless = headless
        self.driver = webdriver.Chrome(options=options)
        self.driver.maximize_window()

    def sign_in(self, username: str, password: str):
        # Go to csgoempire.com
        self.driver.get("https://csgoempire.com")

        # Wait for the sign in button and click it
        sign_in_btn, _ = selenium.find_clickable_element(
            self.driver, By.PARTIAL_LINK_TEXT, ["Sign In"]
        )
        sign_in_btn.click()

        # Wait for the steam sign in page
        selenium.wait_until_urls_prefixes(
            self.driver, ["https://steamcommunity.com/openid/login"]
        )

        # Sign in to Steam
        username_input, _ = selenium.find_clickable_element(
            self.driver, By.ID, ["steamAccountName"]
        )
        username_input.send_keys(username)
        password_input, _ = selenium.find_clickable_element(
            self.driver, By.ID, ["steamPassword"]
        )
        password_input.send_keys(password)
        captcha_img, _ = selenium.find_visible_element(
            self.driver, By.ID, ["captchaImg"], timeout=3
        )
        if captcha_img:
            captcha_img.screenshot("captcha.png")
            Image.open("captcha.png").show()
            captcha_val = pyip.inputStr("Enter the captcha: ", strip=True)
        sign_in_btn, _ = selenium.find_clickable_element(
            self.driver, By.ID, ["imageLogin"], timeout=10
        )
        sign_in_btn.click()
        steam_code = pyip.inputStr("Enter Steam code: ", strip=True)
        # Use this if OTP is sent by email
        # code_input, _ = selenium.find_visible_element(self.driver, By.ID, ["authcode"])

        # Uss this for mobile authenticator
        code_input, _ = selenium.find_visible_element(self.driver, By.ID, ["twofactorcode_entry"])
        code_input.send_keys(steam_code)

        # Use this if OTP is sent by email
        # submit_btn, _ = selenium.find_clickable_element(
        #     self.driver, By.XPATH, ['//*[@id="auth_buttonset_entercode"]/div[1]']
        # )

        # Use this if OTP is sent by email
        submit_btn, _ = selenium.find_clickable_element(
            self.driver, By.XPATH, ['//*[@id="login_twofactorauth_buttonset_entercode"]/div[1]']
        )
        submit_btn.click()

        # Enable this if OTP is sent by email
        # proceed_to_stream_btn, _ = selenium.find_clickable_element(
        #     self.driver, By.PARTIAL_LINK_TEXT, ["Proceed to Steam!"]
        # )
        # proceed_to_stream_btn.click()

        selenium.wait_until_urls_prefixes(self.driver, ["https://csgoempire.com/"])

        try:
            self.account_signed_in(username)
        except:
            logging.exception(f"Failed to invoke account signed in hook")
            self.stop()

    def stop(self):
        if self.driver:
            self.driver.quit()

    @abstractmethod
    def account_signed_in(self, username: str):
        raise NotImplementedError
