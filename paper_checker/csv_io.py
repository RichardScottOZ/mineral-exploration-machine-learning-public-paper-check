"""
CSV input/output for paper data.

Handles reading and writing Paper objects to/from CSV format with all fields
including download workflow metadata.
"""

import csv
from datetime import datetime
from typing import List, Optional

from paper_checker.models import Paper, ResourceType, AccessibilityStatus


# CSV column order
CSV_COLUMNS = [
    'id',
    'title',
    'url',
    'section_path',
    'resource_type',
    'accessibility_status',
    'url_resolvable',
    'final_resolved_url',
    'download_success',
    'local_file_path',
    'doi',
    'authors',
    'unseen_tag',
    'duplicate_of',
]


def write_papers_csv(papers: List[Paper], filepath: str) -> None:
    """
    Write papers to CSV file.
    
    Args:
        papers: List of Paper objects to write
        filepath: Path to output CSV file
    """
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        
        for i, paper in enumerate(papers, start=1):
            # Set ID if not already set
            if paper.id is None:
                paper.id = i
            
            row = {
                'id': paper.id,
                'title': paper.title or '',
                'url': paper.url or '',
                'section_path': paper.section_path or '',
                'resource_type': paper.resource_type.value if paper.resource_type else '',
                'accessibility_status': paper.accessibility_status.value if paper.accessibility_status else '',
                'url_resolvable': str(paper.url_resolvable).lower() if paper.url_resolvable is not None else '',
                'final_resolved_url': paper.final_resolved_url or '',
                'download_success': str(paper.download_success).lower() if paper.download_success is not None else '',
                'local_file_path': paper.local_file_path or '',
                'doi': paper.doi or '',
                'authors': '; '.join(paper.authors) if paper.authors else '',
                'unseen_tag': str(paper.unseen_tag).lower() if paper.unseen_tag is not None else '',
                'duplicate_of': str(paper.duplicate_of) if paper.duplicate_of is not None else '',
            }
            writer.writerow(row)


def read_papers_csv(filepath: str) -> List[Paper]:
    """
    Read papers from CSV file.
    
    Args:
        filepath: Path to input CSV file
        
    Returns:
        List of Paper objects
    """
    papers = []
    
    with open(filepath, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Parse boolean fields
            url_resolvable = row.get('url_resolvable', '').lower() == 'true'
            download_success = row.get('download_success', '').lower() == 'true'
            unseen_tag = row.get('unseen_tag', '').lower() == 'true'
            
            # Parse optional integer fields
            paper_id = int(row['id']) if row.get('id') else None
            duplicate_of = int(row['duplicate_of']) if row.get('duplicate_of') else None
            
            # Parse enum fields
            resource_type = ResourceType(row['resource_type']) if row.get('resource_type') else ResourceType.PAPER
            accessibility_status = AccessibilityStatus(row['accessibility_status']) if row.get('accessibility_status') else AccessibilityStatus.UNKNOWN
            
            # Parse authors
            authors = [a.strip() for a in row.get('authors', '').split(';') if a.strip()]
            
            paper = Paper(
                id=paper_id,
                title=row.get('title', ''),
                url=row.get('url', ''),
                section_path=row.get('section_path', ''),
                resource_type=resource_type,
                accessibility_status=accessibility_status,
                url_resolvable=url_resolvable,
                final_resolved_url=row.get('final_resolved_url', '') or None,
                download_success=download_success,
                local_file_path=row.get('local_file_path', '') or None,
                doi=row.get('doi', '') or None,
                authors=authors,
                unseen_tag=unseen_tag,
                duplicate_of=duplicate_of,
            )
            papers.append(paper)
    
    return papers
