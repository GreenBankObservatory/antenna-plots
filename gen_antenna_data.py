import hashlib
import json
import sys
import argparse
import logging
import math
from collections import defaultdict, namedtuple
from pathlib import Path
from time import perf_counter
import concurrent.futures
import multiprocessing

import astropy.units as u
from astropy.coordinates import Angle
from astropy.table import Column, MaskedColumn, Table, vstack as table_vstack
from astropy.io import fits
import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)

Coordinates = namedtuple("Coordinates", ["x", "y"])
Boundaries = namedtuple("Boundaries", ["left", "bottom", "right", "top"])
# import matplotlib.style as mplstyle
# mplstyle.use('fast')


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super(self.__class__, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg, file=sys.stderr)
            # self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


class Benchmark:
    def __init__(self, description=None, logger=None):
        self._initial_time = perf_counter()
        self._logger = logger if logger else print
        self.description = "Did stuff" if description is None else description

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        _end = perf_counter()
        defaultdict(float)
        self._logger(f"{self.description} in {_end - self._initial_time:.3f} seconds ")


def process_antenna_fits(antenna_path: Path, time_resolution=60) -> Table:
    antenna_hdulist = fits.open(antenna_path, memmap=True)
    try:
        antenna_positions = antenna_hdulist["ANTPOSPF"]
    except KeyError as error:
        try:
            antenna_positions = antenna_hdulist["ANTPOSGR"]
        except KeyError:
            logger.error(f"Failed to find ANTPOSPF or ANTPOSGR table in {antenna_path}")
            return Table()
    # Resolution is 0.1 seconds, so we read every 10 * 60 seconds to get the position every minute
    if time_resolution != 0.1:
        reduced = antenna_positions.data[:: math.floor(10 * time_resolution)]
    else:
        # In this special case, don't bother indexing
        reduced = antenna_positions.data
    table = Table(reduced)["DMJD", "RAJ2000", "DECJ2000", "MNT_AZ", "MNT_EL"]
    if table:
        table["RAJ2000"] = Angle(table["RAJ2000"], unit=u.degree)
        table["DECJ2000"] = Angle(table["DECJ2000"], unit=u.degree)
        table["Scan"] = antenna_hdulist["PRIMARY"].header["SCAN"]
        return table
    return Table()


def get_data_for_batch(
    antenna_paths: list[Path], output_path: Path, time_resolution=60
):
    table = table_vstack(
        [
            process_antenna_fits(path, time_resolution=time_resolution)
            for path in antenna_paths
        ]
    )
    logger.debug(f"Writing to {output_path}")
    table.to_pandas().to_parquet(output_path, engine="pyarrow")
    return table


def gen_path_cache(session_root: Path):
    total_sessions = 0
    total_antenna_files = 0
    session_to_antenna = {}
    for session_path in tqdm(
        list(session_root.iterdir()), unit="session", dynamic_ncols=True
    ):
        if session_path.is_dir():
            antenna_paths = [str(p) for p in (session_path / "Antenna").glob("*.fits")]
            if antenna_paths:
                session_to_antenna[str(session_path)] = antenna_paths
                total_sessions += 1
                total_antenna_files += len(antenna_paths)

    path_cache = {
        "session_to_antenna": session_to_antenna,
        "total_sessions": total_sessions,
        "total_antenna_files": total_antenna_files,
    }

    return path_cache


def stack(output_dir: Path, final_output_path: Path):
    to_stack = []
    output_files = list(output_dir.glob("*.parquet"))
    for path in tqdm(output_files, unit="file"):
        try:
            df = pd.read_parquet(path)
        except ValueError as error:
            raise ValueError(f"Failed to read {path}") from error
        to_stack.append(df)
        logger.debug(f"Processed {path}")
    stacked = pd.concat(to_stack)
    print(
        f"Writing {len(stacked)} antenna positions from {len(output_files)} "
        f"files to {final_output_path}"
    )
    stacked.to_parquet(final_output_path, engine="pyarrow")
    return stacked


def gen_antenna_data(
    session_to_antenna: dict[str, list[str]], output_dir: Path, time_resolution: float
):
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=multiprocessing.cpu_count() // 2,
    ) as executor:
        future_to_session = {}

        total_sessions = 0
        total_antenna_files = 0
        for session_path, antenna_paths in session_to_antenna.items():
            output_path = output_dir / f"{Path(session_path).name}.parquet"
            if not output_path.exists():
                future = executor.submit(
                    get_data_for_batch,
                    antenna_paths=antenna_paths,
                    output_path=output_path,
                    time_resolution=time_resolution,
                )
                future_to_session[future] = (session_path, len(antenna_paths))
                total_sessions += 1
                total_antenna_files += len(antenna_paths)
            else:
                tqdm.write(f"Skipping {Path(session_path).name}; {output_path} exists")

        logger.info(
            f"Processing {total_antenna_files} across {total_sessions} sessions"
        )
        antenna_progress = tqdm(
            total=total_antenna_files,
            unit="file",
            smoothing=0.3,
            dynamic_ncols=True,
        )
        for future in concurrent.futures.as_completed(future_to_session):
            session_path, num_antenna_files = future_to_session[future]
            try:
                future.result()
            except Exception as error:
                print(
                    f"Error in {session_path}: {error}",
                    file=sys.stderr,
                    flush=True,
                )
            finally:
                tqdm.write(session_path)
                antenna_progress.update(num_antenna_files)
                # antenna_progress.set_description(Path(session_path).name)


def init_logging(level=logging.DEBUG):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    logger.setLevel(level)
    console_handler = TqdmLoggingHandler()
    console_handler.setLevel(level)
    # See: https://docs.python.org/3/library/logging.html#logrecord-attributes
    formatter = logging.Formatter("[%(asctime)s - %(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "session_roots",
        type=Path,
        nargs="+",
        help="Path to session root",
    )
    parser.add_argument(
        "final_output_path",
        type=Path,
        help="Path at which to save the final stacked Parquet file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory under which to save Antenna FITS data cache files",
        default=Path("./session_antenna_fits"),
    )
    parser.add_argument(
        "-R",
        "--time-resolution",
        type=float,
        help="Interval in seconds at at which to sample antenna positions",
        default=1,
    )
    parser.add_argument("-v", "--verbosity", type=int, choices=range(0, 4), default=1)
    return parser.parse_args()


def md5(string):
    hash_object = hashlib.md5(string.encode("utf8"))
    return hash_object.hexdigest()


def main():
    print("START")
    args = parse_args()
    if args.verbosity > 2:
        loglevel = logging.DEBUG
    elif args.verbosity == 2:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARNING

    init_logging(loglevel)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    session_dir_cache_path = Path("./session_root_cache")
    session_dir_cache_path.mkdir(parents=True, exist_ok=True)
    path_cache = {
        "total_antenna_files": 0,
        "total_sessions": 0,
        "session_to_antenna": {},
    }
    session_root_progress = tqdm(
        args.session_roots, unit="session_root", dynamic_ncols=True
    )
    for session_root in session_root_progress:
        session_root_progress.set_description(f"{session_root}")
        session_root_cache_path = session_dir_cache_path / Path(
            f"{md5(str(session_root))}.json"
        )
        if session_root_cache_path.exists():
            logger.info(f"Found {session_root_cache_path} cache")
            with open(session_root_cache_path, encoding="utf-8") as file:
                session_root_cache = json.load(file)
        else:
            session_root_cache = gen_path_cache(session_root)
            with open(session_root_cache_path, "w", encoding="utf-8") as file:
                json.dump(session_root_cache, file)
        path_cache["total_sessions"] += session_root_cache["total_sessions"]
        path_cache["total_antenna_files"] += session_root_cache["total_antenna_files"]
        path_cache["session_to_antenna"].update(
            session_root_cache["session_to_antenna"]
        )

    print(
        f"Found {path_cache['total_antenna_files']} Antenna FITS files across "
        f" {len(path_cache['session_to_antenna'])} sessions "
        f"(from {len(args.session_roots)} session roots)"
    )
    gen_antenna_data(
        path_cache["session_to_antenna"],
        output_dir=args.output_dir,
        time_resolution=args.time_resolution,
    )
    stack(args.output_dir, args.final_output_path)


if __name__ == "__main__":
    with Benchmark("TOTAL"):
        main()
