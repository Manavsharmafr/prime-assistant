import asyncio
from playwright.async_api import async_playwright
from typing import Optional, Dict


class PlaywrightBrowserService:
    def __init__(self):
        self.pw = None
        self.browser = None

    async def get_browser(self):
        """Ensure Playwright browser is initialized."""
        if not self.browser:
            self.pw = await async_playwright().start()
            # Launch in headless mode for background operations
            try:
                self.browser = await self.pw.chromium.launch(headless=True)
            except Exception as e:
                # If chromium binaries are not installed, prompt user to run playwright install
                raise RuntimeError(
                    f"Playwright chromium binaries not found. Please run 'playwright install' in your environment. Error: {str(e)}"
                )
        return self.browser

    async def fetch_page_content(self, url: str) -> Dict[str, str]:
        """Fetch the text content of a web page using Playwright."""
        browser = await self.get_browser()
        page = await browser.new_page()
        try:
            # Set a standard timeout (15 seconds) to prevent hanging
            page.set_default_timeout(15000)
            await page.goto(url, wait_until="domcontentloaded")
            title = await page.title()
            # Extract plain text from body
            content = await page.eval_on_selector("body", "el => el.innerText")
            return {"title": title, "content": content, "url": url}
        except Exception as e:
            return {"title": "Error", "content": f"Failed to retrieve content from {url}: {str(e)}", "url": url}
        finally:
            await page.close()

    async def close(self):
        """Close browser resources."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.pw:
            await self.pw.stop()
            self.pw = None


playwright_browser = PlaywrightBrowserService()
