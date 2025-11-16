# Browser Organiser Tests

This directory contains all test files for the Browser Organiser MCP project.

## Test Files

### Core Component Tests

- **test_models.py** - Pydantic model validation and serialization
  - Bookmark creation and validation
  - Folder structures and recursion
  - WebKit timestamp parsing
  - JSON serialization/deserialization

- **test_utils.py** - Utility functions
  - Edge bookmarks path detection
  - Domain extraction
  - Bookmark/folder conversion to dict
  - Domain statistics

- **test_categorizer.py** - Rule-based categorization
  - Category loading from YAML
  - Domain/URL/keyword matching
  - Priority-based selection
  - Batch categorization

- **test_knowledge_base.py** - Knowledge base features
  - Service method verification
  - Mock bookmark workflows
  - JSON serialization for MCP
  - Usage scenarios

## Running Tests

### Run All Tests

```bash
# From project root
python tests/test_models.py
python tests/test_utils.py
python tests/test_categorizer.py
python tests/test_knowledge_base.py
```

### Run Individual Test

```bash
python tests/test_categorizer.py
```

### With pytest (if installed)

```bash
pytest tests/
pytest tests/test_models.py -v
```

## Test Results

All tests should pass with output like:

```
============================================================
Testing Pydantic Models for Browser Organiser
============================================================

✓ All tests passed!
```

## Adding New Tests

When adding new features:

1. Create a new test file: `tests/test_feature_name.py`
2. Follow existing test structure
3. Include docstrings explaining what's being tested
4. Run tests to verify they pass
5. Update this README if needed

## Test Coverage

Current test coverage:
- ✅ Pydantic models (12 models)
- ✅ Utility functions (10+ functions)
- ✅ Rule-based categorizer (25 categories, 99 rules)
- ✅ Knowledge base methods (3 new methods)
- ⏳ BrowserCleanerService (integration tests)
- ⏳ MCP tools (end-to-end tests)

## Notes

- Tests use mock data where possible
- Edge bookmarks path detection may fail if Edge is not installed
- Some tests require the config/categories.yaml file
- No actual bookmark modifications are made during testing
