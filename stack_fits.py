import argparse
from pathlib import Path

from astropy.table import Table, vstack
from astropy.io import fits
from tqdm import tqdm

def stack_fits_files(antenna_paths: list[Path]):
    """Print out the names of every path in antenna_paths"""
    # TODO: Open all Antenna FITS files as astropy Tables and stack them together
    # See: https://docs.astropy.org/en/stable/table/
    # Important: the antenna data you want will be in  HDU index 2!

    table = []

    for i in antenna_paths:
        antenna_data = fits.open(i)
        set_table = Table(antenna_data[2].data)
        table.append(set_table)
        antenna_data.close()
        
    stack_table = vstack(table)
    print(stack_table)

def parse_args():
    """Parse CLI arguments"""

    parser = argparse.ArgumentParser()
    parser.add_argument("antenna_paths", nargs="+", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    # TODO: pass stack_fits_files the antenna paths that argparse has parsed for you!
    stack_fits_files(antenna_paths=args.antenna_paths)


if __name__ == "__main__":
    main()