"""
Tests for CSV I/O functionality.
"""

import tempfile
import os
from paper_checker.csv_io import write_papers_csv, read_papers_csv
from paper_checker.models import Paper, ResourceType, AccessibilityStatus


def test_csv_round_trip():
    """Test writing and reading papers to/from CSV."""
    papers = [
        Paper(
            title="Test Paper 1",
            url="https://example.com/paper1",
            section_path="Section/Subsection",
            resource_type=ResourceType.PAPER,
            accessibility_status=AccessibilityStatus.PUBLIC,
            url_resolvable=True,
            final_resolved_url="https://example.com/paper1.pdf",
            download_success=True,
            local_file_path="/downloads/1_test_paper_1.pdf",
            doi="10.1234/test",
            authors=["John Doe", "Jane Smith"],
            unseen_tag=False,
            duplicate_of=None,
        ),
        Paper(
            title="Test Paper 2 with Unicode: 中文",
            url="https://example.com/paper2",
            section_path="Another/Section",
            resource_type=ResourceType.THESIS,
            accessibility_status=AccessibilityStatus.REQUIRES_LOGIN,
            url_resolvable=True,
            final_resolved_url="https://example.com/paper2",
            download_success=False,
            local_file_path=None,
            doi=None,
            authors=[],
            unseen_tag=True,
            duplicate_of=1,
        ),
    ]
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        temp_path = f.name
    
    try:
        write_papers_csv(papers, temp_path)
        
        # Read back
        read_papers = read_papers_csv(temp_path)
        
        assert len(read_papers) == 2
        
        # Check first paper
        p1 = read_papers[0]
        assert p1.title == "Test Paper 1"
        assert p1.url == "https://example.com/paper1"
        assert p1.section_path == "Section/Subsection"
        assert p1.resource_type == ResourceType.PAPER
        assert p1.accessibility_status == AccessibilityStatus.PUBLIC
        assert p1.url_resolvable is True
        assert p1.final_resolved_url == "https://example.com/paper1.pdf"
        assert p1.download_success is True
        assert p1.local_file_path == "/downloads/1_test_paper_1.pdf"
        assert p1.doi == "10.1234/test"
        assert p1.authors == ["John Doe", "Jane Smith"]
        assert p1.unseen_tag is False
        assert p1.duplicate_of is None
        
        # Check second paper (with unicode)
        p2 = read_papers[1]
        assert p2.title == "Test Paper 2 with Unicode: 中文"
        assert p2.url == "https://example.com/paper2"
        assert p2.section_path == "Another/Section"
        assert p2.resource_type == ResourceType.THESIS
        assert p2.accessibility_status == AccessibilityStatus.REQUIRES_LOGIN
        assert p2.url_resolvable is True
        assert p2.final_resolved_url == "https://example.com/paper2"
        assert p2.download_success is False
        assert p2.local_file_path is None
        assert p2.doi is None
        assert p2.authors == []
        assert p2.unseen_tag is True
        assert p2.duplicate_of == 1
        
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_csv_empty_fields():
    """Test CSV handling of empty/None fields."""
    papers = [
        Paper(
            title="Minimal Paper",
            url="https://example.com/minimal",
        ),
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        temp_path = f.name
    
    try:
        write_papers_csv(papers, temp_path)
        read_papers = read_papers_csv(temp_path)
        
        assert len(read_papers) == 1
        p = read_papers[0]
        assert p.title == "Minimal Paper"
        assert p.url == "https://example.com/minimal"
        assert p.section_path is None or p.section_path == ''
        assert p.doi is None
        assert p.authors == []
        assert p.unseen_tag is False
        assert p.duplicate_of is None
        
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
