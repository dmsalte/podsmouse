"""Run the vendored mousepods test suite (upstream/tests) as part of our own test run.

`python -m unittest discover -s tests` then covers both our code and the upstream
protocol and motion engine, so an upstream update that breaks something shows up at once.
The upstream tests need no hardware and no third-party packages.
"""

import pathlib
import unittest

UPSTREAM_TESTS = pathlib.Path(__file__).resolve().parent.parent / "upstream" / "tests"


def load_tests(loader, standard_tests, pattern):
    suite = unittest.TestSuite()
    suite.addTests(
        loader.discover(
            start_dir=str(UPSTREAM_TESTS),
            pattern="test_*.py",
            top_level_dir=str(UPSTREAM_TESTS),
        )
    )
    return suite
