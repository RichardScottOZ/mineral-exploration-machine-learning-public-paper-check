# PROMPT.md

## Project
Extend the mineral-exploration-machine-learning paper checker to aggressively extract all document links from the source README, check their accessibility/resolvability, download PDFs/HTML to section-organized folders, and produce a CSV status report.

## Requirements
Read clarify-session.md for full requirements. Key points:
- Aggressive README parser handling all messy link patterns (missing https://, arrow-style, double parens, bare URLs, etc.)
- Three-phase workflow: extract → check accessibility/resolvability → download (via Playwright)
- CSV output with: title, URL, section_path, resource_type, accessibility_status, url_resolvable, final_resolved_url, download_success, local_file_path, DOI, authors, unseen_tag, duplicate_of
- Downloads organized by full section hierarchy into `./downloads/` with ASCII-ized filenames `{id}_{truncated_title}.pdf`
- Two-pass: headless first, `--no-headless` for manual login on failures; subsequent runs skip already-downloaded
- New `paper-checker download` CLI subcommand with `--aggressive`, `--output-dir`, `--no-headless`, `--force` flags
- 3-7 second random jitter between requests; adaptive backoff on 429/503
- Skip non-documents (datasets, repos, videos, blogs, notebooks, web services, portals)

## Instructions
1. Read TODO.md to see current tasks
2. Pick the highest priority incomplete task (top `- [ ]` item)
3. Read any files before editing them
4. Implement the task completely
5. Run tests/validation relevant to the task: `python -m pytest tests/ -x -q`
6. If tests fail, fix them before continuing
7. Mark task complete in TODO.md by changing `- [ ]` to `- [x]`
8. Commit changes: `git add -A && git commit -m "descriptive message"`
9. Continue to next task

## Signs (Guardrails)
- Always read files before editing
- Never skip failing tests
- If tests fail 3 times on same issue, output: STUCK - [describe issue]
- Don't refactor unrelated code
- Keep changes focused on current task
- Update TODO.md immediately after completing each task
- Extend existing code (readme_parser.py, models.py, checker.py, cli.py) — don't rewrite from scratch
- CSV is the primary output format — no SQLite for the download workflow
- Preserve existing CLI commands and behavior — only add new functionality
- Test with real README snippets from the mineral-exploration-machine-learning repo (copy samples into test fixtures)
- Don't break existing tests in tests/test_basic.py and tests/test_readme_parser.py

## Completion
When all tasks in TODO.md are marked `[x]` and all tests pass, output: DONE
