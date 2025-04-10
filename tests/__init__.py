"""
This file is a basic implementation of `python -m unittest discover`. We use this
instead of the CLI due to poetry's scripting limitation and that everything has
to be a Python function. This is linked to all packages
"""

import sys
import unittest


def main():
    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner()
    result = runner.run(loader.discover("."))
    if not result.wasSuccessful():
        sys.exit(1)
