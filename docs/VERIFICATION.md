# Verification record

Verified locally on 2026-10-22. This is a bounded v0.1 implementation; passing checks do not establish general correctness or product-market demand.

- Python 3.11: **15 tests passed**.
- Python 3.13: **15 tests passed**.
- CLI help and version 0.1.0: passed.
- Runtime package compilation: passed.
- Offline wheel build and isolated installed console entry point: passed.
- Original logo and mark: valid SVG XML.

```sh
python -m unittest discover -s tests -v
python -m intent_workbench --help
python -m intent_workbench --version
```

The README fixture workflow was run locally with temporary output files and its documented success/adverse exit statuses were checked. The test suite includes invalid inputs and substantive adverse cases.

## Model workflow

The product brief and implementation plan were written first by GPT-6 Astra with high reasoning. GPT-6 Luna with high reasoning implemented the bounded plan. The primary agent independently checked this implementation and retained regression tests where needed. A separate higher-thinking reviewer performed focused portfolio audits of the interactive tools, study/glossary behavior, and publication controls. These model names describe this build process, not runtime dependencies.

## Publication

GitHub CI is configured for Python 3.11 and 3.13. Remote CI and GitHub publication are not established by this local verification record.

## Interactive export coverage

JavaScript syntax checks, HTML/script escaping checks, and installed offline HTML generation passed. Intent Workbench also has Python/JavaScript evaluator parity checks. The strict frontend static audit reports zero findings.

Browser interaction, responsive rendering, and screen-reader behavior were not verified because no browser session is available. The official DESIGN.md package linter is unavailable offline; the static audit does not replace it or runtime browser checks.
