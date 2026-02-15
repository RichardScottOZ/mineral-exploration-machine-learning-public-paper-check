# End-to-End Verification Checklist

## Command to Run
```bash
python -m paper_checker.cli download --repo RichardScottOZ/mineral-exploration-machine-learning --csv test_papers.csv --output-dir ./test_downloads/
```

## What to Verify

### 1. CSV Output
- [ ] CSV file `test_papers.csv` is created
- [ ] CSV contains all expected columns: id, title, url, section_path, resource_type, accessibility_status, url_resolvable, final_resolved_url, download_success, local_file_path, doi, authors, unseen_tag, duplicate_of
- [ ] Unicode titles are preserved correctly
- [ ] Section paths follow hierarchy (e.g., "Prospectivity/Oceania/Australia/South_Australia")
- [ ] Duplicate papers are flagged with `duplicate_of` pointing to first occurrence
- [ ] [UNSEEN] tagged papers have `unseen_tag=true`
- [ ] file:/// URLs are flagged with `accessibility_status=human_error`

### 2. Download Folder Structure
- [ ] Downloads are organized by section hierarchy under `./test_downloads/`
- [ ] Filenames follow format: `{id}_{ascii_truncated_title}.pdf` or `.html`
- [ ] Section folder names are ASCII-ized (spaces replaced with underscores)

### 3. Accessibility Checking
- [ ] `url_resolvable` is set correctly (true/false)
- [ ] `final_resolved_url` contains the URL after following redirects
- [ ] `accessibility_status` is classified correctly:
  - `public` for freely accessible papers
  - `requires_login` for ResearchGate 403 and similar
  - `restricted` for generic 403
  - `paywalled` only when very confident
  - `not_found` for 404
  - `error` for timeouts and other errors
  - `human_error` for file:/// paths

### 4. Download Success
- [ ] `download_success` is true for successfully downloaded papers
- [ ] `local_file_path` points to the correct file
- [ ] PDF files are saved as .pdf
- [ ] HTML-only papers are saved as .html

### 5. Progress Output
- [ ] Verbose progress shows: `[N/total] Checking: title... → status, resolvable: true/false`
- [ ] Download progress shows: `[N/total] Downloading: title... → Downloaded to path` or `→ Download failed`
- [ ] Summary statistics at end show:
  - Total papers found
  - Public
  - Restricted
  - Requires login
  - Successfully downloaded

### 6. Rate Limiting
- [ ] 3-7 second delay between requests (observe timing)
- [ ] Adaptive backoff on 429/503 responses (check logs)

## Quick Test (First 10 Papers)
To test with a smaller subset, you can manually edit the CSV after the initial parse to keep only the first 10 rows, then re-run with `--force` to download just those.

## Status
- [ ] Verification completed
- [ ] All checks passed
- [ ] Issues found (document below)

## Issues Found
(Document any issues here)
