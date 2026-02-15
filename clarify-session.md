# Discovery: Mineral Exploration ML Paper Checker - Download & Verify
Started: 2026-02-16

## Questions Asked
1. What's the main thing you want to change or add? → Make sure it gets ALL papers/reports from the README (handling messy typos/formatting), check public availability, resolve URLs, and actually download them
2. How well does scan work today? → Has a good start but messy human typing errors in the source repo mean some things are missed
3. Which roadmap items are you targeting? → Automatic paper download, accessibility verification, CSV status report
4. What does "done" look like? → A folder of downloaded papers + a CSV dataset with status of each attempt (public accessibility, URL resolvability, download success)

## Answers Received

### Core Functionality
- Extract ALL papers/reports from the mineral-exploration-machine-learning README (handle typos/broken links)
- Check public accessibility of each URL
- Check URL resolvability
- Actually download papers (PDFs) to a local folder
- Handle robot blockers and login-gated sites (ResearchGate etc.)
- May need real browser automation with human login for some sites
- Generate CSV report: paper title, URL, public accessibility status, URL resolvable, download success/failure

### Technical Stack
- Language: Python 3.8+
- Existing: Playwright, requests, BeautifulSoup, SQLite, Click CLI
- Question: Is Playwright sufficient or do we need human-in-the-loop browser sessions?

### Key Insight
- Three-phase verification: (1) extract all refs, (2) check accessibility/resolvability, (3) attempt download
- Final output: folder of PDFs + CSV status report

## Emerging Requirements

### Must Have (MVP)
- Robust README parsing that handles typos and edge cases
- URL resolution checking
- Public accessibility checking
- Paper download to local folder
- CSV export of all status info (accessibility, resolvability, download success)

### Should Have
- Handle robot blockers / login-gated sites
- Human-in-the-loop browser mode for sites requiring login (ResearchGate, IEEE, etc.)

### Download & Organization
- Download folder organized by README section/category (e.g. "Geochemistry", "Remote Sensing")
- File naming by title/section
- Follow full redirect chain (DOI → publisher → PDF), record final resolved URL in CSV
- Two-pass approach: (1) automated headless, (2) --no-headless for manual login on failed ones

### Scope of Extraction
- Skip pure GitHub repos — but DO capture papers/reports associated with repos (common for academics)
- DO capture reports (e.g. from LLM workers), extended abstracts (e.g. Exploring for the Future datasets)
- Basically: if it's a document (paper, report, thesis, extended abstract), grab it even if linked alongside a repo

### Duplicates
- Flag duplicates (likely unintended human errors in source README)
- If same paper appears in multiple sections, include in each section — user will handle dedup later

### Parsing Strategy
- Aggressively look for documents as first pass — grab anything that looks like a document link
- Handle all messy patterns: missing https://, arrow-style links, double parens, space before paren, no parens, bare URLs
- [UNSEEN] tagged papers = known paywalled, but still check them like any other (most won't be public, ~30 of them)
- Treat any URL to a known academic domain (researchgate, arxiv, sciencedirect, springer, etc.) as a paper regardless of label
- Paper links pointing to GitHub repos (e.g. [paper](https://github.com/...)) — still capture if it's a paper about the repo

### Download Behavior
- Download folder uses full section hierarchy path (e.g. Prospectivity/Oceania/Australia/South_Australia/)
- For landing pages (researchgate, sciencedirect, etc.), attempt to find and follow the PDF download link on the page
- Record the full final PDF URL in CSV
- Partial/failed downloads: mark as download_fail in CSV (no retry in v1)
- Subsequent runs: read CSV, skip already-downloaded papers (download_success = true)

### CSV Output Columns
- title, URL, section (full path), resource_type, accessibility_status, url_resolvable, final_resolved_url, download_success, local_file_path, DOI, authors, unseen_tag

### Rate Limiting
- Random jitter delay between requests: 3-7 seconds (uniform random)
- ~1000 papers ballpark, so ~1-2 hours for full run
- Back off adaptively on 429/503 responses

### Exclusions (NOT documents — skip these)
- Datasets / data portals (zenodo datasets, figshare data, USGS data catalogs, etc.)
- Web services / APIs / WMS/WFS endpoints
- Code repositories (GitHub repos that aren't papers)
- YouTube videos
- Medium blog posts
- Colab notebooks
- Web portals / map viewers
- Tools / software

### Error Handling & Classification
- 403/401: Try to distinguish requires_login vs restricted (e.g. ResearchGate 403 = login, random 403 = restricted)
- CAPTCHA/Cloudflare: Mark as restricted in headless pass; in --no-headless pass, user manually solves CAPTCHAs (only a few expected)
- Paywall detection: Only flag as paywalled when very confident — first try to find open access version before flagging
- Partial/failed downloads: mark as download_fail, no retry in v1

### Logging & Progress
- Verbose stdout progress: [142/1000] Checking: Some Paper Title... → public, downloaded
- No need for GitHub API token — README fetched once

### Existing Code Approach
- Extend existing readme_parser.py (solid foundation, add more patterns)
- Add new fields to existing Paper model (section_path, final_resolved_url, download_success, unseen_tag) — keep it simple
- CSV as primary output, skip SQLite for this workflow — data isn't big
- New CLI subcommand: `paper-checker download` — explicit separate step from scan/check
- Try Playwright first for downloads (handles redirects, JS-rendered pages, PDF link discovery)

### Section Path & URL Tracking
- Track full heading hierarchy from root (e.g. Prospectivity/Oceania/Australia/South_Australia)
- Record original URL and final resolved URL only (not intermediates)

### File Naming
- Format: `{csv_id}_{truncated_sanitized_title}.pdf` (or .html)
- Truncate long titles to reasonable filename length

### Duplicate Handling
- Add `duplicate_of` column in CSV to flag duplicates
- Same paper in multiple sections = separate rows, flagged

### HTML-only Papers
- If paper is accessible but not as PDF (HTML-only article), save the HTML
- Expect quite a few of these

### Broken / Invalid URLs
- `file:///` local paths = human error in source README, flag as `human_error` in CSV, skip
- Aggressively fix broken URLs: strip trailing punctuation/markdown artifacts, try adding `https://` prefix
- Flag truly broken URLs as `not_resolvable`

### Second Pass (--no-headless)
- Re-reads CSV, by default skips already-downloaded papers
- `--force` flag to redo all / specific statuses
- Mostly ResearchGate will need manual login; few other sites expected

### Existing Code
- No frustrations with current code — extend as-is
- Keep it straightforward

### CLI Design
- `paper-checker download` as new explicit subcommand
- `--aggressive` flag for parser (default ON for download command, optional for scan)
- `--output-dir` flag for download folder (default: `./downloads/`)
- `--no-headless` for second pass with manual login
- `--force` flag to re-attempt already-downloaded papers

### Character Encoding
- CSV output: plain UTF-8 (no BOM)
- Paper titles in CSV: preserve unicode
- Filenames: ASCII-ize (replace accented/non-ASCII chars with closest ASCII equivalent)
- Handle Portuguese, Spanish, French, Chinese characters in titles gracefully

### Nice to Have
- TBD

### Explicitly Out of Scope
- TBD
