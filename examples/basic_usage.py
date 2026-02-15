"""
Example script demonstrating usage of the paper checker library.
"""

import asyncio
from paper_checker import Paper, PaperDatabase, AccessibilityStatus
from paper_checker.models import ResourceType
from paper_checker.checker import AccessibilityChecker


async def main():
    print("=" * 80)
    print("Paper Accessibility Checker - Example Usage")
    print("=" * 80)
    
    # Initialize database
    print("\n1. Initializing database...")
    db = PaperDatabase("example_papers.db")
    
    # Add some example papers
    print("\n2. Adding example papers...")
    
    papers_to_add = [
        Paper(
            title="ArXiv Example: Machine Learning Paper",
            authors=["Example Author"],
            year=2023,
            url="https://arxiv.org/abs/2301.00001",
            resource_type=ResourceType.PREPRINT,
            abstract="An example arXiv preprint for testing."
        ),
        Paper(
            title="GitHub Example: Documentation",
            authors=["GitHub User"],
            year=2024,
            url="https://github.com/",
            resource_type=ResourceType.REFERENCE
        ),
    ]
    
    for paper in papers_to_add:
        paper_id = db.add_paper(paper)
        print(f"  - Added: {paper.title} (ID: {paper_id})")
    
    # List all papers
    print("\n3. Listing all papers in database...")
    all_papers = db.get_all_papers()
    for paper in all_papers:
        print(f"  - [{paper.id}] {paper.title}")
        print(f"    Status: {paper.accessibility_status.value}")
        print(f"    URL: {paper.url}")
    
    # Check accessibility
    print("\n4. Checking paper accessibility...")
    print("   (This will use browser automation to check if papers are accessible)")
    
    async with AccessibilityChecker(headless=True) as checker:
        for paper in all_papers:
            print(f"\n  Checking: {paper.title}")
            updated_paper = await checker.check_paper(paper, use_browser=False)
            db.update_paper(updated_paper)
            
            print(f"    Status: {updated_paper.accessibility_status.value}")
            if updated_paper.requires_authentication:
                print(f"    Requires authentication: {updated_paper.authentication_service}")
            if updated_paper.download_url:
                print(f"    Download URL: {updated_paper.download_url}")
    
    # Show statistics
    print("\n5. Database Statistics:")
    stats = db.get_statistics()
    print(f"  Total papers: {stats['total_papers']}")
    print(f"  By status:")
    for status, count in stats['by_status'].items():
        print(f"    - {status}: {count}")
    
    # Search for public papers
    print("\n6. Searching for public papers...")
    public_papers = db.search_papers(status=AccessibilityStatus.PUBLIC)
    print(f"  Found {len(public_papers)} public papers:")
    for paper in public_papers:
        print(f"    - {paper.title}")
    
    # Close database
    db.close()
    
    print("\n" + "=" * 80)
    print("Example completed!")
    print(f"Database saved to: example_papers.db")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
