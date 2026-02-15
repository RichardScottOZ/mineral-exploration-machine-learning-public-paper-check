"""
Tests for the README parser module.
"""

import pytest

from paper_checker.models import Paper, ResourceType, AccessibilityStatus
from paper_checker.readme_parser import (
    parse_readme,
    _label_to_resource_type,
    _title_from_url,
    _extract_parent_context,
    _is_academic_url,
    DEFAULT_REPO_OWNER,
    DEFAULT_REPO_NAME,
)


def test_label_to_resource_type():
    """Test mapping labels to resource types."""
    assert _label_to_resource_type("paper") == ResourceType.PAPER
    assert _label_to_resource_type("Paper") == ResourceType.PAPER
    assert _label_to_resource_type("papers") == ResourceType.PAPER
    assert _label_to_resource_type("thesis") == ResourceType.THESIS
    assert _label_to_resource_type("PhD") == ResourceType.THESIS
    assert _label_to_resource_type("report") == ResourceType.REPORT
    assert _label_to_resource_type("Report") == ResourceType.REPORT


def test_title_from_url():
    """Test deriving title from URL."""
    assert _title_from_url("https://arxiv.org/abs/2301.12345") == "2301.12345"
    assert _title_from_url("https://example.com/some-paper-title.pdf") == "some paper title"
    assert _title_from_url("https://example.com/") == "https://example.com/"


def test_parse_readme_paper_link():
    """Test parsing standard [paper](url) links."""
    readme = """\
# Section One
* [My Cool Project](https://github.com/example/project) -> Description
\t* [paper](https://arxiv.org/abs/2301.12345)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://arxiv.org/abs/2301.12345"
    assert papers[0].resource_type == ResourceType.PAPER
    assert papers[0].title == "My Cool Project"
    assert "Section One" in papers[0].keywords


def test_parse_readme_report_link():
    """Test parsing [Report](url) links."""
    readme = """\
# Reports
* [National Survey](https://example.gov/survey)
\t* [Report](https://example.gov/report.pdf)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://example.gov/report.pdf"
    assert papers[0].resource_type == ResourceType.REPORT


def test_parse_readme_arrow_link():
    """Test parsing [paper] -> url style links."""
    readme = """\
# Section
* [pyClusterwise](https://pypi.org/project/pyClusterWise/)
  * [paper] -> https://www.sciencedirect.com/science/article/pii/S0169136825001519 -> Description
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://www.sciencedirect.com/science/article/pii/S0169136825001519"
    assert papers[0].resource_type == ResourceType.PAPER
    assert papers[0].title == "pyClusterwise"


def test_parse_readme_thesis_inline():
    """Test parsing lines mentioning thesis with inline URLs."""
    readme = """\
# Theses
- https://example.edu/thesis/12345 -> PhD thesis about ML
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://example.edu/thesis/12345"
    assert papers[0].resource_type == ResourceType.THESIS


def test_parse_readme_thesis_markdown_link():
    """Test parsing thesis references that are markdown links."""
    readme = """\
# Prospectivity
* [Machine learning for geological mapping](https://eprints.utas.edu.au/18571/) -> PhD thesis with code
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://eprints.utas.edu.au/18571/"
    assert papers[0].resource_type == ResourceType.THESIS


def test_parse_readme_deduplication():
    """Test that duplicate URLs are flagged with duplicate_of."""
    readme = """\
# Section
* [Project A](https://github.com/a)
\t* [paper](https://arxiv.org/abs/1111)
* [Project B](https://github.com/b)
\t* [paper](https://arxiv.org/abs/1111)
"""
    papers = parse_readme(readme)
    assert len(papers) == 2
    # First occurrence should not have duplicate_of set
    assert papers[0].duplicate_of is None
    # Second occurrence should have duplicate_of pointing to first (1-based index)
    assert papers[1].duplicate_of == 1


def test_parse_readme_multiple_papers():
    """Test parsing multiple paper entries."""
    readme = """\
# Deep Learning
* [Project A](https://github.com/a)
\t* [paper](https://arxiv.org/abs/1111)
* [Project B](https://github.com/b)
\t* [paper](https://arxiv.org/abs/2222)

# Geology
* [Project C](https://github.com/c)
\t* [paper](https://doi.org/10.1234/5678)
"""
    papers = parse_readme(readme)
    assert len(papers) == 3
    urls = {p.url for p in papers}
    assert "https://arxiv.org/abs/1111" in urls
    assert "https://arxiv.org/abs/2222" in urls
    assert "https://doi.org/10.1234/5678" in urls


def test_parse_readme_empty():
    """Test parsing an empty README."""
    papers = parse_readme("")
    assert papers == []


def test_parse_readme_no_papers():
    """Test parsing a README with no paper links."""
    readme = """\
# My Project
This is a project without any paper links.
* [GitHub](https://github.com/example)
"""
    papers = parse_readme(readme)
    assert papers == []


def test_parse_readme_honours_thesis_link():
    """Test parsing [Honours Thesis](url) links."""
    readme = """\
# Theses
* [Some Project](https://github.com/example)
\t* [Honours Thesis](https://www.researchgate.net/thesis.pdf)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].resource_type == ResourceType.THESIS


def test_extract_parent_context():
    """Test extracting parent bullet context."""
    lines = [
        "# Section",
        "* [Parent Project](https://github.com/parent) -> Description",
        "\t* [paper](https://arxiv.org/abs/1234)",
    ]
    title, url = _extract_parent_context(lines, 2)
    assert title == "Parent Project"
    assert url == "https://github.com/parent"


def test_extract_parent_context_no_parent():
    """Test extracting parent context when there is no parent."""
    lines = [
        "# Section",
        "* [paper](https://arxiv.org/abs/1234)",
    ]
    title, url = _extract_parent_context(lines, 1)
    # No parent bullet with smaller indent
    assert title == ""
    assert url == ""


def test_anchor_link_filtered():
    """Test that GitHub anchor links (e.g. repo#section) are filtered out."""
    readme = """\
# Table of Contents
* [Papers](https://github.com/RichardScottOZ/mineral-exploration-machine-learning#papers)
"""
    papers = parse_readme(readme)
    assert papers == []


def test_thesis_url_cleaned():
    """Test that thesis URLs with markdown artifacts are cleaned."""
    readme = """\
# Ontology
* [geosim](https://github.com/smolang/SemanticObjects/tree/geosim)
\t* [https://www.duo.uio.no/handle/10852/111467](Knowledge Modelling) -> PhD thesis
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://www.duo.uio.no/handle/10852/111467"
    assert "]" not in papers[0].url


def test_default_repo_constants():
    """Test that default repo constants are set correctly."""
    assert DEFAULT_REPO_OWNER == "RichardScottOZ"
    assert DEFAULT_REPO_NAME == "mineral-exploration-machine-learning"


# ---------------------------------------------------------------------------
# Tests for academic URL detection (patterns 4 & 5)
# ---------------------------------------------------------------------------


def test_is_academic_url():
    """Test that _is_academic_url correctly identifies academic publication URLs."""
    # Positive cases
    assert _is_academic_url("https://www.researchgate.net/publication/12345_Some_Paper")
    assert _is_academic_url("https://www.researchgate.net/profile/Author/publication/12345/links/abc/Paper.pdf")
    assert _is_academic_url("https://arxiv.org/abs/2301.12345")
    assert _is_academic_url("https://arxiv.org/pdf/2301.12345.pdf")
    assert _is_academic_url("https://arxiv.org/html/2401.10825v3")
    assert _is_academic_url("https://www.sciencedirect.com/science/article/pii/S0098300424000839")
    assert _is_academic_url("https://link.springer.com/article/10.1007/s12345")
    assert _is_academic_url("https://www.nature.com/articles/s41467-021-24025-8")
    assert _is_academic_url("https://ieeexplore.ieee.org/abstract/document/10605826")
    assert _is_academic_url("https://doi.org/10.1016/j.oregeorev.2020.103611")
    assert _is_academic_url("https://www.mdpi.com/2075-163X/15/11/1125")
    assert _is_academic_url("https://eartharxiv.org/repository/view/7417/")
    assert _is_academic_url("https://pure.mpg.de/rest/items/item_3029184_8/component/file_3282959/content")

    # Negative cases (non-academic)
    assert not _is_academic_url("https://github.com/example/project")
    assert not _is_academic_url("https://www.researchgate.net/")
    assert not _is_academic_url("https://www.researchgate.net/project/SomeProject")
    assert not _is_academic_url("https://www.researchgate.net/post/SomeQuestion")
    assert not _is_academic_url("https://www.sciencedirect.com/journal/some-journal")
    assert not _is_academic_url("https://www.youtube.com/watch?v=abc")
    assert not _is_academic_url("https://en.wikipedia.org/wiki/Machine_learning")


def test_parse_readme_bare_researchgate_url():
    """Test parsing bare ResearchGate publication URLs on a line."""
    readme = """\
# Prospectivity
- https://www.researchgate.net/publication/358956673_Towards_a_fully_data-driven_prospectivity_mapping_methodology
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert "researchgate.net/publication/358956673" in papers[0].url
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_bare_arxiv_url_with_arrow_title():
    """Test parsing bare arXiv URL with -> title."""
    readme = """\
# Deep Learning
- https://arxiv.org/abs/2408.11804 -> Approaching Deep Learning through the Spectral Dynamics of Weights
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://arxiv.org/abs/2408.11804"
    assert papers[0].title == "Approaching Deep Learning through the Spectral Dynamics of Weights"
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_bare_sciencedirect_url():
    """Test parsing bare ScienceDirect URL."""
    readme = """\
# Geochemistry
- https://www.sciencedirect.com/science/article/abs/pii/S0098300424000839#sec6 -> Leveraging automated deep learning (AutoDL) in geosciences
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert "sciencedirect.com/science/article" in papers[0].url
    assert papers[0].title == "Leveraging automated deep learning (AutoDL) in geosciences"


def test_parse_readme_markdown_link_academic_url():
    """Test parsing [Title](academic_url) links to known academic domains."""
    readme = """\
# Geochemistry
* [GeoCoDa](https://www.researchgate.net/publication/372487589_GeoCoDA_Recognizing)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].title == "GeoCoDa"
    assert "researchgate.net/publication/372487589" in papers[0].url
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_markdown_link_with_space_before_paren():
    """Test parsing [Title] (url) with extra space before parenthesis."""
    readme = """\
# Models
* [Geological Everything Model] (https://arxiv.org/abs/2507.00419) -> A Foundation Model
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].title == "Geological Everything Model"
    assert papers[0].url == "https://arxiv.org/abs/2507.00419"


def test_parse_readme_paper_label_no_parens():
    """Test parsing [paper]url (no parentheses, no arrow)."""
    readme = """\
# NLP
* [Some NER Project](https://github.com/example)
\t* [paper]https://www.researchgate.net/publication/359186219_Few-shot_learning
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert "researchgate.net/publication/359186219" in papers[0].url
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_paper_label_space_no_arrow():
    """Test parsing [paper] url (space but no arrow)."""
    readme = """\
# Geochemistry
* [Some Project](https://github.com/example)
\t* [paper] https://www.researchgate.net/publication/380289934_Secular_Changes
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert "researchgate.net/publication/380289934" in papers[0].url
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_bare_url_no_space_after_dash():
    """Test parsing -https://url (missing space after dash)."""
    readme = """\
# NLP
-https://arxiv.org/html/2401.10825v3 -> Recent Advances in Named Entity Recognition
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].url == "https://arxiv.org/html/2401.10825v3"
    assert papers[0].title == "Recent Advances in Named Entity Recognition"


def test_parse_readme_non_academic_url_excluded():
    """Test that non-academic URLs are NOT captured by patterns 4 & 5."""
    readme = """\
# Resources
* [MyProject](https://github.com/example/project) -> Description
- https://github.com/example/another -> Another repo
- https://www.youtube.com/watch?v=abc -> Some video
- https://zenodo.org/record/123 -> A dataset
"""
    papers = parse_readme(readme)
    assert len(papers) == 0


def test_parse_readme_researchgate_homepage_excluded():
    """Test that ResearchGate homepage link is NOT captured."""
    readme = """\
# Resources
* [ResearchGate](https://www.researchgate.net/) -> Researcher and professional network
"""
    papers = parse_readme(readme)
    assert len(papers) == 0


def test_parse_readme_dedup_academic_and_paper_label():
    """Test that a URL captured by [paper](url) is not also captured by academic URL pattern."""
    readme = """\
# Section
* [Project A](https://github.com/a)
\t* [paper](https://www.researchgate.net/publication/12345_Test)
"""
    papers = parse_readme(readme)
    assert len(papers) == 1
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_multiple_academic_domains():
    """Test parsing multiple different academic domains in one README."""
    readme = """\
# Papers
- https://www.researchgate.net/publication/12345_Paper_A
- https://arxiv.org/abs/2301.12345 -> Paper B
- https://www.nature.com/articles/s41467-021-24025-8 -> Paper C
- https://ieeexplore.ieee.org/abstract/document/10605826 -> Paper D
- https://link.springer.com/article/10.1007/s12345 -> Paper E
"""
    papers = parse_readme(readme)
    assert len(papers) == 5
    urls = {p.url for p in papers}
    assert any("researchgate.net" in u for u in urls)
    assert any("arxiv.org" in u for u in urls)
    assert any("nature.com" in u for u in urls)
    assert any("ieeexplore.ieee.org" in u for u in urls)
    assert any("springer.com" in u for u in urls)


# ---------------------------------------------------------------------------
# Tests for aggressive parsing patterns
# ---------------------------------------------------------------------------


def test_parse_readme_missing_https_prefix():
    """Test parsing [paper](www.sciencedirect.com/...) with missing https://."""
    readme = """\
# Geochemistry
* [paper](www.sciencedirect.com/science/article/pii/S0098300424000839)
"""
    papers = parse_readme(readme, aggressive=True)
    assert len(papers) >= 1
    # Should have at least one paper with the sciencedirect URL
    assert any('sciencedirect.com/science/article/pii/S0098300424000839' in p.url for p in papers)
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_double_parens():
    """Test parsing [paper]((url)) with double parentheses."""
    readme = """\
# Deep Learning
* [Project](https://github.com/example)
\t* [paper]((https://arxiv.org/abs/2301.12345))
"""
    papers = parse_readme(readme, aggressive=True)
    assert len(papers) == 1
    assert papers[0].url == "https://arxiv.org/abs/2301.12345"
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_unseen_tag():
    """Test parsing [UNSEEN] tag detection."""
    readme = """\
# Prospectivity
* [Project A](https://github.com/a)
\t* [paper](https://arxiv.org/abs/1111) [UNSEEN]
* [Project B](https://github.com/b)
\t* [paper](https://arxiv.org/abs/2222)
"""
    papers = parse_readme(readme, aggressive=True)
    assert len(papers) == 2
    assert papers[0].unseen_tag is True
    assert papers[1].unseen_tag is False


def test_parse_readme_file_path_human_error():
    """Test that file:/// paths are flagged as human error."""
    readme = """\
# Papers
* [paper](file:///home/user/papers/paper.pdf)
"""
    papers = parse_readme(readme, aggressive=True)
    assert len(papers) == 1
    assert papers[0].url == "file:///home/user/papers/paper.pdf"
    assert papers[0].accessibility_status == AccessibilityStatus.HUMAN_ERROR


def test_parse_readme_section_path_extraction():
    """Test that section hierarchy is correctly extracted."""
    readme = """\
# Prospectivity
## Oceania
### Australia
#### South Australia
* [Project](https://github.com/example)
\t* [paper](https://arxiv.org/abs/1234)
"""
    papers = parse_readme(readme, aggressive=True)
    assert len(papers) == 1
    assert papers[0].section_path == "Prospectivity/Oceania/Australia/South_Australia"


def test_parse_readme_section_path_multiple_levels():
    """Test section path with different heading levels."""
    readme = """\
# Remote Sensing
## Hyperspectral
* [Project A](https://github.com/a)
\t* [paper](https://arxiv.org/abs/1111)

# Geochemistry
* [Project B](https://github.com/b)
\t* [paper](https://arxiv.org/abs/2222)
"""
    papers = parse_readme(readme, aggressive=True)
    assert len(papers) == 2
    assert papers[0].section_path == "Remote_Sensing/Hyperspectral"
    assert papers[1].section_path == "Geochemistry"


def test_parse_readme_non_document_exclusions():
    """Test that non-document URLs are excluded (datasets, videos, notebooks, etc.)."""
    readme = """\
# Resources
- https://www.youtube.com/watch?v=abc -> Video tutorial
- https://medium.com/@author/article -> Blog post
- https://colab.research.google.com/drive/abc -> Notebook
- https://zenodo.org/record/123 -> Dataset
- https://figshare.com/articles/dataset/123 -> Dataset
- https://github.com/example/repo -> Code repository
"""
    papers = parse_readme(readme, aggressive=True)
    # None of these should be captured as papers
    assert len(papers) == 0


def test_parse_readme_github_repo_with_paper_label():
    """Test that GitHub repos labeled as papers ARE captured."""
    readme = """\
# Papers
* [paper](https://github.com/example/paper-repo) -> Paper about the repo
"""
    papers = parse_readme(readme, aggressive=True)
    assert len(papers) == 1
    assert papers[0].url == "https://github.com/example/paper-repo"
    assert papers[0].resource_type == ResourceType.PAPER


def test_parse_readme_trailing_punctuation_cleaned():
    """Test that trailing punctuation is cleaned from URLs."""
    readme = """\
# Papers
- https://arxiv.org/abs/2301.12346, -> Paper with comma
"""
    papers = parse_readme(readme, aggressive=True)
    assert len(papers) == 1
    assert papers[0].url == "https://arxiv.org/abs/2301.12346"
