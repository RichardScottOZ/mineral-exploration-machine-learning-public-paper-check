"""
Paper accessibility checker using various strategies.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from paper_checker.models import Paper, AccessibilityStatus

logger = logging.getLogger(__name__)


class AccessibilityChecker:
    """Check accessibility of academic papers"""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize checker.
        
        Args:
            headless: Run browser in headless mode
            timeout: Timeout for page loads in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
    
    async def check_and_resolve(self, paper: Paper) -> Paper:
        """
        Check accessibility and resolve final URL following full redirect chain.
        
        This method:
        - Follows all redirects to get final_resolved_url
        - Sets url_resolvable based on whether URL can be reached
        - Classifies accessibility_status (public/restricted/requires_login/paywalled/not_found/error/human_error)
        - Distinguishes ResearchGate 403 as requires_login vs generic 403 as restricted
        - Only flags paywalled when confident
        
        Args:
            paper: Paper object to check
            
        Returns:
            Updated paper with accessibility and resolution info
        """
        # Check for human error (file:/// paths)
        if paper.url and paper.url.startswith('file:///'):
            paper.accessibility_status = AccessibilityStatus.HUMAN_ERROR
            paper.url_resolvable = False
            paper.last_checked = datetime.now()
            return paper
        
        if not paper.url and not paper.doi:
            paper.accessibility_status = AccessibilityStatus.NOT_FOUND
            paper.url_resolvable = False
            paper.last_checked = datetime.now()
            return paper
        
        # Try URL first, then DOI
        url = paper.url or f"https://doi.org/{paper.doi}"
        
        if not self.browser:
            await self._init_browser()
        
        try:
            page = await self.browser.new_page()
            
            try:
                response = await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                
                if not response:
                    paper.accessibility_status = AccessibilityStatus.ERROR
                    paper.url_resolvable = False
                    paper.last_checked = datetime.now()
                    return paper
                
                # Record final URL after redirects
                final_url = page.url
                paper.final_resolved_url = final_url
                paper.url_resolvable = True
                
                status_code = response.status
                
                # Handle 404
                if status_code == 404:
                    paper.accessibility_status = AccessibilityStatus.NOT_FOUND
                    paper.last_checked = datetime.now()
                    return paper
                
                # Handle 403 - distinguish ResearchGate from others
                if status_code == 403:
                    if 'researchgate.net' in final_url.lower():
                        paper.accessibility_status = AccessibilityStatus.REQUIRES_LOGIN
                        paper.requires_authentication = True
                        paper.authentication_service = "ResearchGate"
                    else:
                        paper.accessibility_status = AccessibilityStatus.RESTRICTED
                    paper.last_checked = datetime.now()
                    return paper
                
                # Handle 401
                if status_code == 401:
                    paper.accessibility_status = AccessibilityStatus.REQUIRES_LOGIN
                    paper.requires_authentication = True
                    paper.authentication_service = self._identify_auth_service(final_url)
                    paper.last_checked = datetime.now()
                    return paper
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)
                
                # Check for login requirements first (more specific than paywall)
                if await self._check_login_required_browser(page):
                    auth_service = self._identify_auth_service(final_url)
                    paper.accessibility_status = AccessibilityStatus.REQUIRES_LOGIN
                    paper.requires_authentication = True
                    paper.authentication_service = auth_service
                    paper.last_checked = datetime.now()
                    return paper
                
                # Check for paywall - only flag if very confident
                if await self._check_paywall_browser_confident(page):
                    paper.accessibility_status = AccessibilityStatus.PAYWALLED
                    paper.last_checked = datetime.now()
                    return paper
                
                # Check for download links
                download_url = await self._find_download_link_browser(page, final_url)
                if download_url:
                    paper.download_url = download_url
                
                # If we got here with 200 status, it's likely public
                if status_code == 200:
                    paper.accessibility_status = AccessibilityStatus.PUBLIC
                else:
                    paper.accessibility_status = AccessibilityStatus.RESTRICTED
                
                paper.last_checked = datetime.now()
                return paper
                
            finally:
                await page.close()
                
        except PlaywrightTimeout:
            logger.error(f"Timeout accessing {url}")
            paper.accessibility_status = AccessibilityStatus.ERROR
            paper.url_resolvable = False
            paper.last_checked = datetime.now()
            return paper
        except Exception as e:
            logger.error(f"Error checking paper {paper.title}: {e}")
            paper.accessibility_status = AccessibilityStatus.ERROR
            paper.url_resolvable = False
            paper.notes = f"Error: {str(e)}"
            paper.last_checked = datetime.now()
            return paper
    
    async def _check_paywall_browser_confident(self, page: Page) -> bool:
        """
        Check for paywall with high confidence - only flag if very sure.
        
        Looks for explicit purchase/subscription buttons, not just mentions.
        """
        try:
            # Very specific paywall indicators
            confident_paywall_selectors = [
                "button:has-text('Purchase')",
                "button:has-text('Buy article')",
                "button:has-text('Subscribe to access')",
                "a:has-text('Purchase this article')",
                "[class*='purchase-button']",
                "[id*='purchase-button']",
            ]
            
            for selector in confident_paywall_selectors:
                if await page.locator(selector).count() > 0:
                    return True
            
            return False
        except Exception:
            return False
    
    async def check_paper(self, paper: Paper, use_browser: bool = True) -> Paper:
        """
        Check accessibility of a paper.
        
        Args:
            paper: Paper object to check
            use_browser: Whether to use browser automation (more reliable but slower)
            
        Returns:
            Updated paper with accessibility status
        """
        if not paper.url and not paper.doi:
            paper.accessibility_status = AccessibilityStatus.NOT_FOUND
            paper.last_checked = datetime.now()
            return paper
        
        # Try URL first, then DOI
        url = paper.url or f"https://doi.org/{paper.doi}"
        
        try:
            if use_browser:
                status, details = await self._check_with_browser(url)
            else:
                status, details = await self._check_with_requests(url)
            
            paper.accessibility_status = status
            paper.last_checked = datetime.now()
            
            # Update download URL if found
            if details.get("download_url"):
                paper.download_url = details["download_url"]
            
            # Update authentication requirements
            if details.get("requires_auth"):
                paper.requires_authentication = True
                paper.authentication_service = details.get("auth_service")
            
        except Exception as e:
            logger.error(f"Error checking paper {paper.title}: {e}")
            paper.accessibility_status = AccessibilityStatus.ERROR
            paper.notes = f"Error: {str(e)}"
            paper.last_checked = datetime.now()
        
        return paper
    
    async def _check_with_requests(self, url: str) -> tuple[AccessibilityStatus, Dict[str, Any]]:
        """
        Check accessibility using simple HTTP requests.
        
        Args:
            url: URL to check
            
        Returns:
            Tuple of (status, details dict)
        """
        try:
            response = requests.get(url, allow_redirects=True, timeout=30)
            
            if response.status_code == 404:
                return AccessibilityStatus.NOT_FOUND, {}
            
            if response.status_code == 200:
                # Parse HTML to check for indicators
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check for common paywall indicators
                if self._has_paywall_indicators(soup, response.url):
                    return AccessibilityStatus.PAYWALLED, {}
                
                # Check for login requirements
                if self._requires_login(soup, response.url):
                    auth_service = self._identify_auth_service(response.url)
                    return AccessibilityStatus.REQUIRES_LOGIN, {
                        "requires_auth": True,
                        "auth_service": auth_service
                    }
                
                # Check for download links
                download_url = self._find_download_link(soup, url)
                
                return AccessibilityStatus.PUBLIC, {
                    "download_url": download_url
                }
            
            return AccessibilityStatus.RESTRICTED, {}
            
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return AccessibilityStatus.ERROR, {}
    
    async def _check_with_browser(self, url: str) -> tuple[AccessibilityStatus, Dict[str, Any]]:
        """
        Check accessibility using browser automation.
        
        Args:
            url: URL to check
            
        Returns:
            Tuple of (status, details dict)
        """
        if not self.browser:
            await self._init_browser()
        
        try:
            page = await self.browser.new_page()
            
            try:
                response = await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                
                if not response:
                    return AccessibilityStatus.ERROR, {}
                
                if response.status == 404:
                    return AccessibilityStatus.NOT_FOUND, {}
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                final_url = page.url
                
                # Check for paywall indicators
                if await self._check_paywall_browser(page):
                    return AccessibilityStatus.PAYWALLED, {}
                
                # Check for login requirements
                if await self._check_login_required_browser(page):
                    auth_service = self._identify_auth_service(final_url)
                    return AccessibilityStatus.REQUIRES_LOGIN, {
                        "requires_auth": True,
                        "auth_service": auth_service
                    }
                
                # Check for download links
                download_url = await self._find_download_link_browser(page, final_url)
                
                return AccessibilityStatus.PUBLIC, {
                    "download_url": download_url
                }
                
            finally:
                await page.close()
                
        except PlaywrightTimeout:
            logger.error(f"Timeout accessing {url}")
            return AccessibilityStatus.ERROR, {}
        except Exception as e:
            logger.error(f"Browser error for {url}: {e}")
            return AccessibilityStatus.ERROR, {}
    
    def _has_paywall_indicators(self, soup: BeautifulSoup, url: str) -> bool:
        """Check if page has paywall indicators"""
        paywall_keywords = [
            "paywall", "subscribe", "purchase", "buy article",
            "access denied", "requires subscription", "premium content"
        ]
        
        text = soup.get_text().lower()
        return any(keyword in text for keyword in paywall_keywords)
    
    def _requires_login(self, soup: BeautifulSoup, url: str) -> bool:
        """Check if page requires login"""
        login_keywords = [
            "sign in", "log in", "login required", "authentication required",
            "please login", "member access"
        ]
        
        text = soup.get_text().lower()
        
        # Check for login forms
        has_login_form = bool(soup.find("form", {"id": lambda x: x and "login" in x.lower() if x else False}))
        
        return has_login_form or any(keyword in text for keyword in login_keywords)
    
    def _identify_auth_service(self, url: str) -> Optional[str]:
        """Identify authentication service from URL"""
        domain = urlparse(url).netloc.lower()
        
        services = {
            "researchgate.net": "ResearchGate",
            "ieee.org": "IEEE Xplore",
            "sciencedirect.com": "ScienceDirect",
            "springer.com": "Springer",
            "wiley.com": "Wiley",
            "nature.com": "Nature",
            "jstor.org": "JSTOR",
            "acm.org": "ACM Digital Library",
        }
        
        for domain_part, service in services.items():
            if domain_part in domain:
                return service
        
        return None
    
    def _find_download_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Find PDF download link on page"""
        # Look for PDF links
        pdf_links = soup.find_all("a", href=lambda x: x and ".pdf" in x.lower() if x else False)
        
        if pdf_links:
            return pdf_links[0].get("href")
        
        # Look for download buttons
        download_buttons = soup.find_all("a", text=lambda x: x and "download" in x.lower() if x else False)
        
        if download_buttons:
            return download_buttons[0].get("href")
        
        return None
    
    async def _check_paywall_browser(self, page: Page) -> bool:
        """Check for paywall using browser"""
        try:
            # Check for common paywall elements
            paywall_selectors = [
                "[class*='paywall']",
                "[id*='paywall']",
                "[class*='subscription']",
                "text=Purchase this article",
                "text=Subscribe to view"
            ]
            
            for selector in paywall_selectors:
                if await page.locator(selector).count() > 0:
                    return True
            
            return False
        except Exception:
            return False
    
    async def _check_login_required_browser(self, page: Page) -> bool:
        """Check if login is required using browser"""
        try:
            # Check for login forms or buttons
            login_selectors = [
                "input[type='password']",
                "button:has-text('Sign in')",
                "button:has-text('Log in')",
                "a:has-text('Sign in')",
                "form[id*='login']"
            ]
            
            for selector in login_selectors:
                if await page.locator(selector).count() > 0:
                    return True
            
            return False
        except Exception:
            return False
    
    async def _find_download_link_browser(self, page: Page, base_url: str) -> Optional[str]:
        """Find PDF download link using browser"""
        try:
            # Look for PDF links
            pdf_locator = page.locator("a[href*='.pdf']")
            if await pdf_locator.count() > 0:
                return await pdf_locator.first.get_attribute("href")
            
            # Look for download buttons
            download_locator = page.locator("a:has-text('Download')")
            if await download_locator.count() > 0:
                return await download_locator.first.get_attribute("href")
            
        except Exception:
            pass
        
        return None
    
    async def _init_browser(self):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
    
    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def check_papers_batch(papers: list[Paper], headless: bool = True) -> list[Paper]:
    """
    Check accessibility for multiple papers.
    
    Args:
        papers: List of papers to check
        headless: Run browser in headless mode
        
    Returns:
        List of updated papers
    """
    async with AccessibilityChecker(headless=headless) as checker:
        tasks = [checker.check_paper(paper) for paper in papers]
        return await asyncio.gather(*tasks)
