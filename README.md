# fMRI Time Series Extraction Tool

This tool extracts mean BOLD signal time series from 4D fMRI NIfTI files using a 3D ROI Atlas. It is designed to prepare data for further analysis, such as calculating spatial and temporal autocorrelation.

## Features

*   **Robust Extraction**: Uses `nilearn` to accurately extract mean signals from regions defined in an atlas.
*   **Flexible Inputs**: Accepts standard NIfTI files (`.nii` or `.nii.gz`).
*   **Optional Masking**: Supports an additional binary mask to restrict analysis to specific brain areas.
*   **Standard Output**: Generates a CSV file where **Rows = Time Points** and **Columns = Region Labels**.

## Prerequisites

*   Python 3.8+
*   The following NIfTI files:
    *   **4D Time Series**: The cleaned fMRI data (e.g., `cleaned_bold.nii.gz`).
    *   **3D Atlas**: The ROI labels (e.g., `atlas.nii.gz`).
    *   (Optional) **3D Mask**: A binary mask (e.g., `brain_mask.nii.gz`).

## Installation

1.  **Clone or Download** this repository.
2.  **Set up the environment**:
    You can use the provided helper script to create a virtual environment and install dependencies:

    ```bash
    ./setup_env.sh
    source venv/bin/activate
    ```

    *Alternatively, install manually:*
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Command Line

Run the script from your terminal:

```bash
python extract_timeseries.py <input_4d> <atlas_3d> <output_csv> [--mask <mask_file>]
```

**Examples:**

1.  **Basic Extraction:**
    ```bash
    python extract_timeseries.py data/rabies_cleaned.nii.gz data/roi_atlas.nii.gz results/timeseries.csv
    ```

2.  **With a Mask:**
    ```bash
    python extract_timeseries.py data/rabies_cleaned.nii.gz data/roi_atlas.nii.gz results/timeseries.csv --mask data/brain_mask.nii.gz
    ```

### Batch Processing

If you have multiple subjects organized in subfolders, you can use `batch_extract.py` to process them all at once.

```bash
python batch_extract.py <root_data_dir> <atlas_path> [--output_dir <results_folder>]
```

**Example:**

Assume your data structure is:
```
data/
  sub-01/
     ...cleaned.nii.gz
  sub-02/
     ...cleaned.nii.gz
```

Run:
```bash
python batch_extract.py data/ my_atlas.nii.gz
```

This will automatically find all `*cleaned.nii.gz` files and create a corresponding `_timeseries.csv` file in the same folder.

**Options:**
*   `--mask`: Use a common binary mask for all subjects.
*   `--output_dir`: Save all resulting CSVs into a single folder instead of next to the original files.

### Using in VS Code

1.  **Open the Folder**: Open this repository folder in VS Code.
2.  **Select Interpreter**:
    *   Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac).
    *   Type "Python: Select Interpreter".
    *   Select the one inside the `venv` folder (e.g., `venv/bin/python`).
3.  **Run the Script**:
    *   Open `extract_timeseries.py`.
    *   Open the Integrated Terminal (`Ctrl+` `).
    *   Type the command (e.g., `python extract_timeseries.py ...`) and hit Enter.

## Output Format

The output is a CSV file:

| region_1 | region_2 | ... | region_N |
| :--- | :--- | :--- | :--- |
| 0.123 | -0.045 | ... | 0.881 |
| 0.110 | -0.021 | ... | 0.870 |
| ... | ... | ... | ... |

*   **Rows**: Time points (TRs).
*   **Columns**: Region labels from the atlas (usually integers).
