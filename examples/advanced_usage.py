"""
Advanced example: Managing a research paper collection with batch operations.
"""

import asyncio
from datetime import datetime
from paper_checker import Paper, PaperDatabase, AccessibilityStatus
from paper_checker.models import ResourceType
from paper_checker.checker import check_papers_batch


async def main():
    print("=" * 80)
    print("Advanced Example: Research Paper Collection Management")
    print("=" * 80)
    
    # Initialize database
    db = PaperDatabase("research_collection.db")
    
    # 1. Batch add papers from a research project
    print("\n1. Adding papers from research project...")
    
    research_papers = [
        Paper(
            title="Convolutional Neural Networks for Mineral Classification",
            authors=["Dr. Sarah Johnson", "Prof. Michael Chen"],
            year=2023,
            resource_type=ResourceType.PAPER,
            journal="IEEE Transactions on Geoscience",
            url="https://ieeexplore.ieee.org/document/12345",
            doi="10.1109/TGRS.2023.12345",
            keywords=["CNN", "mineral classification", "deep learning"],
            abstract="This paper presents a novel CNN architecture for automated mineral classification."
        ),
        Paper(
            title="Random Forest Applications in Geological Surveys",
            authors=["Dr. Emily White", "Dr. James Brown"],
            year=2022,
            resource_type=ResourceType.PAPER,
            conference="International Conference on Machine Learning in Geoscience",
            url="https://example.com/conference/paper123",
            keywords=["random forest", "geological surveys", "prediction"],
        ),
        Paper(
            title="Machine Learning Approaches to Ore Grade Estimation",
            authors=["Dr. Robert Taylor"],
            year=2024,
            resource_type=ResourceType.THESIS,
            publisher="University of Mining Sciences",
            url="https://university.edu/thesis/2024/taylor-ml-ore",
            keywords=["machine learning", "ore grade", "estimation"],
        ),
        Paper(
            title="AI in Mineral Exploration: A Government Perspective",
            authors=["National Geological Survey Team"],
            year=2023,
            resource_type=ResourceType.REPORT,
            publisher="National Geological Survey",
            url="https://gov.example/reports/ai-mineral-2023.pdf",
        ),
    ]
    
    paper_ids = []
    for paper in research_papers:
        paper_id = db.add_paper(paper)
        paper_ids.append(paper_id)
        print(f"  ✓ Added: {paper.title[:60]}... (ID: {paper_id})")
    
    # 2. Batch check accessibility
    print("\n2. Checking accessibility for all papers (batch mode)...")
    papers_to_check = [db.get_paper(pid) for pid in paper_ids]
    
    # Note: In a real environment with network access, this would check URLs
    print("   (Simulating batch check - would use real network in production)")
    
    # 3. Filter and organize papers by status
    print("\n3. Organizing papers by accessibility status...")
    
    all_papers = db.get_all_papers()
    
    status_groups = {
        AccessibilityStatus.PUBLIC: [],
        AccessibilityStatus.REQUIRES_LOGIN: [],
        AccessibilityStatus.PAYWALLED: [],
        AccessibilityStatus.UNKNOWN: [],
    }
    
    for paper in all_papers:
        if paper.accessibility_status in status_groups:
            status_groups[paper.accessibility_status].append(paper)
    
    print(f"   - Public papers: {len(status_groups[AccessibilityStatus.PUBLIC])}")
    print(f"   - Requires login: {len(status_groups[AccessibilityStatus.REQUIRES_LOGIN])}")
    print(f"   - Paywalled: {len(status_groups[AccessibilityStatus.PAYWALLED])}")
    print(f"   - Unknown status: {len(status_groups[AccessibilityStatus.UNKNOWN])}")
    
    # 4. Advanced search examples
    print("\n4. Running advanced searches...")
    
    # Search by keyword
    ml_papers = db.search_papers(query="machine learning")
    print(f"   - Papers mentioning 'machine learning': {len(ml_papers)}")
    
    # Search by type
    theses = db.search_papers(resource_type=ResourceType.THESIS)
    print(f"   - Theses in collection: {len(theses)}")
    
    # Search by year
    recent_papers = db.search_papers(year=2023)
    print(f"   - Papers from 2023: {len(recent_papers)}")
    
    # 5. Generate reports
    print("\n5. Generating collection report...")
    
    stats = db.get_statistics()
    
    print(f"\n   📊 Collection Summary:")
    print(f"   ━" * 40)
    print(f"   Total Papers: {stats['total_papers']}")
    print(f"\n   By Type:")
    for paper_type, count in stats['by_type'].items():
        print(f"      • {paper_type}: {count}")
    print(f"\n   By Status:")
    for status, count in stats['by_status'].items():
        print(f"      • {status}: {count}")
    
    # 6. Export specific collections
    print("\n6. Exporting paper collections...")
    
    # Export public papers
    public_papers = db.search_papers(status=AccessibilityStatus.PUBLIC)
    if public_papers:
        print(f"   ✓ Found {len(public_papers)} public papers to export")
    
    # Export papers by year
    papers_2023 = db.search_papers(year=2023)
    print(f"   ✓ Found {len(papers_2023)} papers from 2023")
    
    # 7. Update paper information
    print("\n7. Updating paper metadata...")
    
    if paper_ids:
        paper = db.get_paper(paper_ids[0])
        paper.notes = f"Reviewed on {datetime.now().strftime('%Y-%m-%d')}"
        paper.keywords.append("reviewed")
        db.update_paper(paper)
        print(f"   ✓ Updated paper {paper_ids[0]} with review notes")
    
    # 8. Find papers needing attention
    print("\n8. Finding papers that need attention...")
    
    unknown_papers = db.search_papers(status=AccessibilityStatus.UNKNOWN)
    print(f"   - {len(unknown_papers)} papers need accessibility check")
    
    paywalled_papers = db.search_papers(status=AccessibilityStatus.PAYWALLED)
    print(f"   - {len(paywalled_papers)} papers behind paywalls")
    
    # Close database
    db.close()
    
    print("\n" + "=" * 80)
    print("Advanced example completed!")
    print(f"Database: research_collection.db")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
