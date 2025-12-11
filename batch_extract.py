import os
import argparse
import glob
import sys
from extract_timeseries import extract_timeseries

def batch_process(data_dir, atlas_path, output_dir=None, mask_path=None):
    """
    Recursively finds all 4D fMRI files matching the pattern and extracts time series.
    """
    
    # The pattern based on user description:
    # conf_correction* -> confound_correction_datasink -> cleaned_timeseries -> *"sub-name"*"ses-0#"* -> "sub-name"*
    # Since the structure is deep and variable, using a recursive glob with the filename suffix is the most robust approach.
    # We look for any file ending in 'cleaned.nii.gz' anywhere under the data_dir.
    search_pattern = "**/*cleaned.nii.gz"
    
    print(f"Searching for files in: {data_dir}")
    print(f"Pattern: {search_pattern} (recursive)")
    
    # recursive=True allows ** to match subdirectories of any depth
    files = glob.glob(os.path.join(data_dir, search_pattern), recursive=True)
    
    if not files:
        print("No files found matching the pattern!")
        return

    print(f"Found {len(files)} files to process.")
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Outputs will be saved to: {output_dir}")
    else:
        print("Outputs will be saved alongside input files.")

    success_count = 0
    error_count = 0

    for i, input_path in enumerate(files):
        print(f"\n[{i+1}/{len(files)}] Processing: {input_path}")
        
        try:
            # Determine output filename
            filename = os.path.basename(input_path)
            # Replace extension
            base_name = filename.replace(".nii.gz", "").replace(".nii", "")
            csv_name = f"{base_name}_timeseries.csv"
            
            if output_dir:
                output_path = os.path.join(output_dir, csv_name)
            else:
                # Save in the same folder as the input
                parent_dir = os.path.dirname(input_path)
                output_path = os.path.join(parent_dir, csv_name)
            
            # Check if output already exists to avoid re-doing work (optional but nice)
            if os.path.exists(output_path):
                print(f"  -> Output {output_path} already exists. Skipping.")
                continue

            # Run extraction
            extract_timeseries(input_path, atlas_path, output_path, mask_path)
            success_count += 1
            
        except Exception as e:
            print(f"  -> ERROR processing {input_path}: {e}")
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
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data_dir):
        print(f"Error: Data directory {args.data_dir} not found.")
        sys.exit(1)
        
    if not os.path.exists(args.atlas_path):
        print(f"Error: Atlas file {args.atlas_path} not found.")
        sys.exit(1)

    batch_process(args.data_dir, args.atlas_path, args.output_dir, args.mask)
