import os
import argparse
import glob
import pandas as pd
import re
import sys

def concat_timeseries(data_dir, output_dir="timeseries_concatenated", exclude_runs=None):
    """
    Concatenates time series CSV files for each subject.

    Parameters:
    - data_dir: Root directory containing subject folders and time series CSVs.
    - output_dir: Directory to save the concatenated CSV files.
    - exclude_runs: List of run identifiers to exclude (e.g., ['run-01', 'run-02']).
    """

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Find all timeseries files
    # We assume the standard naming from extract_timeseries.py which produces `*_timeseries.csv`
    search_pattern = "**/*_timeseries.csv"
    print(f"Searching for files in: {data_dir}")
    files = glob.glob(os.path.join(data_dir, search_pattern), recursive=True)

    if not files:
        print("No timeseries files found.")
        return

    # Group files by subject
    subjects = {}

    # Regex to extract subject ID (sub-XXXX)
    # We assume the filename or parent folder contains the subject ID.
    # Standard BIDS-like naming usually puts `sub-01` at the start of the filename.
    sub_pattern = re.compile(r'(sub-[a-zA-Z0-9]+)')

    for file_path in files:
        filename = os.path.basename(file_path)
        match = sub_pattern.search(filename)

        if match:
            sub_id = match.group(1)
            if sub_id not in subjects:
                subjects[sub_id] = []
            subjects[sub_id].append(file_path)
        else:
            print(f"Warning: Could not extract subject ID from {filename}. Skipping.")

    print(f"Found {len(subjects)} subjects.")

    for sub_id, sub_files in subjects.items():
        print(f"\nProcessing {sub_id}...")

        # Sort files to ensure chronological order (assuming runs are named sequentially like run-01, run-02)
        sub_files.sort()

        files_to_concat = []

        for file_path in sub_files:
            # Check for exclusions
            if exclude_runs:
                exclude = False
                for run_id in exclude_runs:
                    # Check if run_id exists in the filename
                    # Use a robust check similar to batch_extract.py
                    pattern = re.escape(run_id) + r'(?:[^a-zA-Z0-9]|$)'
                    if re.search(pattern, os.path.basename(file_path)):
                        print(f"  Excluding: {os.path.basename(file_path)}")
                        exclude = True
                        break
                if exclude:
                    continue

            files_to_concat.append(file_path)

        if not files_to_concat:
            print(f"  No files left to concatenate for {sub_id} after exclusions.")
            continue

        print(f"  Concatenating {len(files_to_concat)} files.")

        dfs = []
        for fp in files_to_concat:
            try:
                df = pd.read_csv(fp)
                dfs.append(df)
            except Exception as e:
                print(f"  Error reading {fp}: {e}")

        if dfs:
            concatenated_df = pd.concat(dfs, ignore_index=True)

            output_filename = f"{sub_id}_concatenated_timeseries.csv"
            output_path = os.path.join(output_dir, output_filename)

            concatenated_df.to_csv(output_path, index=False)
            print(f"  Saved to {output_path} (Shape: {concatenated_df.shape})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concatenate timeseries CSV files by subject.")

    parser.add_argument("data_dir", help="Root directory containing timeseries CSV files.")
    parser.add_argument("--output_dir", default="timeseries_concatenated", help="Directory to save concatenated files.")
    parser.add_argument("--exclude-runs", help="Comma-separated list of runs to exclude (e.g., 'run-01,run-03').", default=None)

    args = parser.parse_args()

    if not os.path.exists(args.data_dir):
        print(f"Error: Data directory {args.data_dir} not found.")
        sys.exit(1)

    exclude_runs = []
    if args.exclude_runs:
        exclude_runs = [r.strip() for r in args.exclude_runs.split(',')]

    concat_timeseries(args.data_dir, args.output_dir, exclude_runs)
