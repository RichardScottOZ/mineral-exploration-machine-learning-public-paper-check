"""
Basic tests for paper checker functionality.
"""

import pytest
from datetime import datetime
from paper_checker.models import Paper, AccessibilityStatus, ResourceType
from paper_checker.database import PaperDatabase
import tempfile
import os


def test_paper_creation():
    """Test creating a Paper object"""
    paper = Paper(
        title="Test Paper",
        authors=["John Doe", "Jane Smith"],
        year=2023,
        resource_type=ResourceType.PAPER,
        url="https://example.com/paper.pdf"
    )
    
    assert paper.title == "Test Paper"
    assert len(paper.authors) == 2
    assert paper.year == 2023
    assert paper.accessibility_status == AccessibilityStatus.UNKNOWN


def test_paper_to_dict():
    """Test converting Paper to dictionary"""
    paper = Paper(
        title="Test Paper",
        authors=["John Doe"],
        year=2023
    )
    
    paper_dict = paper.to_dict()
    
    assert paper_dict["title"] == "Test Paper"
    assert paper_dict["authors"] == ["John Doe"]
    assert paper_dict["year"] == 2023


def test_paper_from_dict():
    """Test creating Paper from dictionary"""
    data = {
        "title": "Test Paper",
        "authors": ["John Doe"],
        "year": 2023,
        "resource_type": "paper",
        "accessibility_status": "public"
    }
    
    paper = Paper.from_dict(data)
    
    assert paper.title == "Test Paper"
    assert paper.year == 2023
    assert paper.resource_type == ResourceType.PAPER
    assert paper.accessibility_status == AccessibilityStatus.PUBLIC


def test_database_operations():
    """Test database CRUD operations"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name
    
    try:
        db = PaperDatabase(db_path)
        
        # Test adding a paper
        paper = Paper(
            title="Test Database Paper",
            authors=["Test Author"],
            year=2023,
            url="https://example.com/test.pdf"
        )
        
        paper_id = db.add_paper(paper)
        assert paper_id > 0
        
        # Test retrieving a paper
        retrieved_paper = db.get_paper(paper_id)
        assert retrieved_paper is not None
        assert retrieved_paper.title == "Test Database Paper"
        assert retrieved_paper.authors == ["Test Author"]
        
        # Test updating a paper
        retrieved_paper.accessibility_status = AccessibilityStatus.PUBLIC
        retrieved_paper.download_url = "https://example.com/download.pdf"
        
        success = db.update_paper(retrieved_paper)
        assert success
        
        updated_paper = db.get_paper(paper_id)
        assert updated_paper.accessibility_status == AccessibilityStatus.PUBLIC
        assert updated_paper.download_url == "https://example.com/download.pdf"
        
        # Test searching papers
        results = db.search_papers(query="Database")
        assert len(results) > 0
        assert results[0].title == "Test Database Paper"
        
        # Test statistics
        stats = db.get_statistics()
        assert stats["total_papers"] == 1
        
        # Test deleting a paper
        success = db.delete_paper(paper_id)
        assert success
        
        deleted_paper = db.get_paper(paper_id)
        assert deleted_paper is None
        
        db.close()
    
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_search_with_filters():
    """Test database search with various filters"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name
    
    try:
        db = PaperDatabase(db_path)
        
        # Add multiple papers
        papers = [
            Paper(title="ML Paper 1", year=2023, resource_type=ResourceType.PAPER,
                  accessibility_status=AccessibilityStatus.PUBLIC),
            Paper(title="ML Thesis", year=2022, resource_type=ResourceType.THESIS,
                  accessibility_status=AccessibilityStatus.RESTRICTED),
            Paper(title="ML Paper 2", year=2023, resource_type=ResourceType.PAPER,
                  accessibility_status=AccessibilityStatus.PUBLIC),
        ]
        
        for paper in papers:
            db.add_paper(paper)
        
        # Search by status
        public_papers = db.search_papers(status=AccessibilityStatus.PUBLIC)
        assert len(public_papers) == 2
        
        # Search by type
        theses = db.search_papers(resource_type=ResourceType.THESIS)
        assert len(theses) == 1
        assert theses[0].title == "ML Thesis"
        
        # Search by year
        papers_2023 = db.search_papers(year=2023)
        assert len(papers_2023) == 2
        
        # Search by query
        results = db.search_papers(query="Thesis")
        assert len(results) == 1
        
        db.close()
    
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
