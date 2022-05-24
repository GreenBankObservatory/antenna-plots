#! /usr/bin/env python3


import argparse
from pathlib import Path

from astropy.table import Table
import fastparquet

def fits_to_parquet(input_path: Path, output_path: Path):
    print(f"Reading {input_path}...")
    table = Table.read(input_path)
    print(f"Converting to pandas...")
    df = table.to_pandas()
    print("Filtering...")
    filtered = df[
        (df["RAJ2000"] >= -180)
        & (df["RAJ2000"] <= 180)
        & (df["DECJ2000"] >= -90)
        & (df["DECJ2000"] <= 90)
    ]
    print(f"Filtered from {len(df)} to {len(filtered)} rows")
    print(f"Writing to {output_path}...")
    # fastparquet.write(filtered, output_path)
    filtered.to_parquet(output_path, engine="pyarrow")



def main():
    args = parse_args()

    output_path = (
        f"{args.input_path.stem}.parquet" if args.output_path is None else args.output_path
    )
    fits_to_parquet(args.input_path, output_path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_path", type=Path, nargs="?")
    parser.add_argument("-v", "--verbosity", choices=[0, 1, 2, 3], type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
