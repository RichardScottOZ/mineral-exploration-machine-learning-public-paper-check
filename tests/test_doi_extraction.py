"""
Tests for DOI extraction from URLs.
"""

import pytest
from paper_checker.checker import AccessibilityChecker


class TestDOIExtraction:
    """Test DOI extraction from various URL formats"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.checker = AccessibilityChecker()
    
    def test_doi_org_url(self):
        """Test extraction from doi.org URLs"""
        url = "https://doi.org/10.1016/j.oregeorev.2020.103654"
        doi = self.checker._extract_doi_from_url(url)
        assert doi == "10.1016/j.oregeorev.2020.103654"
    
    def test_doi_org_url_with_query_params(self):
        """Test extraction from doi.org URLs with query parameters"""
        url = "https://doi.org/10.1016/j.oregeorev.2020.103654?via=ihub"
        doi = self.checker._extract_doi_from_url(url)
        assert doi == "10.1016/j.oregeorev.2020.103654"
    
    def test_doi_in_path(self):
        """Test extraction from URLs with /doi/ in path"""
        url = "https://example.com/doi/10.1234/example.paper.2023"
        doi = self.checker._extract_doi_from_url(url)
        assert doi == "10.1234/example.paper.2023"
    
    def test_doi_as_query_param(self):
        """Test extraction from URLs with DOI as query parameter"""
        url = "https://example.com/article?doi=10.5678/test.2024&format=pdf"
        doi = self.checker._extract_doi_from_url(url)
        assert doi == "10.5678/test.2024"
    
    def test_url_encoded_doi(self):
        """Test extraction from URL-encoded DOIs"""
        url = "https://example.com/doi/10.1016%2Fj.oregeorev.2020.103654"
        doi = self.checker._extract_doi_from_url(url)
        assert doi == "10.1016/j.oregeorev.2020.103654"
    
    def test_no_doi_in_url(self):
        """Test URLs without DOI return None"""
        url = "https://example.com/paper/some-paper-title"
        doi = self.checker._extract_doi_from_url(url)
        assert doi is None
    
    def test_none_url(self):
        """Test None URL returns None"""
        doi = self.checker._extract_doi_from_url(None)
        assert doi is None
    
    def test_empty_url(self):
        """Test empty URL returns None"""
        doi = self.checker._extract_doi_from_url("")
        assert doi is None
    
    def test_complex_doi_with_special_chars(self):
        """Test DOI with special characters"""
        url = "https://doi.org/10.1234/example-paper_2023.v1"
        doi = self.checker._extract_doi_from_url(url)
        assert doi == "10.1234/example-paper_2023.v1"
    
    def test_sciencedirect_style_url(self):
        """Test ScienceDirect URLs (no DOI in URL structure)"""
        # ScienceDirect uses PII, not DOI in URL
        url = "https://www.sciencedirect.com/science/article/pii/S0169136820303863"
        doi = self.checker._extract_doi_from_url(url)
        # Should return None as there's no DOI in the URL
        assert doi is None
