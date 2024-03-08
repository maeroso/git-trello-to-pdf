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
    await expect(page.get_by_test_id("header-member-menu-avatar")).to_be_visible(timeout=20000)
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
        await page.click("text=Show more", timeout=1000)
    except:
        pass
    try:
        await page.click("text=Show details", timeout=1000)
    except:
        pass

async def download_attachments(page, output_dir, card):
    attachment_divs = await page.query_selector_all('.attachment-thumbnail')
    for attachment_div in attachment_divs:
        attachment_link = await attachment_div.query_selector('.js-download')
        attachment_name = await(await attachment_div.query_selector('.attachment-thumbnail-name')).inner_text()
        async with page.expect_download() as download_info:
            await attachment_link.click()
        download = await download_info.value
        
        # Wait for the download process to complete and save the downloaded file somewhere
        await download.save_as(output_dir + "/" + card + "_att_" + download.suggested_filename)

async def extract_checklists(page):
    checklists = await page.query_selector_all(".checklist")
    checklist_data = ""
    for checklist in checklists:
        title = await (await checklist.query_selector(".checklist-title h3")).text_content()

        items = await checklist.query_selector_all(".checklist-item")
        for item in items:
            is_checked = await (await item.query_selector(".checklist-item-checkbox input")).is_checked()
            item_text = await (await item.query_selector(".checklist-item-details-text")).text_content()
            checklist_data += f"- [{'x' if is_checked else ' '}] {item_text}\n"
        checklist_data += "\n"

    return checklist_data

async def save_card_description_to_md(page, output_dir, card):
    await page.click(".js-edit-desc")
    await page.click('[data-testid="MarkdownIcon"]')
    
    card_description = await page.query_selector('.card-description')
    description_markdown = await card_description.input_value()
    checklist_markdown =  await extract_checklists(page)
    with open(f"{output_dir}/{card}.md", "w") as md_file:
        md_file.write(description_markdown + "\n" + checklist_markdown)

async def extract_card_board_list_names(page):
    # Extract the first 32 characters of the card name
    card_name_element = await page.query_selector('.window-title > h2')
    card_name = (await card_name_element.text_content())[:32] if card_name_element else "Card name not found"
    
    # Extract the list name
    list_name_element = await page.query_selector('.js-current-list > p > a')
    list_name = await list_name_element.text_content() if list_name_element else "List name not found"
    
    # Extract the board name
    board_name_element = await page.query_selector('a[data-testid="workspace-detail-name"] > p')
    board_name = await board_name_element.text_content() if board_name_element else "Board name not found"
    
    return card_name.strip(), board_name, list_name

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
            
            card_name, board_name, list_name = await extract_card_board_list_names(page)
            card_output_dir = f"{output_dir}/{board_name}/{list_name}"
            print(card_output_dir)
            
            await page.pdf(path=f"{card_output_dir}/{card}${card_name}.pdf")
            await save_card_description_to_md(page, card_output_dir, card)
            await download_attachments(page, card_output_dir, card)
            print(f"Card {card} saved to {card_output_dir}/{card}")
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
