import pandas as pd
import re
import os
import glob
import numpy as np
from matplotlib import pyplot as plt


def update_tsv(subj, search_dir,task_tag):
    """
    Searches for all TSV files matching the given `subj` identifier, processes each one by removing specific rows,
    and saves the updated file, overwriting the original.

    - The script searches for the files based on the `subj` identifier.
    - It processes all matching files and removes rows where `trial_type` is "BAD boundary" or "EDGE boundary".
    - Each modified TSV file replaces the original file.

    Parameters:
    - subj: str, the subject identifier (e.g., 'D53').
    - search_dir: str, directory to search for the files (default is the current directory).

    Raises:
    - ValueError: If no files or more than one matching file are found for a `subj` and those files have issues.
    """
    # Construct the pattern to match the filenames based on `subj`
    task_tag_clean = task_tag.replace('_', '')
    pattern = f"sub-{subj}_task-{task_tag_clean}_acq-.+?_run-.+?_desc-clean_events.tsv"

    # Search for all files in the specified directory that match the pattern
    files = [f for f in os.listdir(search_dir) if re.match(pattern, f)]

    if not files:
        raise ValueError(f"No files matching the pattern found for subj {subj}.")

    # If matching files are found, process each one
    for file in files:
        input_file = os.path.join(search_dir, file)

        # Read the TSV file
        df = pd.read_csv(input_file, sep="\t")

        # Remove rows with trial_type "BAD boundary" or "EDGE boundary"
        df_filtered = df[~df['trial_type'].isin(["BAD boundary", "EDGE boundary", "BAD_ACQ_SKIP"])]

        # Overwrite the original file with the filtered data
        df_filtered.to_csv(input_file, sep="\t", index=False)
        print(f"Processed and replaced the original file: {input_file}")

def detect_outlier(subj, search_dir, task_tag):
    """
    Detect outliers in files matching a specific pattern for a given subject.
    
    Args:
        task_tag: tag for task
        subj (str): Subject identifier.
        search_dir (str): Directory to search for the files. Defaults to the current directory.
    
    Returns:
        int: 1 if any file contains 'outlier' in the 'status_description' column, 0 otherwise.
    """
    # Construct the pattern to match the filenames based on `subj`
    task_tag_clean = task_tag.replace('_', '')
    pattern = f"sub-{subj}_task-{task_tag_clean}_acq-.+?_run-.+?_desc-clean_channels.tsv"
    
    # Search for all files in the specified directory that match the pattern
    files = [f for f in os.listdir(search_dir) if re.match(pattern, f)]
    
    if not files:
        raise ValueError(f"No files matching the pattern found for subj {subj}.")
    
    # Check each file for 'outlier' in the 'status_description' column
    for file in files:
        file_path = os.path.join(search_dir, file)
        # Read the file assuming it's a tab-separated values (TSV) file
        data = pd.read_csv(file_path, sep='\t')
        
        # If 'status_description' column contains 'outlier', return 1
        if 'status_description' in data.columns and 'outlier' in data['status_description'].values:
            return 1
    
    return 0

def load_eeg_chs(subject):
        
    """
    Load the eeg channels for a specific subject.

    Args:
        subject (str): Subject identifier.

    Returns:
        list: List of eeg channel names.
    """
    eeg_chs_loc=os.path.join('data','eeg_chans',f'{subject}_eeg_chans.csv')
    df = pd.read_csv(eeg_chs_loc, header=None)
    df.columns = ['eeg_chs']
    eeg_chs = df['eeg_chs'].tolist()
    return eeg_chs

def load_muscle_chs(subject):
        
    """
    Load the muscle channels for a specific subject.

    Args:
        subject (str): Subject identifier.

    Returns:
        list: List of muscle channel names.
    """
    muscle_chs_loc=os.path.join('data','muscle_chans',f'{subject}_muscle_chans.csv')
    df = pd.read_csv(muscle_chs_loc, header=None)
    df.columns = ['muscle_chs']
    muscle_chs = df['muscle_chs'].tolist()
    return muscle_chs

def update_muscle_chs(subj, search_dir,task_tag):
    """
    Update the status and status_description of specified electrodes in the subject's channel files
    based on the muscle channels loaded for the subject.

    Args:
        subj (str): Subject identifier.
        search_dir (str): Directory to search for the files. Defaults to the current directory.

    Returns:
        None
    """

    # Load muscle channels for the subject
    electrode_list = load_muscle_chs(subj)

    # Construct the pattern to match the filenames based on `subj`
    task_tag_clean = task_tag.replace('_', '')
    pattern = f"sub-{subj}_task-{task_tag_clean}_acq-.+?_run-.+?_desc-clean_channels.tsv"

    # Search for all files in the specified directory that match the pattern
    files = [f for f in os.listdir(search_dir) if re.match(pattern, f)]

    if not files:
        raise ValueError(f"No files matching the pattern found for subj {subj}.")

    for file in files:
        file_path = os.path.join(search_dir, file)
        # Read the file assuming it's a tab-separated values (TSV) file
        data = pd.read_csv(file_path, sep='\t')

        # Check and update the status and status_description for the electrodes
        for electrode in electrode_list:
            if electrode in data['name'].values:
                idx = data[data['name'] == electrode].index[0]
                if data.at[idx, 'status'] != 'bad' or data.at[idx, 'status_description'] != 'muscle':
                    data.at[idx, 'status'] = 'bad'
                    data.at[idx, 'status_description'] = 'muscle'

        # Save the updated file back to disk
        data.to_csv(file_path, sep='\t', index=False)

    print(f"Updated files for subject {subj}: {files}")

def plot_save_gammamask(mask,epoch_mask,subj_gamma_dir,fname):
    fig, ax = plt.subplots()
    ax.imshow(mask, cmap='Reds')
    channel_names=epoch_mask.ch_names[::5]
    ax.set_yticks(range(0,len(channel_names)*5,5))
    ax.set_yticklabels(channel_names)
    time_stamps=epoch_mask.times[::20]
    ax.set_xticks(range(0,len(time_stamps)*20,20))
    ax.set_xticklabels(time_stamps)
    try:
        zero_time_index = np.where(epoch_mask.times == 0)[0][0]
        ax.axvline(x=zero_time_index, color='black', linestyle='--', linewidth=1)
    except Exception as e:
        print('no zero time found')
    fig.savefig(os.path.join(subj_gamma_dir,fname), dpi=300)
    plt.close(fig)