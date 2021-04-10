# -*- coding: utf-8 -*-
import re
import time
import logging
import requests
from datetime import datetime, timezone
from typing import List, Tuple

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from dataclasses import dataclass
from app.bot.base_bot import BaseBot
from app.util import selenium

WITHDRAW_LINK = "https://csgoempire.com/withdraw"


@dataclass
class AuctionItem:
    quality: str
    wear_value: float
    name1: str
    name2: str
    price: float
    offer_percent: float


@dataclass
class WantedItem:
    name1: str
    name2: str
    max_price: float
    wear_value: float


def _to_float(txt: str):
    return float(txt.replace(",", "").strip())


def _get_items(driver) -> List[AuctionItem]:
    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.find_all("div", class_="item--trading")
    result = []
    for index, item in enumerate(items):
        try:
            name2_elem = item.find("div", class_="item__name")
            name2 = name2_elem.text.strip()
            name1_elem = name2_elem.previous_sibling
            name1 = name1_elem.text.strip() if name1_elem.name == "div" else ""
            price_elem = item.find("div", class_="item__price")
            price = float(price_elem.text.strip().replace(",", ""))
            offer_percent = 0
            offer_percent_elem = price_elem.next_sibling.find("button")
            if offer_percent_elem != -1:
                offer_percent_text = offer_percent_elem.text.lower()
                if offer_percent_text.find("off") > -1:
                    offer_percent = -float(
                        offer_percent_text.replace("off", "").replace("%", "").strip()
                    )
                else:
                    offer_percent = float(offer_percent_text.replace("%", "").strip())
            quality_elem = item.find("div", class_="item__quality")
            quality = ""
            wear_value = 0
            if quality_elem:
                quality_spans = quality_elem.find_all("span")
                quality = quality_spans[0].text.strip()
                if len(quality_spans) == 3:
                    wear_value = float(quality_spans[2].text.replace("~", ""))
                elif len(quality_spans) == 1:
                    wear_value = 0
                else:
                    raise Exception("cannot detect wear value %s", item)
            result.append(
                AuctionItem(
                    quality=quality,
                    wear_value=wear_value,
                    name1=name1,
                    name2=name2,
                    price=price,
                    offer_percent=offer_percent,
                )
            )
        except:
            logging.exception("item: %s", index)
            return items

    return result


last_time_send_qualified_warning = None


def is_qualified(wanted_item: WantedItem, auction_item: AuctionItem) -> bool:
    is_same_name = (
        re.sub("[^A-Za-z0-9_-]+", "", auction_item.name1).lower()
        == re.sub("[^A-Za-z0-9-_-]+", "", wanted_item.name1).lower()
        and re.sub("[^A-Za-z0-9_-]+", "", auction_item.name2).lower()
        == re.sub("[^A-Za-z0-9-_-]+", "", wanted_item.name2).lower()
    )
    if not is_same_name:
        return False
    if wanted_item.wear_value is not None and auction_item.wear_value is not None:
        if auction_item.wear_value <= wanted_item.wear_value:
            return False
    # if wanted_item.offer_percent is not None and auction_item.offer_percent is not None:
    #     if auction_item.offer_percent <= wanted_item.offer_percent:
    #         return False
    is_good_price = auction_item.price <= wanted_item.max_price
    if not is_good_price:
        global last_time_send_qualified_warning
        if (
            last_time_send_qualified_warning
            and (datetime.now() - last_time_send_qualified_warning).total_seconds()
            <= 180
        ):
            return False
        send_slack_message(
            f"Found an auction item with higher price {auction_item}, our max price {wanted_item.max_price}"
        )
        last_time_send_qualified_warning = datetime.now()
        return False
    send_slack_message(f"BIDING AN ITEM {auction_item}")
    return True


def _check_sidebar_same_as_item(driver, item: AuctionItem) -> bool:
    try:
        sidebar, _ = selenium.find_visible_element(
            driver, By.CLASS_NAME, ["trades-sidebar"], 5
        )
        if sidebar is None:
            return False
        name2 = driver.find_element_by_xpath(
            "/html/body/div[1]/div[6]/div/div[3]/div/div/div/div[3]/div[1]/div/div[2]/div[2]"
        ).get_attribute("innerText")
        name2 = re.sub("[^A-Za-z0-9_-]+", "", name2).lower()
        name1 = driver.find_element_by_xpath(
            "/html/body/div[1]/div[6]/div/div[3]/div/div/div/div[3]/div[1]/div/div[2]/div[1]"
        ).get_attribute("innerText")
        name1 = re.sub("[^A-Za-z0-9_-]+", "", name1).lower()
        item.name1 = re.sub("[^A-Za-z0-9_-]+", "", item.name1).lower()
        item.name2 = re.sub("[^A-Za-z0-9_-]+", "", item.name2).lower()
        result = (item.name2 == name2 or name2.find(item.name2) > -1) and (
            item.name1 == name1 or name1.find(item.name1) > -1
        )
        if not result:
            print(
                f"Expecting item {item.name1} {item.name2} "
                f"but clicked on {name1} {name2}"
            )
        return result
    except:
        logging.exception("failed to check sidebar")
        return False


def send_slack_message(msg: str, whole_channel=True):
    if whole_channel and "<!channel>" not in msg:
        msg = f"<!channel> {msg}"
    requests.post(
        "https://hooks.slack.com/services/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",
        json={"text": msg},
    )


class AuctionBot(BaseBot):
    def __init__(
        self,
        wanted_items: List[WantedItem],
        headless: bool = False,
        download_dir: str = None,
    ):
        super().__init__(headless, download_dir)
        self.wanted_items = wanted_items

    def _open_auction_page(self):
        all_item_btn_xpath = '//*[@id="page-scroll"]/div[1]/div/div/div[2]/div[1]/div[1]/div[2]/div[4]/div/div/button'
        auction_item_btn_xpath = "/html/body/div[3]/div/div[1]/div[1]/button[2]/div/div"

        self.driver.get(WITHDRAW_LINK)

        time.sleep(1)
        elem, _ = selenium.find_visible_element(
            self.driver, By.XPATH, [all_item_btn_xpath]
        )
        elem.click()
        time.sleep(1)
        elem, _ = selenium.find_visible_element(
            self.driver, By.XPATH, [auction_item_btn_xpath]
        )
        elem.click()

    def _click_on_item(self, index: int, auction_item: AuctionItem) -> bool:
        position = index + 1
        item = self.driver.find_element_by_xpath(
            f'//*[@id="page-scroll"]/div[1]/div/div/div[3]/div/div/div[{position}]'
        )
        selenium.click(self.driver, item)
        return _check_sidebar_same_as_item(self.driver, auction_item)

    def _offer_selected_item(
        self, item: AuctionItem, max_price: float
    ) -> Tuple[str, bool, bool]:
        start_time = datetime.now(timezone.utc)
        while True:
            is_offering = False
            is_ready_to_trade = False
            offer_btn, _ = selenium.find_clickable_element(
                self.driver,
                By.XPATH,
                [
                    "/html/body/div[1]/div[6]/div/div[3]/div/div/div/div[4]/div[3]/button"
                ],
                5,
            )
            if offer_btn:
                is_offering = True
                is_ready_to_trade = False
            else:
                ready_btn, _ = selenium.find_visible_element(
                    self.driver,
                    By.XPATH,
                    [
                        "/html/body/div[1]/div[6]/div/div[2]/div/div/div/div[4]/div[2]/div[1]/button"
                    ],
                    1,
                )
                if ready_btn:
                    is_offering = False
                    is_ready_to_trade = True

            if is_ready_to_trade:
                print("Ready to trade")
                # click ready trade btn
                btn, _ = selenium.find_clickable_element(
                    self.driver,
                    By.XPATH,
                    [
                        "/html/body/div[1]/div[6]/div/div[2]/div/div/div/div[4]/div[2]/div[1]/button"
                    ],
                    30,
                )
                if btn is None:
                    error = "Cannot find ready to trade button. Auction failed!"
                    print(error)
                    return error, False, True
                selenium.click(self.driver, btn)
                return "", True, True

            if is_offering:
                # We can offer
                offer_price = _to_float(
                    self.driver.find_element_by_xpath(
                        "/html/body/div[1]/div[6]/div/div[3]/div/div/div/div[4]/div[2]/div/div/div[2]/div[2]"
                    ).get_attribute("innerText")
                )
                if offer_price > max_price:
                    error = (
                        f"Item {item.name1} {item.name2} has high offer price {offer_price}, max price {max_price}. "
                        f"Will ignore auction!"
                    )
                    print(error)
                    return error, False, False
                print(
                    f"Item {item.name1} {item.name2} has good offer price {offer_price}, max price {max_price}. "
                    "Offering..."
                )
                # click Offer btn
                btn, _ = selenium.find_clickable_element(
                    self.driver,
                    By.XPATH,
                    [
                        "/html/body/div[1]/div[6]/div/div[3]/div/div/div/div[4]/div[3]/button"
                    ],
                    5,
                )
                if btn is None:
                    error = "Cannot find Offer button. Auction failed!"
                    print(error)
                    return error, False, True
                selenium.click(self.driver, btn)
                # click confirm btn
                btn, _ = selenium.find_clickable_element(
                    self.driver,
                    By.XPATH,
                    [
                        "/html/body/div[1]/div[6]/div/div[3]/div/div/div/div[4]/div[3]/button[2]"
                    ],
                    5,
                )
                if btn is None:
                    error = "Cannot find Confirm button. Auction failed!"
                    print(error)
                    return error, False, True
                selenium.click(self.driver, btn)
                # check if any error
                error_text_elem, _ = selenium.find_visible_element(
                    self.driver, By.CLASS_NAME, ["dialog-c-text"], 1
                )
                if error_text_elem:
                    error = f'Failed to offer, error: {error_text_elem.get_property("innerHTML")}'
                    print(error)
                    return error, False, True

            if (datetime.now(timezone.utc) - start_time).total_seconds() > 10 * 600:
                error = "Something is wrong with auction. Do not know what to do"
                print(error)
                return error, False, True

            # Waiting for ready to trade. Do nothing
            time.sleep(0.5)

    def account_signed_in(self, username: str):
        send_slack_message(f"{username} will try to bid for item {self.wanted_items}")
        self._open_auction_page()
        auction_page_time = datetime.now()
        while True:
            try:
                if (datetime.now() - auction_page_time).total_seconds() > 300:
                    self._open_auction_page()
                    auction_page_time = datetime.now()
                auction_items = _get_items(self.driver)
                start_time = datetime.now()
                while not auction_items:
                    time.sleep(1)
                    auction_items = _get_items(self.driver)
                    if (datetime.now() - start_time).total_seconds() > 30:
                        break
                for auction_index, auction_item in enumerate(auction_items):
                    for wanted_item in self.wanted_items:
                        if is_qualified(wanted_item, auction_item) and self._click_on_item(
                            auction_index, auction_item
                        ):
                            (error_msg, success, notification,) = self._offer_selected_item(
                                auction_item, wanted_item.max_price
                            )
                            if success:
                                send_slack_message(f"Offer successfully: {wanted_item}")
                                time.sleep(24 * 3600)
                            elif notification:
                                send_slack_message(
                                    f"FAILED to offer: {wanted_item}, error message {error_msg}"
                                )
                                time.sleep(24 * 3600)
            except Exception as e:
                send_slack_message(
                    f"There is an error with bot {username}, error {e}"
                )
                logging.exception(f"There is an error with bot {username}")
                try:
                    selenium.capture_for_debug(self.driver, "error")
                except:
                    logging.exception("There is an error with bot")
                break
            time.sleep(1)
        time.sleep(24 * 3600)
