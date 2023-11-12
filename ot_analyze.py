import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

from write_failed_analysis import write_failed_analysis


def generate_analysis_path(protocol_file: Path) -> Path:
    """
    Takes a Path to a protocol file and returns a Path to the analysis file that
    should be generated by the analyze command.

    :param protocol_file: A Path to a protocol file.
    :return: A Path to the analysis file that should be generated by the analyze command.
    """
    return Path(protocol_file.parent, f"{protocol_file.stem}_analysis.json")


def analyze(protocol_file: Path):
    start_time = time.time()  # Start timing
    analysis_file = generate_analysis_path(protocol_file)
    custom_labware_directory = os.path.join(protocol_file.parent, "custom_labware")

    custom_labware = []
    if os.path.isdir(custom_labware_directory):
        custom_labware = [
            os.path.join(custom_labware_directory, file) for file in os.listdir(custom_labware_directory) if file.endswith(".json")
        ]

    command = [
        "python",
        "-I",
        "-m",
        "opentrons.cli",
        "analyze",
        "--json-output",
        analysis_file,
        protocol_file,
    ] + custom_labware
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
    except Exception as e:
        print(f"Error in analysis of {protocol_file}")
        write_failed_analysis(analysis_file, str(e))
        end_time = time.time()
        return end_time - start_time
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Successful analysis of {protocol_file} completed in {elapsed_time:.2f} seconds")
    return elapsed_time


def run_analyze_in_parallel(protocol_files: List[Path]):
    start_time = time.time()
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(analyze, file) for file in protocol_files]
        accumulated_time = 0
        for future in as_completed(futures):
            try:
                accumulated_time += future.result()  # This blocks until the future is done
            except Exception as e:
                print(f"An error occurred: {e}")
        end_time = time.time()
        clock_time = end_time - start_time
        print(
            f"""{protocol_files.len()} protocols with total analysis time of {accumulated_time:.2f}
            seconds analyzed in {clock_time:2f} seconds thanks to parallelization
            """
        )


def find_python_files(directory: Path) -> List[Path]:
    # Check if the provided path is a valid directory
    if not directory.is_dir():
        raise NotADirectoryError(f"The path {directory} is not a valid directory.")

    # Recursively find all .py files
    python_files = list(directory.rglob("*.py"))

    return python_files


if __name__ == "__main__":
    repo_relative_path = Path(os.getenv("GITHUB_WORKSPACE"), os.getenv("INPUT_BASE_DIRECTORY"))
    print(f"Analyzing all .py files in {repo_relative_path}")
    python_files = find_python_files(repo_relative_path)
    run_analyze_in_parallel(python_files)
