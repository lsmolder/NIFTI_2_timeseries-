import os
import argparse
import glob
import sys
import re
from extract_timeseries import extract_timeseries

def find_transform(subject_id, transforms_dir, transform_suffix):
    """
    Finds a transform file for a specific subject in the transforms directory.

    Parameters:
    - subject_id: String like "sub-01"
    - transforms_dir: Root directory for transforms
    - transform_suffix: Suffix to look for (e.g. "anat_to_atlas_warp.nii.gz")

    Returns:
    - Path to the transform file, or None if not found.
    """
    # We look for files recursively that match the subject ID and the suffix
    # Pattern: *subject_id*suffix
    # Note: Using glob with recursive=True

    # We construct a pattern that ensures subject_id is part of the filename
    # and it ends with the suffix.
    # We iterate to find the specific file because globbing specific filenames recursively
    # with complex patterns is tricky in all OS/versions.
    # Simpler approach: glob all files recursively, then filter.

    # But transforms_dir might be huge.
    # Let's try to target the search.
    # Usually files are in subfolders.

    # Heuristic: Search recursively for *suffix
    # Then filter for subject_id
    search_pattern = f"**/*{transform_suffix}"
    candidates = glob.glob(os.path.join(transforms_dir, search_pattern), recursive=True)

    for path in candidates:
        if subject_id in os.path.basename(path):
            return path

    return None

def batch_process(data_dir, atlas_path, output_dir=None, mask_path=None,
                  exclude_runs=None, exclude_subjects=None,
                  transforms_dir=None, transform_suffix="anat_to_atlas_warp.nii.gz"):
    """
    Recursively finds all 4D fMRI files matching the pattern and extracts time series.
    
    Parameters:
    - data_dir: Root directory containing subject folders.
    - atlas_path: Path to the ROI Atlas NIfTI file.
    - output_dir: (Optional) Directory to save all output CSVs.
    - mask_path: (Optional) Path to a common binary mask file.
    - exclude_runs: (Optional) List of run identifiers to exclude.
    - exclude_subjects: (Optional) List of subject identifiers to exclude.
    - transforms_dir: (Optional) Root directory containing transform files.
    - transform_suffix: (Optional) Suffix of the transform file to search for.
    """
    
    # The pattern based on user description:
    # conf_correction* -> confound_correction_datasink -> cleaned_timeseries -> *"sub-name"*"ses-0#"* -> "sub-name"*
    search_pattern = "**/*cleaned.nii.gz"
    
    print(f"Searching for files in: {data_dir}")
    print(f"Pattern: {search_pattern} (recursive)")
    
    files = glob.glob(os.path.join(data_dir, search_pattern), recursive=True)
    
    if not files:
        print("No files found matching the pattern!")
        return

    print(f"Found {len(files)} files to process.")
    
    # Filter out excluded runs and subjects
    if exclude_runs or exclude_subjects:
        original_count = len(files)
        filtered_files = []
        
        for file_path in files:
            # Check if file should be excluded based on run identifiers
            if exclude_runs:
                exclude_file = False
                for run_id in exclude_runs:
                    pattern = re.escape(run_id) + r'(?:[^a-zA-Z0-9]|$)'
                    if re.search(pattern, file_path):
                        print(f"  Excluding (run): {file_path}")
                        exclude_file = True
                        break
                if exclude_file:
                    continue
            
            # Check if file should be excluded based on subject identifiers
            if exclude_subjects:
                exclude_file = False
                for subject_id in exclude_subjects:
                    pattern = re.escape(subject_id) + r'(?:[^a-zA-Z0-9]|$)'
                    if re.search(pattern, file_path):
                        print(f"  Excluding (subject): {file_path}")
                        exclude_file = True
                        break
                if exclude_file:
                    continue
            
            filtered_files.append(file_path)
        
        files = filtered_files
        print(f"After filtering: {len(files)} files remaining ({original_count - len(files)} excluded).")
    
    if not files:
        print("No files remaining after exclusion filters!")
        return
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Outputs will be saved to: {output_dir}")
    else:
        print("Outputs will be saved alongside input files.")

    if transforms_dir:
        print(f"Transforms Directory: {transforms_dir}")
        print(f"Transform Suffix: {transform_suffix}")

    success_count = 0
    error_count = 0

    for i, input_path in enumerate(files):
        print(f"\n[{i+1}/{len(files)}] Processing: {input_path}")
        
        try:
            # Determine output filename
            filename = os.path.basename(input_path)
            base_name = filename.replace(".nii.gz", "").replace(".nii", "")
            csv_name = f"{base_name}_timeseries.csv"
            
            if output_dir:
                output_path = os.path.join(output_dir, csv_name)
            else:
                parent_dir = os.path.dirname(input_path)
                output_path = os.path.join(parent_dir, csv_name)
            
            if os.path.exists(output_path):
                print(f"  -> Output {output_path} already exists. Skipping.")
                continue

            # Find transform if requested
            transform_path = None
            if transforms_dir:
                # Extract Subject ID
                # We assume standard BIDS-like naming "sub-XXXX"
                match = re.search(r"(sub-[a-zA-Z0-9]+)", filename)
                if match:
                    subject_id = match.group(1)
                    transform_path = find_transform(subject_id, transforms_dir, transform_suffix)
                    if transform_path:
                        print(f"  -> Found Transform: {transform_path}")
                    else:
                        print(f"  -> WARNING: No transform found for {subject_id} with suffix {transform_suffix}")
                else:
                    print("  -> WARNING: Could not extract subject ID (sub-XXXX) from filename.")

            # Run extraction
            extract_timeseries(input_path, atlas_path, output_path, mask_path, transform_path)
            success_count += 1
            
        except Exception as e:
            print(f"  -> ERROR processing {input_path}: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
            
    print("\n" + "="*30)
    print("Batch Processing Complete")
    print(f"Successfully processed: {success_count}")
    print(f"Errors: {error_count}")
    print("="*30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch extract time series from multiple fMRI files.")
    
    parser.add_argument("data_dir", help="Root directory containing subject folders.")
    parser.add_argument("atlas_path", help="Path to the ROI Atlas NIfTI file.")
    parser.add_argument("--mask", help="(Optional) Path to a common binary mask file.", default=None)
    parser.add_argument("--output_dir", help="(Optional) Directory to save all output CSVs. If omitted, saves next to input files.", default=None)
    parser.add_argument("--exclude-runs", help="(Optional) Comma-separated list of run identifiers to exclude (e.g., 'run-01,run-03')", default=None)
    parser.add_argument("--exclude-subjects", help="(Optional) Comma-separated list of subject identifiers to exclude (e.g., 'sub-01,sub-05')", default=None)
    parser.add_argument("--transforms_dir", help="(Optional) Root directory containing transform files.", default=None)
    parser.add_argument("--transform_suffix", help="(Optional) Suffix of the transform file to search for (default: 'anat_to_atlas_warp.nii.gz').", default="anat_to_atlas_warp.nii.gz")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data_dir):
        print(f"Error: Data directory {args.data_dir} not found.")
        sys.exit(1)
        
    if not os.path.exists(args.atlas_path):
        print(f"Error: Atlas file {args.atlas_path} not found.")
        sys.exit(1)

    if args.transforms_dir and not os.path.exists(args.transforms_dir):
        print(f"Error: Transforms directory {args.transforms_dir} not found.")
        sys.exit(1)
    
    # Parse exclusion lists
    exclude_runs = None
    if args.exclude_runs:
        exclude_runs = [run.strip() for run in args.exclude_runs.split(',')]
    
    exclude_subjects = None
    if args.exclude_subjects:
        exclude_subjects = [sub.strip() for sub in args.exclude_subjects.split(',')]

    batch_process(args.data_dir, args.atlas_path, args.output_dir, args.mask,
                  exclude_runs, exclude_subjects, args.transforms_dir, args.transform_suffix)
