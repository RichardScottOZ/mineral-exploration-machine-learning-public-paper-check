# Quick Start Guide

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/RichardScottOZ/mineral-exploration-machine-learning-public-paper-check.git
   cd mineral-exploration-machine-learning-public-paper-check
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers** (for browser automation):
   ```bash
   playwright install chromium
   ```

4. **Optional: Install in development mode**:
   ```bash
   pip install -e .
   ```

## Quick Start

### 1. Import Sample Papers

Import the provided sample papers to get started:

```bash
paper-checker import-papers data/sample_papers.json --format json
```

### 2. List Papers

View all papers in your database:

```bash
paper-checker list
```

### 3. Check Accessibility

Check if papers are publicly accessible:

```bash
# Check specific papers by ID
paper-checker check --id 1 --id 2

# Check all papers with unknown status
paper-checker check --status unknown

# Check all papers
paper-checker check --all
```

### 4. View Paper Details

Get detailed information about a specific paper:

```bash
paper-checker show 1
```

### 5. Database Statistics

View statistics about your paper collection:

```bash
paper-checker stats
```

## Common Use Cases

### Adding Papers Manually

```bash
paper-checker add \
  --title "Your Paper Title" \
  --authors "Author One, Author Two" \
  --year 2024 \
  --url "https://example.com/paper.pdf" \
  --journal "Journal Name"
```

### Searching Papers

```bash
# Search by keyword
paper-checker list --query "machine learning"

# Filter by status
paper-checker list --status public

# Filter by type and year
paper-checker list --type thesis --year 2023

# Export results as JSON
paper-checker list --format json > my_papers.json
```

### Export and Backup

```bash
# Export all papers
paper-checker export backup.json --format json

# Export only public papers
paper-checker export public_papers.csv --format csv --status public
```

## Using the Python API

```python
from paper_checker import Paper, PaperDatabase, AccessibilityStatus
from paper_checker.checker import AccessibilityChecker
import asyncio

# Create and manage database
db = PaperDatabase("papers.db")

# Add a paper
paper = Paper(
    title="Example Paper",
    authors=["John Doe"],
    year=2024,
    url="https://example.com/paper.pdf"
)
paper_id = db.add_paper(paper)

# Check accessibility
async def check_paper():
    async with AccessibilityChecker() as checker:
        paper = db.get_paper(paper_id)
        updated = await checker.check_paper(paper)
        db.update_paper(updated)
        print(f"Status: {updated.accessibility_status}")

asyncio.run(check_paper())
```

## Browser Automation Features

### Checking Papers with Authentication

For papers that require login (e.g., ResearchGate):

```bash
# Run with visible browser to handle login manually
paper-checker check --id 1 --no-headless
```

When the browser opens, log in to the required service, then the tool will continue checking.

## Tips

1. **Start with sample data**: Import `data/sample_papers.json` to see how the system works
2. **Regular checks**: Run `paper-checker check --all` periodically to keep accessibility status up to date
3. **Backup your database**: Use `paper-checker export` to create regular backups
4. **Use filters**: When working with large collections, use filters to narrow down results

## Troubleshooting

### Playwright Browsers Not Installed

If you get an error about missing browsers:
```bash
playwright install chromium
```

### Network Errors

The checker requires internet access to verify paper accessibility. Make sure you have a working internet connection.

### Database Location

By default, the database is created as `papers.db` in your current directory. You can specify a different location:
```bash
paper-checker --db /path/to/database.db list
```

## Next Steps

- Check out the [full README](README.md) for comprehensive documentation
- Run the example script: `python examples/basic_usage.py`
- Explore the test suite: `pytest tests/`
- Read the code documentation in `paper_checker/` modules

## Getting Help

- Open an issue on GitHub for bugs or feature requests
- Check the README for detailed documentation
- Review the example script for usage patterns
