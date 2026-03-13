"""Browser automation tools — Playwright bridge for UI actions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import Browser, Page, async_playwright


@dataclass
class BrowserController:
    """Manages a Playwright browser instance for UI actions."""

    _browser: Optional[Browser] = field(default=None, init=False)
    _page: Optional[Page] = field(default=None, init=False)

    async def launch(self, url: str = "about:blank") -> None:
        pw = await async_playwright().start()
        self._browser = await pw.chromium.launch(headless=False)
        self._page = await self._browser.new_page()
        await self._page.goto(url)

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._page

    async def click_at(self, x: int, y: int) -> str:
        """Click at screen coordinates - OPTIMIZED for speed and reliability."""
        # Move mouse first, then click for better reliability
        await self.page.mouse.move(x, y)
        await asyncio.sleep(0.01)  # Brief pause for mouse movement
        await self.page.mouse.click(x, y)
        return f"Clicked at ({x}, {y})"

    async def type_text(self, text: str) -> str:
        """Type text at the current cursor position - OPTIMIZED for speed."""
        # Use faster typing with reduced delay
        await self.page.keyboard.type(text, delay=15)  # Reduced from 30 to 15
        return f"Typed: {text}"

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        """Scroll the page - OPTIMIZED for reliability."""
        delta = amount if direction == "down" else -amount
        # Use smooth scrolling with proper wait
        await self.page.mouse.wheel(0, delta)
        await asyncio.sleep(0.15)  # Reduced from 0.3s to 0.15s
        return f"Scrolled {direction} by {amount}px"

    async def press_key(self, key: str) -> str:
        """Press a keyboard key (Enter, Tab, Escape, etc.) - OPTIMIZED."""
        await self.page.keyboard.down(key)
        await asyncio.sleep(0.02)  # Brief pause for key down
        await self.page.keyboard.up(key)
        return f"Pressed {key}"

    async def navigate(self, url: str) -> str:
        """Navigate to a URL - OPTIMIZED for speed."""
        # Use domcontentloaded instead of full for faster navigation
        await self.page.goto(url, wait_until="domcontentloaded", timeout=10000)  # Reduced timeout
        return f"Navigated to {url}"

    async def get_page_title(self) -> str:
        """Get the current page title."""
        return await self.page.title()

    async def screenshot_bytes(self) -> bytes:
        """Take a screenshot of the current page as PNG bytes."""
        return await self.page.screenshot(type="png")

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
