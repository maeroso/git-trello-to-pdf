import argparse
import asyncio
import os
from playwright.async_api import async_playwright, expect

async def login_to_trello(context, username, password):
    page = await context.new_page()
    await page.goto("https://trello.com/login")
    await page.fill('input[name="user"]', username)
    await page.click('input[type="submit"]')
    await page.wait_for_load_state()
    await page.fill('input[name="password"]', password)
    await page.click("#login-submit")
    await expect(page.get_by_test_id("header-member-menu-avatar")).to_be_visible()
    print(f"Logged on Trello in as {username}")

async def print_card_to_pdf(semaphore, context, card, output_dir):
    async with semaphore:
        page = await context.new_page()
        await page.goto(f"https://trello.com/c/{card}")
        try:
            await expect(page.locator(".card-detail-window")).to_be_visible()
            # await expect(page.get_by_text("Description")).to_be_visible()
            try:
                await page.click("text=Show more")
            except:
                pass
            try:
                await expect(page.locator(".attachment-thumbnail")).to_be_visible()
            except:
                pass
            await page.wait_for_load_state("networkidle")
            await page.pdf(path=f"{output_dir}/{card}.pdf")
            print(f"Card {card} saved to {output_dir}/{card}.pdf")
        except:
            await check_error(page, card)
        finally:
            await page.close()
    

async def check_error(page, card):
    try:
        expect(await page.get_by_text("Board not found")).to_be_visible()
        print(f"Card {card} or board not found")
    except:
        print(f"Card {card} requires access")

async def main():
    parser = argparse.ArgumentParser(description="Convert Trello cards to PDF")
    parser.add_argument("-i", "--file", type=argparse.FileType("r"), help="File containing card hashes")
    parser.add_argument("-o", "--output", default="output/trello_cards", help="Output directory")
    parser.add_argument("-u", "--username", help="Trello username")
    parser.add_argument("-p", "--password", help="Trello password")
    args = parser.parse_args()

    cards = []

    if args.file:
        card_hashes = [line.strip() for line in args.file]
        cards.extend(card_hashes)

    if not cards:
        parser.error("No card hashes provided")

    if not args.username or not args.password:
        parser.error("Please provide Trello username and password")

    username = args.username
    password = args.password

    semaphore = asyncio.Semaphore(5)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=50)
        context = await browser.new_context()
        await login_to_trello(context, username, password)
        tasks = [asyncio.create_task(print_card_to_pdf(semaphore, context, card, args.output)) for card in cards]
        _ = await asyncio.wait(tasks)
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())