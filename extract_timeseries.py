import argparse
import pandas as pd
import numpy as np
import nibabel as nib
from nilearn.maskers import NiftiLabelsMasker
import sys
import os

def extract_timeseries(input_4d, atlas_3d, output_csv, mask_img=None):
    """
    Extracts time series from a 4D NIfTI file using a 3D Atlas.
    
    Parameters:
    - input_4d: Path to the 4D fMRI NIfTI file.
    - atlas_3d: Path to the 3D Atlas NIfTI file.
    - output_csv: Path to save the resulting CSV.
    - mask_img: (Optional) Path to a binary mask NIfTI file.
    """
    
    print(f"Loading Atlas: {atlas_3d}")
    print(f"Loading 4D Data: {input_4d}")
    if mask_img:
        print(f"Using Mask: {mask_img}")
    else:
        print("No mask provided. Using Atlas definition directly.")

    # Initialize the masker
    # standardize=False: We assume input is already cleaned/preprocessed as per user description.
    # detrend=False: We assume input is already cleaned.
    masker = NiftiLabelsMasker(labels_img=atlas_3d, mask_img=mask_img, standardize=False)
    
    # Extract signals
    # Output shape: (n_timepoints, n_regions)
    print("Extracting signals...")
    try:
        time_series = masker.fit_transform(input_4d)
    except Exception as e:
        print(f"Error during extraction: {e}")
        sys.exit(1)
        
    # Get region labels
    # masker.labels_ contains the labels that nilearn found in the atlas.
    # Note: NiftiLabelsMasker drops regions that are empty (no signal in input_4d),
    # so we need to check if any are missing and pad them.
    extracted_labels = masker.labels_
    print(f"Extracted signals for {time_series.shape[1]} regions.")
    
    # NiftiLabelsMasker includes the background label (usually 0) in .labels_ 
    # if it's in the atlas image, even if it ignores it during extraction.
    # We generally want to ignore 0.
    if extracted_labels[0] == 0:
        extracted_labels = extracted_labels[1:]
        
    # Double check alignment
    if len(extracted_labels) != time_series.shape[1]:
        # Sometimes nilearn drops regions entirely if they are empty in the data
        print(f"Warning: Extracted {time_series.shape[1]} signals but found {len(extracted_labels)} labels.")
        # We need to trust the data shape. The 'extracted_labels' usually matches the *Atlas* content.
        # But if regions were dropped due to being empty, we need to find out WHICH ones.
        pass

    # To Ensure we have ALL regions from the atlas, we should inspect the atlas directly 
    # or rely on extracted_labels being the "Truth" from the atlas file.
    
    # 1. Create DataFrame with the labels nilearn *did* extract
    # We assume 'extracted_labels' are the ones associated with the columns of 'time_series'
    # IF nilearn dropped regions, 'extracted_labels' might still contain ALL atlas labels
    # while 'time_series' is smaller.
    
    # Strategy: 
    # If (len(extracted_labels) > time_series.shape[1]), it means nilearn kept the labels list full
    # but dropped columns. We need to find which are missing.
    # HOWEVER, NiftiLabelsMasker behavior varies. 
    # The most robust way: Load the Atlas manually to get the "Ground Truth" list of all regions.
    
    atlas_img = nib.load(atlas_3d)
    atlas_data = atlas_img.get_fdata()
    all_labels = sorted(list(np.unique(atlas_data.astype(int))))
    if all_labels[0] == 0:
        all_labels = all_labels[1:] # Remove background
    
    print(f"Total regions in Atlas file: {len(all_labels)}")
    
    # Check if we are missing any
    if time_series.shape[1] < len(all_labels):
        print(f"WARNING: Extracted {time_series.shape[1]} regions, but Atlas has {len(all_labels)}.")
        print("Padding missing regions with Zeros...")
        
        # We need to map the columns we HAVE to the labels we EXPECT.
        # Unfortunately, NiftiLabelsMasker doesn't easily tell us "Column 1 is Region 5" if it silently dropped Region 2.
        # BUT: masker.labels_ *usually* contains the list of labels that correspond to the columns... 
        # WAIT: The documentation says "labels_: the labels of the regions extracted".
        # So if a region is dropped, it should be missing from masker.labels_.
        
        # Let's verify that assumption.
        current_labels = list(extracted_labels)
        
        # If lengths mismatch (labels vs columns), we have a deeper issue, but usually they match.
        if len(current_labels) != time_series.shape[1]:
             # Fallback: if nilearn kept the background in the list but not the data
             if len(current_labels) == time_series.shape[1] + 1:
                 current_labels = current_labels[1:]
        
        # Create the initial DF with what we have
        df = pd.DataFrame(time_series, columns=current_labels)
        
        # Add missing columns
        for label in all_labels:
            if label not in df.columns:
                print(f"  -> Region {label} missing. Filling with 0.")
                df[label] = 0.0
                
        # Sort columns to match Atlas order (1, 2, 3...)
        df = df.reindex(columns=all_labels)
        
    else:
        # All good, just creating the DF
        # Handle the mismatch if nilearn included background in labels list
        current_labels = list(extracted_labels)
        if len(current_labels) == time_series.shape[1] + 1:
             current_labels = current_labels[1:]
             
        df = pd.DataFrame(time_series, columns=current_labels)

    
    # Add a 'TR' (Time Repetition) column for clarity? 
    # Usually stats packages just want the matrix. 
    # The user asked for: "one of the axes ... should be the regions ... other will be their signal values"
    # Current format: Index is time, Columns are regions.
    
    # Save to CSV
    print(f"Saving to {output_csv}...")
    df.to_csv(output_csv, index=False) # index=False means we don't save the row numbers 0..N explicitly as a column, unless desired.
    # But usually for time series, the row order implies time.
    
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract mean time series from 4D fMRI NIfTI using an Atlas.")
    
    parser.add_argument("input_4d", help="Path to the cleaned 4D fMRI NIfTI file (.nii or .nii.gz)")
    parser.add_argument("atlas_3d", help="Path to the ROI Atlas NIfTI file (.nii or .nii.gz)")
    parser.add_argument("output_csv", help="Path to save the output CSV file")
    parser.add_argument("--mask", help="(Optional) Path to a binary mask NIfTI file", default=None)
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_4d):
        print(f"Error: Input file {args.input_4d} not found.")
        sys.exit(1)
        
    if not os.path.exists(args.atlas_3d):
        print(f"Error: Atlas file {args.atlas_3d} not found.")
        sys.exit(1)
        
    if args.mask and not os.path.exists(args.mask):
        print(f"Error: Mask file {args.mask} not found.")
        sys.exit(1)

    extract_timeseries(args.input_4d, args.atlas_3d, args.output_csv, args.mask)
