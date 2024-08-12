import unittest


def main():
    loader = unittest.TestLoader()
    runner = unittest.TextTestRunner()
    runner.run(loader.discover("."))
