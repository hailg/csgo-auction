# -*- coding: utf-8 -*-
import click
import csv
from app.bot.auction_bot import AuctionBot, WantedItem


@click.command()
@click.option("-u", "--username", help="Steam username", required=True)
@click.option("-p", "--password", prompt=True, hide_input=True)
@click.argument('filename', type=click.Path(exists=True))
def auction(
    username, password, filename: str
):
    with open(filename, 'rt') as f:
        wanted_items = list(csv.DictReader(f))
        wanted_items = [WantedItem(
            name1=wanted_item["name1"],
            name2=wanted_item["name2"],
            max_price=float(wanted_item["max_price"]),
            wear_value=float(wanted_item["max_wear_value"]) if wanted_item["max_wear_value"] else None

        ) for wanted_item in wanted_items]

    bot = AuctionBot(wanted_items=wanted_items, headless=False)
    bot.sign_in(username, password)


if __name__ == "__main__":
    auction()
    # This is to test only
    # bot = AuctionBot(
    #     wanted_items=[WantedItem(
    #         name1="AK-47", name2="Baroque Purple"
    #                              "", max_price=10, wear_value=None
    #     )],
    #     headless=False,
    # )
    # bot.sign_in("stream username", "steam pass")
