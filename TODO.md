# TODO

## Critical (MVP - Vertical Slice: Parse → CSV → Download one paper end-to-end)

- [x] Add new fields to Paper model in `models.py`: `section_path`, `final_resolved_url`, `download_success`, `unseen_tag`, `duplicate_of` — keep existing fields intact
- [x] Add section hierarchy tracking to `readme_parser.py`: new `_build_section_path()` function that walks heading levels (#, ##, ###, ####) and returns full path like `Prospectivity/Oceania/Australia/South_Australia`; attach `section_path` to each extracted Paper
- [x] Add aggressive link patterns to `readme_parser.py`: handle missing `https://` prefix (`[paper](www.sciencedirect.com/...)`), `[paper] -> url` arrow-style, `[paper]url` no-parens, `[paper]((url))` double-parens, `[label] (url)` space-before-paren, bare academic URLs in the Papers section; add `--aggressive` flag support via a parameter to `parse_readme()`
- [x] Add non-document URL exclusion filter in `readme_parser.py`: skip YouTube, Medium, Colab, GitHub repos (unless labeled paper/report/thesis), zenodo datasets, figshare data, WMS/WFS endpoints, data portals, tools; detect `file:///` paths and flag as `human_error`
- [x] Add `[UNSEEN]` tag detection in `readme_parser.py`: when line contains `[UNSEEN]`, set `unseen_tag=True` on the extracted Paper
- [x] Add duplicate detection: after parsing, scan for duplicate URLs across all extracted Papers; set `duplicate_of` field to the CSV row ID of the first occurrence
- [x] Create `paper_checker/csv_io.py`: write/read CSV with columns: id, title, url, section_path, resource_type, accessibility_status, url_resolvable, final_resolved_url, download_success, local_file_path, doi, authors, unseen_tag, duplicate_of — plain UTF-8, no BOM
- [x] Add URL resolution and accessibility checking to `checker.py`: new `async check_and_resolve(paper)` method that follows full redirect chain via Playwright, records `final_resolved_url`, sets `url_resolvable` (bool), classifies status (public/restricted/requires_login/paywalled/not_found/error/human_error), distinguishes ResearchGate 403 as `requires_login` vs generic 403 as `restricted`, only flags paywalled when confident
- [ ] Add paper download function to `checker.py`: new `async download_paper(paper, output_dir)` method — for direct PDF URLs save file, for landing pages attempt to find PDF link on page and follow it, fall back to saving HTML; set `download_success` and `local_file_path`; filename format `{id}_{ascii_truncated_title}.pdf` (or `.html`); create section hierarchy subdirectories under output_dir
- [ ] Add rate limiting: 3-7 second uniform random jitter between requests; adaptive backoff (double delay) on 429/503 responses
- [ ] Create `paper-checker download` CLI subcommand in `cli.py`: accepts `--repo` (default mineral-exploration-machine-learning), `--output-dir` (default `./downloads/`), `--aggressive` (default True), `--headless/--no-headless`, `--force`; workflow: parse README → write initial CSV → check accessibility → download → update CSV; verbose stdout progress `[N/total] Checking: title... → status, downloaded`
- [ ] Write tests for aggressive parser: use real README snippets as fixtures covering all messy patterns (arrow-style, missing https, double parens, bare URLs, UNSEEN tags, file:/// paths, non-document exclusions); verify section_path extraction
- [ ] Write tests for CSV round-trip: write Papers to CSV, read back, verify all fields preserved including unicode titles
- [ ] **HARD STOP** — Verify end-to-end: run `paper-checker download --repo RichardScottOZ/mineral-exploration-machine-learning` on a small subset (first 10 papers), confirm CSV output is correct and files download to proper section folders

## High Priority

- [ ] Add `--force` flag logic: re-read existing CSV, skip papers with `download_success=true` unless `--force` is set; merge new scan results with existing CSV (preserve download status for known URLs)
- [ ] Add `--no-headless` second pass support: filter CSV to papers with status `requires_login`/`restricted`/`error`, launch visible browser, pause for manual login when needed, re-attempt downloads
- [ ] Improve paywall detection in `checker.py`: only flag as paywalled when very confident (e.g. explicit "purchase article" button, not just "subscribe to newsletter"); try to find open-access version first
- [ ] Add adaptive backoff: track 429/503 responses per domain, increase delay for that domain, log when backing off

## Medium Priority

- [ ] Add `--aggressive` flag to existing `paper-checker scan` command (default off for backward compat, on for download)
- [ ] Handle edge case: same paper in multiple sections creates separate CSV rows, each with correct section_path, all flagged via `duplicate_of`
- [ ] Add progress summary at end of run: total papers found, checked, public, restricted, downloaded, failed — printed to stdout
- [ ] **HARD STOP** — Review before continuing to low priority

## Low Priority / Nice-to-Have

- [ ] Add DOI extraction from URLs (parse doi.org links, sciencedirect DOIs, etc.) and populate `doi` column
- [ ] Add author extraction from page metadata (og:author, citation_author meta tags) during accessibility check
- [ ] Support resuming interrupted runs: if CSV exists and `--force` not set, skip already-processed entries
- [ ] Add `--limit N` flag to process only first N papers (useful for testing)

---
## Completed
(Completed tasks will be moved here by the execution agent)
