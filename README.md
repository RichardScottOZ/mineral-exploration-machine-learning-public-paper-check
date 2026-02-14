# Mineral Exploration Machine Learning - Public Paper Check

A comprehensive tool to check and manage the accessibility of academic papers, references, reports, and theses related to mineral exploration and machine learning. This tool helps researchers track which papers are publicly accessible and provides automated checking using browser automation.

## Features

- 📚 **Database Management**: Store paper information in SQLite database (offline and online compatible)
- 🔍 **Accessibility Checking**: Automatically check if papers are publicly accessible
- 🤖 **Browser Automation**: Use Playwright for automated checking with login support
- 🔐 **Authentication Support**: Handle papers requiring login (ResearchGate, IEEE, etc.)
- 📊 **Queryable Database**: Search and filter papers by various criteria
- 💾 **Import/Export**: Support for JSON and CSV formats
- 📈 **Statistics**: View database statistics and accessibility reports
- 🖥️ **CLI Interface**: Easy-to-use command-line interface

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/RichardScottOZ/mineral-exploration-machine-learning-public-paper-check.git
cd mineral-exploration-machine-learning-public-paper-check
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. (Optional) Install in development mode:
```bash
pip install -e .
```

## Usage

### Command Line Interface

The tool provides a comprehensive CLI for managing papers:

#### Add a Paper

```bash
paper-checker add --title "Machine Learning in Mineral Exploration" \
  --authors "John Smith, Jane Doe" \
  --year 2023 \
  --url "https://example.com/paper.pdf" \
  --journal "Journal of Geoscience"
```

#### List Papers

```bash
# List all papers
paper-checker list

# Search papers
paper-checker list --query "machine learning"

# Filter by status
paper-checker list --status public

# Filter by type
paper-checker list --type thesis --year 2023

# Export as JSON or CSV
paper-checker list --format json
paper-checker list --format csv > papers.csv
```

#### Check Accessibility

```bash
# Check specific papers
paper-checker check --id 1 --id 2 --id 3

# Check all papers
paper-checker check --all

# Check papers with unknown status
paper-checker check --status unknown

# Run with visible browser (for debugging)
paper-checker check --id 1 --no-headless
```

#### View Paper Details

```bash
paper-checker show 1
```

#### Database Statistics

```bash
paper-checker stats
```

#### Import Papers

```bash
# Import from JSON
paper-checker import data/sample_papers.json --format json

# Import from CSV
paper-checker import data/sample_papers.csv --format csv
```

#### Export Papers

```bash
# Export all papers
paper-checker export papers_export.json --format json

# Export only public papers
paper-checker export public_papers.csv --format csv --status public
```

#### Delete a Paper

```bash
paper-checker delete 1
```

### Python API

You can also use the library programmatically:

```python
from paper_checker import Paper, PaperDatabase, AccessibilityStatus
from paper_checker.checker import AccessibilityChecker
import asyncio

# Create a database
db = PaperDatabase("papers.db")

# Add a paper
paper = Paper(
    title="Example Paper",
    authors=["John Doe"],
    year=2023,
    url="https://example.com/paper.pdf"
)
paper_id = db.add_paper(paper)

# Check accessibility
async def check():
    async with AccessibilityChecker() as checker:
        paper = db.get_paper(paper_id)
        updated_paper = await checker.check_paper(paper)
        db.update_paper(updated_paper)
        print(f"Status: {updated_paper.accessibility_status}")

asyncio.run(check())

# Search papers
public_papers = db.search_papers(status=AccessibilityStatus.PUBLIC)
for paper in public_papers:
    print(f"{paper.title} - {paper.url}")

# Close database
db.close()
```

## Data Structure

### Paper Model

Each paper in the database contains:

- **Basic Information**:
  - Title
  - Authors (list)
  - Year
  - Resource type (paper, thesis, report, etc.)

- **Identifiers**:
  - DOI
  - URL
  - arXiv ID

- **Publication Details**:
  - Journal
  - Conference
  - Publisher
  - Volume/Issue/Pages

- **Accessibility Information**:
  - Accessibility status (public, restricted, requires_login, paywalled, etc.)
  - Last checked timestamp
  - Download URL
  - Authentication requirements
  - Authentication service

- **Local Storage**:
  - Local file path (if downloaded)

- **Metadata**:
  - Abstract
  - Keywords
  - Notes

### Accessibility Statuses

- `unknown`: Not yet checked
- `public`: Freely accessible
- `restricted`: Access restricted but reason unclear
- `requires_login`: Requires authentication (e.g., ResearchGate)
- `paywalled`: Behind a paywall
- `not_found`: Paper not found at URL
- `error`: Error occurred during checking

## Database

The tool uses SQLite for storage, providing:

- **Offline Access**: Works without internet connection
- **Queryable**: SQL-based searching and filtering
- **Portable**: Single file database
- **Flexible**: Easy to backup and share

Database file is created as `papers.db` by default, but you can specify a different path with the `--db` option.

## Browser Automation

The tool uses Playwright for browser automation, which allows:

- **JavaScript Rendering**: Handle dynamic websites
- **Login Support**: Can interact with authentication pages
- **Download Detection**: Find download links on pages
- **Paywall Detection**: Identify paywalled content

### Authentication

For papers requiring login (e.g., ResearchGate, IEEE):

1. Run the checker with visible browser: `--no-headless`
2. Manually log in when prompted
3. The tool will continue checking after authentication

Future versions will support saved credentials and automatic login.

## Sample Data

Sample papers are provided in the `data/` directory:

- `data/sample_papers.json`: Sample papers in JSON format
- `data/sample_papers.csv`: Sample papers in CSV format

Import them with:
```bash
paper-checker import data/sample_papers.json --format json
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black paper_checker/
ruff check paper_checker/
```

## Architecture

```
paper_checker/
├── __init__.py          # Package initialization
├── models.py            # Data models (Paper, AccessibilityStatus, etc.)
├── database.py          # SQLite database operations
├── checker.py           # Accessibility checking logic
└── cli.py              # Command-line interface

data/
├── sample_papers.json   # Sample data in JSON
└── sample_papers.csv    # Sample data in CSV

tests/
└── test_*.py           # Test files
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

MIT License

## Roadmap

- [ ] BibTeX import/export support
- [ ] Automatic paper download functionality
- [ ] Saved credentials for authentication
- [ ] Web interface
- [ ] Integration with reference managers (Zotero, Mendeley)
- [ ] Advanced search with full-text indexing
- [ ] Paper similarity detection
- [ ] Citation graph visualization
- [ ] Batch processing with progress bars
- [ ] Email notifications for status changes

## Support

For issues and questions, please open an issue on GitHub.

