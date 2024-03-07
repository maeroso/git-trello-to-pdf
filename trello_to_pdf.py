import argparse
import asyncio
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


async def wait_for_no_changes(page, sleep_time):
    while True:
        html = await page.content()
        await asyncio.sleep(sleep_time)
        new_html = await page.content()
        if html == new_html:
            break


async def expand_all_details(page):
    try:
        await page.click("text=Show more")
    except:
        pass
    try:
        await page.click("text=Show details")
    except:
        pass

async def save_card_description_to_md(page, output_dir, card):
    await page.click(".js-edit-desc")
    await page.click('[data-testid="MarkdownIcon"]')
    
    card_description = await page.query_selector('.card-description')
    description_markdown = await card_description.input_value()
    with open(f"{output_dir}/{card}.md", "w") as md_file:
        md_file.write(description_markdown)

async def print_card_to_pdf(semaphore, context, card, output_dir, sleep_time):
    async with semaphore:
        page = await context.new_page()
        await page.goto(f"https://trello.com/c/{card}")
        try:
            await wait_for_no_changes(page, sleep_time)
            page_has_error = await has_error(page, card)
            if page_has_error:
                return
            await expand_all_details(page)
            await page.pdf(path=f"{output_dir}/{card}.pdf")
            await save_card_description_to_md(page, output_dir, card)
            print(f"Card {card} saved to {output_dir}/{card}.pdf")
        except Exception as e:
            print(f"Error processing card {card}: {e}")
        finally:
            await page.close()


async def has_error(page, card) -> bool:
    try:
        await expect(page.get_by_text("Board not found")).to_be_visible()
        print(f"Card {card} or board not found")
        return True
    except:
        try:
            await expect(page.get_by_text("This board is private")).to_be_visible()
            print(f"Card {card} is private")
            return True
        except:
            pass
    return False


async def main():
    parser = argparse.ArgumentParser(description="Convert Trello cards to PDF")
    parser.add_argument(
        "-i", "--file", type=argparse.FileType("r"), help="File containing card hashes"
    )
    parser.add_argument(
        "-o", "--output", default="output/trello_cards", help="Output directory"
    )
    parser.add_argument("-u", "--username", help="Trello username")
    parser.add_argument("-p", "--password", help="Trello password")
    parser.add_argument("-b", "--headful", action="store_true", help="Run headful mode")
    parser.add_argument(
        "-t",
        "--tasks",
        type=int,
        default=5,
        help="Number of tasks to run simultaneously",
    )
    parser.add_argument("-s", "--page-sleep-time", type=int, default=2, help="Time to wait for page to load in seconds")
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
    headless = not args.headful
    slow_mo = 50 if args.headful else None
    tasks_number = int(args.tasks)

    semaphore = asyncio.Semaphore(tasks_number)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=slow_mo)
        context = await browser.new_context()
        await login_to_trello(context, username, password)
        tasks = [
            asyncio.create_task(
                print_card_to_pdf(semaphore, context, card, args.output, args.page_sleep_time)
            )
            for card in cards
        ]
        _ = await asyncio.wait(tasks)
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
