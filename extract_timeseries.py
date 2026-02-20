import argparse
import pandas as pd
import numpy as np
import nibabel as nib
from nilearn.image import resample_to_img
from nilearn.maskers import NiftiLabelsMasker
import sys
import os
import subprocess
import tempfile

def align_atlas_to_target(atlas_path, target_path, transform_path=None, output_path=None):
    """
    Aligns the atlas to the target image geometry (resolution, FOV, orientation).

    If a transform_path is provided, it uses 'antsApplyTransforms' with GenericLabel interpolation.
    If no transform_path is provided, it uses nilearn's resample_to_img with nearest neighbor interpolation.

    Parameters:
    - atlas_path: Path to the input atlas NIfTI file.
    - target_path: Path to the reference/target NIfTI file (the time series or a 3D volume from it).
    - transform_path: (Optional) Path to a transform file (e.g., warp or affine).
    - output_path: (Optional) Path to save the aligned atlas. If None, a temporary file is created.

    Returns:
    - Path to the aligned atlas file.
    """

    # If no output path is provided, create a temporary one
    if output_path is None:
        # We use a named temporary file that persists so we can read it later
        # The caller is responsible for cleanup if needed, but for now we'll let the OS handle temp files eventually
        # or just return the path and let the script finish.
        fd, output_path = tempfile.mkstemp(suffix="_aligned_atlas.nii.gz")
        os.close(fd)

    print(f"Aligning Atlas to Target...")
    print(f"  Atlas: {atlas_path}")
    print(f"  Target: {target_path}")
    if transform_path:
        print(f"  Transform: {transform_path}")
        print("  Using ANTs (antsApplyTransforms) with GenericLabel interpolation.")

        # Construct the command
        # antsApplyTransforms -d 3 -i <atlas> -r <target> -t <transform> -o <output> -n GenericLabel
        # Note: If target is 4D, we need a 3D reference.
        # antsApplyTransforms might handle 4D target as reference by taking the first volume,
        # but to be safe, we should extract the first volume of the target if it's 4D.

        # Check if target is 4D
        target_img = nib.load(target_path)
        if len(target_img.shape) == 4:
            print("  Target is 4D. Extracting first volume as reference for registration.")
            ref_vol = target_img.slicer[..., 0]
            fd_ref, ref_path = tempfile.mkstemp(suffix="_ref_vol.nii.gz")
            os.close(fd_ref)
            nib.save(ref_vol, ref_path)
            reference_image = ref_path
        else:
            reference_image = target_path

        cmd = [
            "antsApplyTransforms",
            "-d", "3",
            "-i", atlas_path,
            "-r", reference_image,
            "-t", transform_path,
            "-o", output_path,
            "-n", "GenericLabel"
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"  -> Aligned atlas saved to: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error running ANTs: {e}")
            print(f"Standard Output: {e.stdout.decode()}")
            print(f"Standard Error: {e.stderr.decode()}")
            # Clean up temp reference if created
            if len(target_img.shape) == 4 and os.path.exists(reference_image):
                os.remove(reference_image)
            sys.exit(1)

        # Clean up temp reference if created
        if len(target_img.shape) == 4 and os.path.exists(reference_image):
            os.remove(reference_image)

    else:
        print("  No transform provided. Using Nilearn resample_to_img (Nearest Neighbor).")
        # Load images
        atlas_img = nib.load(atlas_path)
        target_img = nib.load(target_path)

        # If target is 4D, use the first volume as reference
        if len(target_img.shape) == 4:
            target_img = target_img.slicer[..., 0]

        # Resample
        # interpolation='nearest' is equivalent to GenericLabel for labels
        resampled_atlas = resample_to_img(
            source_img=atlas_img,
            target_img=target_img,
            interpolation='nearest'
        )

        # Save
        nib.save(resampled_atlas, output_path)
        print(f"  -> Resampled atlas saved to: {output_path}")

    return output_path


def extract_timeseries(input_4d, atlas_3d, output_csv, mask_img=None, transform_path=None):
    """
    Extracts time series from a 4D NIfTI file using a 3D Atlas.
    
    Parameters:
    - input_4d: Path to the 4D fMRI NIfTI file.
    - atlas_3d: Path to the 3D Atlas NIfTI file.
    - output_csv: Path to save the resulting CSV.
    - mask_img: (Optional) Path to a binary mask NIfTI file.
    - transform_path: (Optional) Path to a transform file to apply to the atlas.
    """
    
    print(f"Loading 4D Data: {input_4d}")

    # 1. Align Atlas to Data (using transform or just resampling)
    # We always align/resample to ensure the atlas matches the EPI geometry perfectly.
    # This solves the issue of resolution mismatch creating empty regions.
    aligned_atlas_path = align_atlas_to_target(atlas_3d, input_4d, transform_path)

    print(f"Using Aligned Atlas: {aligned_atlas_path}")
    if mask_img:
        print(f"Using Mask: {mask_img}")
        # Note: If mask is provided, it should ideally also be in the same space/geometry.
        # If not, nilearn might handle it, or we might need to resample it too.
        # For now, we assume the mask is correct (e.g., brain mask from the same pipeline).
    else:
        print("No mask provided. Using Atlas definition directly.")

    # Initialize the masker
    # standardize=False: We assume input is already cleaned/preprocessed.
    # detrend=False: We assume input is already cleaned.
    masker = NiftiLabelsMasker(labels_img=aligned_atlas_path, mask_img=mask_img, standardize=False)
    
    # Extract signals
    print("Extracting signals...")
    try:
        time_series = masker.fit_transform(input_4d)
    except Exception as e:
        print(f"Error during extraction: {e}")
        # Clean up temp file
        if os.path.exists(aligned_atlas_path) and aligned_atlas_path != atlas_3d:
             os.remove(aligned_atlas_path)
        sys.exit(1)
        
    # Get region labels from the ALIGNED atlas
    extracted_labels = masker.labels_
    print(f"Extracted signals for {time_series.shape[1]} regions.")
    
    if extracted_labels[0] == 0:
        extracted_labels = extracted_labels[1:]
        
    # Logic to handle missing regions (same as before)
    # Load the ORIGINAL atlas to get the "Ground Truth" list of all regions.
    # This ensures consistency across subjects even if some regions are lost during alignment.
    original_atlas_img = nib.load(atlas_3d)
    original_atlas_data = original_atlas_img.get_fdata()
    all_labels = sorted(list(np.unique(original_atlas_data.astype(int))))
    if all_labels[0] == 0:
        all_labels = all_labels[1:]
    
    print(f"Total regions in Original Atlas: {len(all_labels)}")
    
    if time_series.shape[1] < len(all_labels):
        print(f"WARNING: Extracted {time_series.shape[1]} regions, but Atlas has {len(all_labels)}.")
        print("Padding missing regions with Zeros...")
        
        current_labels = list(extracted_labels)
        if len(current_labels) == time_series.shape[1] + 1:
             current_labels = current_labels[1:]
        
        df = pd.DataFrame(time_series, columns=current_labels)
        
        for label in all_labels:
            if label not in df.columns:
                print(f"  -> Region {label} missing. Filling with 0.")
                df[label] = 0.0
                
        df = df.reindex(columns=all_labels)
    else:
        current_labels = list(extracted_labels)
        if len(current_labels) == time_series.shape[1] + 1:
             current_labels = current_labels[1:]
        df = pd.DataFrame(time_series, columns=current_labels)

    # Save to CSV
    print(f"Saving to {output_csv}...")
    df.to_csv(output_csv, index=False)

    # Clean up temporary aligned atlas
    if os.path.exists(aligned_atlas_path) and aligned_atlas_path != atlas_3d:
        print(f"Removing temporary aligned atlas: {aligned_atlas_path}")
        os.remove(aligned_atlas_path)
    
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract mean time series from 4D fMRI NIfTI using an Atlas.")
    
    parser.add_argument("input_4d", help="Path to the cleaned 4D fMRI NIfTI file (.nii or .nii.gz)")
    parser.add_argument("atlas_3d", help="Path to the ROI Atlas NIfTI file (.nii or .nii.gz)")
    parser.add_argument("output_csv", help="Path to save the output CSV file")
    parser.add_argument("--mask", help="(Optional) Path to a binary mask NIfTI file", default=None)
    parser.add_argument("--transform", help="(Optional) Path to a transform file (warp/affine) to align atlas to data.", default=None)
    
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

    if args.transform and not os.path.exists(args.transform):
        print(f"Error: Transform file {args.transform} not found.")
        sys.exit(1)

    extract_timeseries(args.input_4d, args.atlas_3d, args.output_csv, args.mask, args.transform)
