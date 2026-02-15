"""
Command-line interface for paper accessibility checker.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click
from tabulate import tabulate

from paper_checker.database import PaperDatabase
from paper_checker.models import Paper, AccessibilityStatus, ResourceType
from paper_checker.checker import AccessibilityChecker, check_papers_batch
from paper_checker.readme_parser import (
    scan_repo,
    parse_readme,
    DEFAULT_REPO_OWNER,
    DEFAULT_REPO_NAME,
    DEFAULT_REPO_URL,
)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Paper Accessibility Checker - Manage and check academic papers"""
    pass


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
@click.option(
    "--repo",
    default=f"{DEFAULT_REPO_OWNER}/{DEFAULT_REPO_NAME}",
    help="GitHub repository to scan (owner/name)",
)
@click.option("--check/--no-check", default=False, help="Also check accessibility after importing")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
def scan(db, repo, check, headless):
    """Scan a GitHub repository README for paper/report/thesis links and import them.

    By default scans the mineral-exploration-machine-learning repository:
    https://github.com/RichardScottOZ/mineral-exploration-machine-learning
    """
    parts = repo.split("/", 1)
    if len(parts) != 2:
        click.echo(f"Invalid repository format: {repo}. Use owner/name.", err=True)
        sys.exit(1)
    owner, name = parts

    click.echo(f"Scanning https://github.com/{owner}/{name} ...")

    try:
        papers = scan_repo(owner=owner, repo=name)
    except RuntimeError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if not papers:
        click.echo("No papers/reports/theses found in the README.")
        return

    click.echo(f"Found {len(papers)} paper/report/thesis entries.")

    with PaperDatabase(db) as database:
        # Check for duplicates by URL
        existing = database.get_all_papers(limit=100000)
        existing_urls = {p.url for p in existing if p.url}

        added = 0
        skipped = 0
        for paper in papers:
            if paper.url and paper.url in existing_urls:
                skipped += 1
                continue
            database.add_paper(paper)
            if paper.url:
                existing_urls.add(paper.url)
            added += 1

        click.echo(f"✓ Imported {added} new entries ({skipped} duplicates skipped).")

        if check and added > 0:
            all_papers = database.get_all_papers()
            unchecked = [p for p in all_papers if p.accessibility_status == AccessibilityStatus.UNKNOWN]
            if unchecked:
                click.echo(f"\nChecking accessibility for {len(unchecked)} papers...")

                async def check_and_update():
                    async with AccessibilityChecker(headless=headless) as checker:
                        for i, paper in enumerate(unchecked, 1):
                            click.echo(f"[{i}/{len(unchecked)}] Checking: {paper.title[:60]}...")
                            updated = await checker.check_paper(paper)
                            database.update_paper(updated)
                            click.echo(f"  → Status: {updated.accessibility_status.value}")

                asyncio.run(check_and_update())
                click.echo("✓ Accessibility check complete!")


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
@click.option("--title", required=True, help="Paper title")
@click.option("--authors", help="Authors (comma-separated)")
@click.option("--year", type=int, help="Publication year")
@click.option("--url", help="Paper URL")
@click.option("--doi", help="DOI")
@click.option("--resource-type", type=click.Choice([t.value for t in ResourceType]), default="paper", help="Resource type")
@click.option("--journal", help="Journal name")
@click.option("--conference", help="Conference name")
def add(db, title, authors, year, url, doi, resource_type, journal, conference):
    """Add a new paper to the database"""
    authors_list = [a.strip() for a in authors.split(",")] if authors else []
    
    paper = Paper(
        title=title,
        authors=authors_list,
        year=year,
        url=url,
        doi=doi,
        resource_type=ResourceType(resource_type),
        journal=journal,
        conference=conference
    )
    
    with PaperDatabase(db) as database:
        paper_id = database.add_paper(paper)
        click.echo(f"✓ Added paper with ID: {paper_id}")


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
@click.option("--query", help="Search query")
@click.option("--status", type=click.Choice([s.value for s in AccessibilityStatus]), help="Filter by status")
@click.option("--type", "resource_type", type=click.Choice([t.value for t in ResourceType]), help="Filter by type")
@click.option("--year", type=int, help="Filter by year")
@click.option("--limit", type=int, default=100, help="Maximum results")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
def list(db, query, status, resource_type, year, limit, output_format):
    """List papers in the database"""
    with PaperDatabase(db) as database:
        status_enum = AccessibilityStatus(status) if status else None
        type_enum = ResourceType(resource_type) if resource_type else None
        
        if query or status or resource_type or year:
            papers = database.search_papers(
                query=query,
                status=status_enum,
                resource_type=type_enum,
                year=year,
                limit=limit
            )
        else:
            papers = database.get_all_papers(limit=limit)
        
        if not papers:
            click.echo("No papers found.")
            return
        
        if output_format == "json":
            click.echo(json.dumps([p.to_dict() for p in papers], indent=2))
        elif output_format == "csv":
            import csv
            import sys
            writer = csv.DictWriter(sys.stdout, fieldnames=papers[0].to_dict().keys())
            writer.writeheader()
            for paper in papers:
                writer.writerow(paper.to_dict())
        else:
            # Table format
            headers = ["ID", "Title", "Authors", "Year", "Status", "Type", "URL"]
            rows = []
            for p in papers:
                authors_str = ", ".join(p.authors[:2])
                if len(p.authors) > 2:
                    authors_str += f" +{len(p.authors) - 2}"
                
                rows.append([
                    p.id,
                    p.title[:50] + "..." if len(p.title) > 50 else p.title,
                    authors_str[:30],
                    p.year or "-",
                    p.accessibility_status.value,
                    p.resource_type.value,
                    (p.url[:40] + "...") if p.url and len(p.url) > 40 else (p.url or "-")
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt="grid"))
            click.echo(f"\nTotal: {len(papers)} papers")


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
@click.argument("paper_id", type=int)
def show(db, paper_id):
    """Show detailed information about a paper"""
    with PaperDatabase(db) as database:
        paper = database.get_paper(paper_id)
        
        if not paper:
            click.echo(f"Paper {paper_id} not found.", err=True)
            sys.exit(1)
        
        click.echo(f"\n{'=' * 80}")
        click.echo(f"Paper ID: {paper.id}")
        click.echo(f"{'=' * 80}")
        click.echo(f"Title: {paper.title}")
        click.echo(f"Authors: {', '.join(paper.authors)}")
        click.echo(f"Year: {paper.year or 'N/A'}")
        click.echo(f"Type: {paper.resource_type.value}")
        click.echo(f"\nPublication Details:")
        click.echo(f"  Journal: {paper.journal or 'N/A'}")
        click.echo(f"  Conference: {paper.conference or 'N/A'}")
        click.echo(f"  Publisher: {paper.publisher or 'N/A'}")
        click.echo(f"\nIdentifiers:")
        click.echo(f"  DOI: {paper.doi or 'N/A'}")
        click.echo(f"  arXiv ID: {paper.arxiv_id or 'N/A'}")
        click.echo(f"  URL: {paper.url or 'N/A'}")
        click.echo(f"\nAccessibility:")
        click.echo(f"  Status: {paper.accessibility_status.value}")
        click.echo(f"  Last Checked: {paper.last_checked or 'Never'}")
        click.echo(f"  Requires Auth: {'Yes' if paper.requires_authentication else 'No'}")
        if paper.authentication_service:
            click.echo(f"  Auth Service: {paper.authentication_service}")
        if paper.download_url:
            click.echo(f"  Download URL: {paper.download_url}")
        if paper.local_file_path:
            click.echo(f"  Local File: {paper.local_file_path}")
        
        if paper.abstract:
            click.echo(f"\nAbstract:")
            click.echo(f"  {paper.abstract[:500]}...")
        
        if paper.notes:
            click.echo(f"\nNotes: {paper.notes}")
        
        click.echo(f"{'=' * 80}\n")


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
@click.option("--id", "paper_ids", multiple=True, type=int, help="Specific paper IDs to check")
@click.option("--all", "check_all", is_flag=True, help="Check all papers")
@click.option("--status", type=click.Choice([s.value for s in AccessibilityStatus]), help="Check papers with specific status")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
@click.option("--browser/--no-browser", default=True, help="Use browser automation")
def check(db, paper_ids, check_all, status, headless, browser):
    """Check accessibility status of papers"""
    with PaperDatabase(db) as database:
        if paper_ids:
            papers = [database.get_paper(pid) for pid in paper_ids]
            papers = [p for p in papers if p is not None]
        elif check_all:
            papers = database.get_all_papers()
        elif status:
            papers = database.search_papers(status=AccessibilityStatus(status))
        else:
            click.echo("Please specify papers to check (--id, --all, or --status)", err=True)
            sys.exit(1)
        
        if not papers:
            click.echo("No papers to check.")
            return
        
        click.echo(f"Checking {len(papers)} papers...")
        
        async def check_and_update():
            async with AccessibilityChecker(headless=headless) as checker:
                for i, paper in enumerate(papers, 1):
                    click.echo(f"[{i}/{len(papers)}] Checking: {paper.title[:60]}...")
                    updated_paper = await checker.check_paper(paper, use_browser=browser)
                    database.update_paper(updated_paper)
                    click.echo(f"  → Status: {updated_paper.accessibility_status.value}")
        
        asyncio.run(check_and_update())
        click.echo("✓ Done!")


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
def stats(db):
    """Show database statistics"""
    with PaperDatabase(db) as database:
        statistics = database.get_statistics()
        
        click.echo("\n📊 Database Statistics")
        click.echo("=" * 50)
        click.echo(f"Total Papers: {statistics['total_papers']}")
        
        click.echo("\n📋 By Status:")
        for status, count in statistics['by_status'].items():
            click.echo(f"  {status or 'Unknown'}: {count}")
        
        click.echo("\n📚 By Type:")
        for type_name, count in statistics['by_type'].items():
            click.echo(f"  {type_name or 'Unknown'}: {count}")
        
        click.echo("=" * 50 + "\n")


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
@click.argument("paper_id", type=int)
def delete(db, paper_id):
    """Delete a paper from the database"""
    with PaperDatabase(db) as database:
        paper = database.get_paper(paper_id)
        
        if not paper:
            click.echo(f"Paper {paper_id} not found.", err=True)
            sys.exit(1)
        
        if click.confirm(f"Delete paper '{paper.title}'?"):
            database.delete_paper(paper_id)
            click.echo("✓ Paper deleted.")


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--format", "input_format", type=click.Choice(["json", "csv", "bibtex"]), required=True, help="Input format")
def import_papers(db, input_file, input_format):
    """Import papers from a file"""
    with PaperDatabase(db) as database:
        if input_format == "json":
            with open(input_file) as f:
                data = json.load(f)
                papers = [Paper.from_dict(p) for p in data]
        elif input_format == "csv":
            import csv
            with open(input_file) as f:
                reader = csv.DictReader(f)
                papers = []
                for row in reader:
                    paper = Paper(
                        title=row.get("title", ""),
                        authors=row.get("authors", "").split(";") if row.get("authors") else [],
                        year=int(row["year"]) if row.get("year") else None,
                        url=row.get("url"),
                        doi=row.get("doi")
                    )
                    papers.append(paper)
        else:
            click.echo(f"Format {input_format} not yet implemented.", err=True)
            sys.exit(1)
        
        count = 0
        for paper in papers:
            database.add_paper(paper)
            count += 1
        
        click.echo(f"✓ Imported {count} papers.")


@main.command()
@click.option("--db", default="papers.db", help="Database file path")
@click.argument("output_file", type=click.Path())
@click.option("--format", "output_format", type=click.Choice(["json", "csv"]), required=True, help="Output format")
@click.option("--status", type=click.Choice([s.value for s in AccessibilityStatus]), help="Filter by status")
def export(db, output_file, output_format, status):
    """Export papers to a file"""
    with PaperDatabase(db) as database:
        if status:
            papers = database.search_papers(status=AccessibilityStatus(status))
        else:
            papers = database.get_all_papers()
        
        if output_format == "json":
            with open(output_file, "w") as f:
                json.dump([p.to_dict() for p in papers], f, indent=2)
        elif output_format == "csv":
            import csv
            with open(output_file, "w") as f:
                if papers:
                    writer = csv.DictWriter(f, fieldnames=papers[0].to_dict().keys())
                    writer.writeheader()
                    for paper in papers:
                        writer.writerow(paper.to_dict())
        
        click.echo(f"✓ Exported {len(papers)} papers to {output_file}")


@main.command()
@click.option(
    "--repo",
    default=f"{DEFAULT_REPO_OWNER}/{DEFAULT_REPO_NAME}",
    help="GitHub repository to scan (owner/name)",
)
@click.option("--output-dir", default="./downloads/", help="Output directory for downloads")
@click.option("--aggressive/--no-aggressive", default=True, help="Use aggressive link parsing")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
@click.option("--force", is_flag=True, help="Re-download already downloaded papers")
@click.option("--csv", "csv_path", default="papers_download.csv", help="CSV file path for status tracking")
def download(repo, output_dir, aggressive, headless, force, csv_path):
    """
    Download papers from a GitHub repository README.
    
    Workflow:
    1. Parse README and extract all paper/report/thesis links
    2. Check if CSV exists and merge with existing data (unless --force)
    3. Check accessibility and resolve URLs
    4. Download papers to section-organized folders
    5. Update CSV with final status
    """
    from paper_checker.csv_io import write_papers_csv, read_papers_csv
    from pathlib import Path
    import os
    
    parts = repo.split("/", 1)
    if len(parts) != 2:
        click.echo(f"Invalid repository format: {repo}. Use owner/name.", err=True)
        sys.exit(1)
    owner, name = parts
    
    # Check if CSV exists
    csv_exists = os.path.exists(csv_path)
    existing_papers = {}
    
    if csv_exists and not force:
        click.echo(f"Found existing CSV: {csv_path}")
        click.echo("Reading existing data...")
        existing_list = read_papers_csv(csv_path)
        # Build map of URL -> Paper for merging
        existing_papers = {p.url: p for p in existing_list if p.url}
        click.echo(f"Loaded {len(existing_papers)} existing papers")
    
    click.echo(f"\nScanning https://github.com/{owner}/{name} ...")
    
    # Phase 1: Parse README
    try:
        papers = scan_repo(owner=owner, repo=name, aggressive=aggressive)
    except RuntimeError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    
    if not papers:
        click.echo("No papers/reports/theses found in the README.")
        return
    
    click.echo(f"Found {len(papers)} paper/report/thesis entries from README.")
    
    # Merge with existing data
    if existing_papers and not force:
        click.echo("Merging with existing data...")
        merged_count = 0
        for paper in papers:
            if paper.url in existing_papers:
                existing = existing_papers[paper.url]
                # Preserve download status and file path from existing
                paper.download_success = existing.download_success
                paper.local_file_path = existing.local_file_path
                paper.accessibility_status = existing.accessibility_status
                paper.url_resolvable = existing.url_resolvable
                paper.final_resolved_url = existing.final_resolved_url
                paper.last_checked = existing.last_checked
                merged_count += 1
        click.echo(f"Merged {merged_count} papers with existing data")
    
    # Assign IDs
    for i, paper in enumerate(papers, start=1):
        paper.id = i
    
    # Write initial CSV
    click.echo(f"Writing CSV to {csv_path}...")
    write_papers_csv(papers, csv_path)
    
    # Phase 2: Check accessibility and resolve URLs (skip already checked unless force)
    papers_to_check = papers if force else [p for p in papers if p.accessibility_status == AccessibilityStatus.UNKNOWN]
    
    if papers_to_check:
        click.echo(f"\nChecking accessibility for {len(papers_to_check)} papers...")
        
        async def check_all():
            async with AccessibilityChecker(headless=headless) as checker:
                for i, paper in enumerate(papers_to_check, 1):
                    title_display = paper.title[:60] if paper.title else "untitled"
                    click.echo(f"[{i}/{len(papers_to_check)}] Checking: {title_display}...")
                    updated = await checker.check_and_resolve(paper)
                    # Update in main list
                    for j, p in enumerate(papers):
                        if p.id == updated.id:
                            papers[j] = updated
                            break
                    click.echo(f"  → {updated.accessibility_status.value}, resolvable: {updated.url_resolvable}")
        
        asyncio.run(check_all())
        
        # Update CSV after accessibility check
        write_papers_csv(papers, csv_path)
        click.echo(f"✓ Updated CSV with accessibility status")
    else:
        click.echo("All papers already checked (use --force to re-check)")
    
    # Phase 3: Download papers
    click.echo(f"\nDownloading papers to {output_dir}...")
    
    # Filter papers to download
    if not force:
        # Skip already downloaded
        papers_to_download = [p for p in papers if not p.download_success and p.url_resolvable]
    else:
        papers_to_download = [p for p in papers if p.url_resolvable]
    
    if not papers_to_download:
        click.echo("No papers to download.")
    else:
        click.echo(f"Downloading {len(papers_to_download)} papers...")
        
        async def download_all():
            async with AccessibilityChecker(headless=headless) as checker:
                for i, paper in enumerate(papers_to_download, 1):
                    title_display = paper.title[:60] if paper.title else "untitled"
                    click.echo(f"[{i}/{len(papers_to_download)}] Downloading: {title_display}...")
                    updated = await checker.download_paper(paper, output_dir)
                    # Update in main list
                    for j, p in enumerate(papers):
                        if p.id == updated.id:
                            papers[j] = updated
                            break
                    if updated.download_success:
                        click.echo(f"  → Downloaded to {updated.local_file_path}")
                    else:
                        click.echo(f"  → Download failed")
        
        asyncio.run(download_all())
    
    # Final CSV update
    write_papers_csv(papers, csv_path)
    click.echo(f"\n✓ Final CSV written to {csv_path}")
    
    # Summary statistics
    total = len(papers)
    public = sum(1 for p in papers if p.accessibility_status == AccessibilityStatus.PUBLIC)
    restricted = sum(1 for p in papers if p.accessibility_status == AccessibilityStatus.RESTRICTED)
    requires_login = sum(1 for p in papers if p.accessibility_status == AccessibilityStatus.REQUIRES_LOGIN)
    downloaded = sum(1 for p in papers if p.download_success)
    
    click.echo(f"\n=== Summary ===")
    click.echo(f"Total papers found: {total}")
    click.echo(f"Public: {public}")
    click.echo(f"Restricted: {restricted}")
    click.echo(f"Requires login: {requires_login}")
    click.echo(f"Successfully downloaded: {downloaded}")


if __name__ == "__main__":
    main()
