# Contributing to Paper Accessibility Checker

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mineral-exploration-machine-learning-public-paper-check.git
   cd mineral-exploration-machine-learning-public-paper-check
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .[dev]
   playwright install chromium
   ```

## Development Workflow

1. Create a new branch for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Run tests:
   ```bash
   pytest tests/ -v
   ```

4. Format your code:
   ```bash
   black paper_checker/
   ruff check paper_checker/
   ```

5. Commit your changes:
   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

6. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

7. Open a Pull Request

## Code Style

- Follow PEP 8 guidelines
- Use Black for code formatting (line length: 100)
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and modular

## Testing

- Write tests for new features
- Ensure all tests pass before submitting a PR
- Aim for good test coverage
- Use pytest for testing

## Project Structure

```
paper_checker/
├── __init__.py      # Package initialization
├── models.py        # Data models
├── database.py      # Database operations
├── checker.py       # Accessibility checking
└── cli.py          # Command-line interface

tests/
└── test_*.py       # Test files

data/
├── sample_papers.json
└── sample_papers.csv

examples/
└── basic_usage.py
```

## Areas for Contribution

### High Priority
- BibTeX import/export support
- Automatic paper download functionality
- Saved credentials for authentication
- More comprehensive tests
- Better error handling

### Medium Priority
- Web interface
- Integration with reference managers (Zotero, Mendeley)
- Advanced search with full-text indexing
- Citation graph visualization
- Batch processing with progress bars

### Low Priority
- Email notifications
- Paper similarity detection
- Additional export formats
- Performance optimizations

## Pull Request Guidelines

1. **Title**: Use a clear, descriptive title
2. **Description**: Explain what your PR does and why
3. **Tests**: Include tests for new features
4. **Documentation**: Update README if needed
5. **Small Changes**: Keep PRs focused on a single feature/fix
6. **Code Quality**: Ensure code passes linting and tests

## Reporting Bugs

When reporting bugs, please include:

1. Python version
2. Operating system
3. Steps to reproduce
4. Expected vs actual behavior
5. Error messages or logs
6. Minimal code example (if applicable)

## Feature Requests

Feature requests are welcome! Please:

1. Check if the feature already exists or is planned
2. Describe the use case clearly
3. Explain why it would be useful
4. Provide examples if possible

## Code Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged
4. Your contribution will be acknowledged in release notes

## Questions?

Feel free to open an issue for any questions about contributing.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Every contribution helps make this project better. Thank you for taking the time to contribute!
