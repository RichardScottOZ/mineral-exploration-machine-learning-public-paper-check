"""
Tests for author extraction from page metadata.
"""

import pytest
from playwright.async_api import async_playwright
from paper_checker.checker import AccessibilityChecker


class TestAuthorExtraction:
    """Test author extraction from various metadata formats"""
    
    @pytest.mark.asyncio
    async def test_citation_author_meta_tags(self):
        """Test extraction from citation_author meta tags"""
        html = """
        <html>
        <head>
            <meta name="citation_author" content="John Smith">
            <meta name="citation_author" content="Jane Doe">
            <meta name="citation_author" content="Bob Johnson">
        </head>
        <body></body>
        </html>
        """
        
        checker = AccessibilityChecker()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            
            authors = await checker._extract_authors_from_page(page)
            
            await browser.close()
        
        assert len(authors) == 3
        assert "John Smith" in authors
        assert "Jane Doe" in authors
        assert "Bob Johnson" in authors
    
    @pytest.mark.asyncio
    async def test_og_author_meta_tags(self):
        """Test extraction from og:author meta tags"""
        html = """
        <html>
        <head>
            <meta property="og:author" content="Alice Cooper">
        </head>
        <body></body>
        </html>
        """
        
        checker = AccessibilityChecker()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            
            authors = await checker._extract_authors_from_page(page)
            
            await browser.close()
        
        assert len(authors) == 1
        assert "Alice Cooper" in authors
    
    @pytest.mark.asyncio
    async def test_author_meta_tags(self):
        """Test extraction from author meta tags"""
        html = """
        <html>
        <head>
            <meta name="author" content="Charlie Brown">
        </head>
        <body></body>
        </html>
        """
        
        checker = AccessibilityChecker()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            
            authors = await checker._extract_authors_from_page(page)
            
            await browser.close()
        
        assert len(authors) == 1
        assert "Charlie Brown" in authors
    
    @pytest.mark.asyncio
    async def test_json_ld_author_array(self):
        """Test extraction from JSON-LD with author array"""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "ScholarlyArticle",
                "author": [
                    {"@type": "Person", "name": "David Lee"},
                    {"@type": "Person", "name": "Emma Wilson"}
                ]
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        
        checker = AccessibilityChecker()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            
            authors = await checker._extract_authors_from_page(page)
            
            await browser.close()
        
        assert len(authors) == 2
        assert "David Lee" in authors
        assert "Emma Wilson" in authors
    
    @pytest.mark.asyncio
    async def test_json_ld_single_author(self):
        """Test extraction from JSON-LD with single author"""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "ScholarlyArticle",
                "author": {"@type": "Person", "name": "Frank Miller"}
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        
        checker = AccessibilityChecker()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            
            authors = await checker._extract_authors_from_page(page)
            
            await browser.close()
        
        assert len(authors) == 1
        assert "Frank Miller" in authors
    
    @pytest.mark.asyncio
    async def test_no_authors(self):
        """Test page with no author metadata"""
        html = """
        <html>
        <head>
            <title>Some Page</title>
        </head>
        <body></body>
        </html>
        """
        
        checker = AccessibilityChecker()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            
            authors = await checker._extract_authors_from_page(page)
            
            await browser.close()
        
        assert len(authors) == 0
    
    @pytest.mark.asyncio
    async def test_duplicate_authors_removed(self):
        """Test that duplicate authors are removed"""
        html = """
        <html>
        <head>
            <meta name="citation_author" content="John Smith">
            <meta name="citation_author" content="John Smith">
        </head>
        <body></body>
        </html>
        """
        
        checker = AccessibilityChecker()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            
            authors = await checker._extract_authors_from_page(page)
            
            await browser.close()
        
        assert len(authors) == 1
        assert "John Smith" in authors
    
    @pytest.mark.asyncio
    async def test_priority_citation_author_over_others(self):
        """Test that citation_author takes priority over other methods"""
        html = """
        <html>
        <head>
            <meta name="citation_author" content="Priority Author">
            <meta name="author" content="Secondary Author">
        </head>
        <body></body>
        </html>
        """
        
        checker = AccessibilityChecker()
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html)
            
            authors = await checker._extract_authors_from_page(page)
            
            await browser.close()
        
        # Should only get citation_author, not the generic author tag
        assert len(authors) == 1
        assert "Priority Author" in authors
        assert "Secondary Author" not in authors
