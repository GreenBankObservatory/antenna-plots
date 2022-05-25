import argparse
from pathlib import Path


def stack_fits_files(antenna_paths: list[Path]):
    """Print out the names of every path in antenna_paths"""
    # TODO: Complete this method body

    for i in antenna_paths:
        print(i.name)


def parse_args():
    """Parse CLI arguments"""

    parser = argparse.ArgumentParser()
    # TODO: Fill out the add_argument method call, using the docs/examples here:
    # https://docs.python.org/3/library/argparse.html?highlight=argparse#example
    # Hint: you have to handle ONE OR MORE paths
    parser.add_argument('path',type=Path, nargs='+')
    return parser.parse_args()


def main():
    args = parse_args()
    # TODO: pass stack_fits_files the antenna paths that argparse has parsed for you!
    stack_fits_files(antenna_paths=args.path)

if __name__ == "__main__":
    main()