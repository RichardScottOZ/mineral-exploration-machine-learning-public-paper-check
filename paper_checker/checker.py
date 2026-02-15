"""
Paper accessibility checker using various strategies.
"""

import asyncio
import logging
import random
import re
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse, unquote

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
        self.domain_delays: Dict[str, float] = {}  # Track delays per domain for adaptive backoff
        self.base_delay = (3.0, 7.0)  # Base random jitter range in seconds
    
    async def _rate_limit(self, url: str):
        """
        Apply rate limiting with random jitter and adaptive backoff.
        
        Args:
            url: URL being accessed (used to track per-domain delays)
        """
        domain = urlparse(url).netloc
        
        # Get delay for this domain (or use base delay)
        if domain in self.domain_delays:
            delay = self.domain_delays[domain]
        else:
            delay = random.uniform(*self.base_delay)
        
        await asyncio.sleep(delay)
    
    def _handle_rate_limit_response(self, url: str, status_code: int):
        """
        Handle rate limit responses by increasing delay for domain.
        
        Args:
            url: URL that returned rate limit
            status_code: HTTP status code (429 or 503)
        """
        domain = urlparse(url).netloc
        
        # Double the delay for this domain
        current_delay = self.domain_delays.get(domain, self.base_delay[1])
        new_delay = min(current_delay * 2, 60.0)  # Cap at 60 seconds
        self.domain_delays[domain] = new_delay
        
        logger.warning(f"Rate limited by {domain} (status {status_code}), backing off to {new_delay:.1f}s delay")
    
    def _extract_doi_from_url(self, url: str) -> Optional[str]:
        """
        Extract DOI from URL.
        
        Handles:
        - doi.org links: https://doi.org/10.1016/j.oregeorev.2020.103654
        - ScienceDirect: https://www.sciencedirect.com/science/article/pii/S0169136820303863
        - Embedded DOIs in URLs: /doi/10.1234/example
        
        Args:
            url: URL to extract DOI from
            
        Returns:
            DOI string if found, None otherwise
        """
        if not url:
            return None
        
        # Decode URL-encoded characters
        url = unquote(url)
        
        # Pattern 1: doi.org links
        doi_org_match = re.search(r'doi\.org/(10\.\d{4,}/[^\s\?&#]+)', url)
        if doi_org_match:
            return doi_org_match.group(1)
        
        # Pattern 2: /doi/ in path
        doi_path_match = re.search(r'/doi/(10\.\d{4,}/[^\s\?&#]+)', url)
        if doi_path_match:
            return doi_path_match.group(1)
        
        # Pattern 3: DOI as query parameter
        doi_param_match = re.search(r'[?&]doi=(10\.\d{4,}/[^\s\?&#]+)', url)
        if doi_param_match:
            return doi_param_match.group(1)
        
        return None
    
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
        
        # Extract DOI from URL if not already set
        if not paper.doi and paper.url:
            extracted_doi = self._extract_doi_from_url(paper.url)
            if extracted_doi:
                paper.doi = extracted_doi
        
        # Apply rate limiting
        await self._rate_limit(url)
        
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
                
                # Extract DOI from URL if not already set
                if not paper.doi:
                    extracted_doi = self._extract_doi_from_url(final_url)
                    if extracted_doi:
                        paper.doi = extracted_doi
                
                status_code = response.status
                
                # Handle rate limiting
                if status_code in (429, 503):
                    self._handle_rate_limit_response(url, status_code)
                    paper.accessibility_status = AccessibilityStatus.ERROR
                    paper.notes = f"Rate limited (status {status_code})"
                    paper.last_checked = datetime.now()
                    return paper
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
    
    async def download_paper(self, paper: Paper, output_dir: str) -> Paper:
        """
        Download paper to output directory.
        
        For direct PDF URLs, saves the file directly.
        For landing pages, attempts to find PDF link on page and follow it.
        Falls back to saving HTML if PDF not found.
        
        Creates section hierarchy subdirectories under output_dir.
        Filename format: {id}_{ascii_truncated_title}.pdf (or .html)
        
        Args:
            paper: Paper object to download
            output_dir: Base output directory
            
        Returns:
            Updated paper with download_success and local_file_path
        """
        import os
        import re
        from pathlib import Path
        from unicodedata import normalize
        
        if not paper.url and not paper.final_resolved_url:
            paper.download_success = False
            return paper
        
        url = paper.final_resolved_url or paper.url
        
        # Apply rate limiting
        await self._rate_limit(url)
        
        if not self.browser:
            await self._init_browser()
        
        try:
            # Create section subdirectory
            section_dir = Path(output_dir)
            if paper.section_path:
                # ASCII-ize section path components
                section_parts = [self._ascii_ize(part) for part in paper.section_path.split('/')]
                section_dir = section_dir / Path(*section_parts)
            section_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            title_truncated = paper.title[:80] if paper.title else "untitled"
            title_ascii = self._ascii_ize(title_truncated)
            # Remove invalid filename characters
            title_clean = re.sub(r'[<>:"/\\|?*]', '_', title_ascii)
            title_clean = re.sub(r'\s+', '_', title_clean)
            
            paper_id = paper.id or 0
            
            page = await self.browser.new_page()
            
            try:
                # Check if URL is direct PDF
                if url.lower().endswith('.pdf'):
                    # Direct PDF download
                    filename = f"{paper_id}_{title_clean}.pdf"
                    filepath = section_dir / filename
                    
                    response = await page.goto(url, timeout=self.timeout)
                    if response:
                        # Handle rate limiting
                        if response.status in (429, 503):
                            self._handle_rate_limit_response(url, response.status)
                            paper.download_success = False
                            return paper
                        
                        if response.status == 200:
                            # Save PDF
                            content = await response.body()
                            with open(filepath, 'wb') as f:
                                f.write(content)
                            
                            paper.local_file_path = str(filepath)
                            paper.download_success = True
                            return paper
                else:
                    # Landing page - try to find PDF link
                    response = await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                    
                    if not response:
                        paper.download_success = False
                        return paper
                    
                    # Handle rate limiting
                    if response.status in (429, 503):
                        self._handle_rate_limit_response(url, response.status)
                        paper.download_success = False
                        return paper
                    
                    if response.status != 200:
                        paper.download_success = False
                        return paper
                    
                    # Wait for dynamic content
                    await page.wait_for_timeout(2000)
                    
                    # Try to find PDF link
                    pdf_url = await self._find_download_link_browser(page, url)
                    
                    if pdf_url:
                        # Make absolute URL
                        if not pdf_url.startswith('http'):
                            from urllib.parse import urljoin
                            pdf_url = urljoin(url, pdf_url)
                        
                        # Download PDF
                        filename = f"{paper_id}_{title_clean}.pdf"
                        filepath = section_dir / filename
                        
                        pdf_response = await page.goto(pdf_url, timeout=self.timeout)
                        if pdf_response and pdf_response.status == 200:
                            content = await pdf_response.body()
                            with open(filepath, 'wb') as f:
                                f.write(content)
                            
                            paper.local_file_path = str(filepath)
                            paper.download_success = True
                            return paper
                    
                    # Fallback: save HTML
                    filename = f"{paper_id}_{title_clean}.html"
                    filepath = section_dir / filename
                    
                    content = await page.content()
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    paper.local_file_path = str(filepath)
                    paper.download_success = True
                    return paper
                    
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Error downloading paper {paper.title}: {e}")
            paper.download_success = False
            return paper
    
    def _ascii_ize(self, text: str) -> str:
        """
        Convert unicode text to ASCII, replacing accented characters.
        
        Args:
            text: Unicode text
            
        Returns:
            ASCII text
        """
        # Normalize to NFD (decomposed form) then filter out combining marks
        normalized = normalize('NFD', text)
        ascii_text = ''.join(c for c in normalized if ord(c) < 128)
        return ascii_text
    
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
