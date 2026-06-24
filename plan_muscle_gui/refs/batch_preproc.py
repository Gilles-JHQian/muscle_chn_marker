"""
    Batch preprocessing scripts for lexical delay task, Lexical nodelay task, and RetroCue task.
    Including: line noise filtering, outlier channels removal, and wavelet.
    Parameters are equal to Sentence Rep processing code unless a change is necessary (NEEDED TO BE RE-CHECKED!):
    https://github.com/coganlab/SentenceRep_analysis
    From Baishen Liang.
"""
# %% Preparation:

import os
import sys
import mne
import datetime
import numpy as np
from ieeg.navigate import crop_empty_data, channel_outlier_marker, trial_ieeg, outliers_to_nan
from ieeg.mt_filter import line_filter
from ieeg.io import get_data, raw_from_layout, save_derivative, update
from ieeg.calc import stats, scaling
from ieeg.calc.scaling import rescale
from ieeg.viz.ensemble import chan_grid
from ieeg.timefreq.utils import crop_pad, wavelet_scaleogram
from ieeg.timefreq import gamma, utils
from ieeg.viz.parula import parula_map
from utils.batch import update_tsv, detect_outlier, load_eeg_chs, update_muscle_chs, plot_save_gammamask
from matplotlib import pyplot as plt

# %% Subj list
subject_processing_dict_org = {
    "D0023": "gamma",
    "D0024": "gamma",
    "D0026": "gamma",
    "D0027": "gamma",
    "D0028": "gamma",
    "D0029": "gamma",
    "D0032": "gamma",
    "D0035": "gamma",
    "D0038": "gamma",
    "D0042": "gamma",
    "D0044": "gamma",
    "D0047": "gamma",
    "D0053": "gamma",
    "D0054": "gamma",
    "D0055": "gamma",
    "D0057": "gamma",
    "D0059": "gamma",
    "D0063": "gamma",
    "D0065": "gamma",
    "D0066": "gamma",
    "D0068": "gamma",
    "D0069": "gamma",
    "D0070": "gamma",
    "D0071": "gamma",
    "D0077": "gamma",
    "D0079": "gamma",
    "D0080": "gamma",
    "D0081": "gamma",
    "D0084": "gamma",
    "D0086": "gamma",
    "D0090": "gamma",
    "D0092": "gamma",
    "D0094": "gamma",
    "D0096": "gamma",
    "D0100": "gamma",
    "D0101": "gamma",
    "D0102": "gamma",
    "D0103": "gamma",
    "D0107": "gamma",
    "D0115": "gamma",
    "D0117": "gamma",
    "D0127": "gamma",
    "D0128": "gamma",
    "D0129": "gamma",
    "D0132": "gamma",
    "D0135": "gamma",
    "D0137": "gamma",
    "D0138": "gamma",
    "D0139": "gamma",
    "D0140": "gamma",
    "D0143": "gamma"
}

# "D0100": "linernoise/outlierchs/wavelet/multitaper/gamma"
# %% define task
Task_Tag="LexicalDecRepDelay"
#Task_Tag="LexicalDecRepNoDelay"
# Task_Tag="RetroCue"
BIDS_Tag=f"BIDS-1.0_{Task_Tag}"

# %% check if currently running a slurm job
HOME = os.path.expanduser("~")
if 'SLURM_ARRAY_TASK_ID' in os.environ.keys():
    LAB_root = os.path.join(HOME, "workspace")
    save_dir=os.path.join(HOME,"workspace", "Baishen_Figs",Task_Tag)
    if not os.path.exists(os.path.join(save_dir)):
        try:
            os.mkdir(os.path.join(save_dir))
        except Exception as e:
            print('skip') 
    subj_No = int(os.environ['SLURM_ARRAY_TASK_ID'])
    subj = f"D{subj_No:04}"
    if subj in subject_processing_dict_org:
        subject_processing_dict = {subj: subject_processing_dict_org[subj]}
    else:
        raise KeyError(f"Subject '{subj}' not found in the original dictionary.")
else:  # if not then set box directory
    LAB_root = os.path.join(HOME, "Box", "CoganLab")
    if Task_Tag != "RetroCue":
        save_dir=os.path.join(HOME, "Box", "CoganLab", "D_Data",Task_Tag,"Baishen_Figs")
    else:
        save_dir=os.path.join(HOME, "Box", "CoganLab", "D_Data","Retro_Cue","Baishen_Figs")
    if not os.path.exists(os.path.join(save_dir)):
        os.mkdir(os.path.join(save_dir))
    subject_processing_dict = subject_processing_dict_org


bids_root = os.path.join(LAB_root,BIDS_Tag,'BIDS')

# %% Log
current_time = datetime.datetime.now().strftime('%Y-%m-%d')
log_file_path = os.path.join('data', 'logs', f'batch_preproc_{current_time}')
if not os.path.exists(log_file_path):
    os.mkdir(log_file_path)


# %% Loop
for subject, processing_type in subject_processing_dict.items():

    ## %% Line Noise Filtering
    if "linernoise" in processing_type:

        print('=========================\n')
        print(f'Line Noise Filtering {subject}\n')
        print('=========================\n')

        # make a subject log file or load the existing file
        log_file = open(os.path.join(log_file_path,f'{subject}.txt'), 'a')

        try:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Executing line noise filter\n")

            # load BIDS raw data
            layout = get_data(Task_Tag, root=LAB_root)
            raw = raw_from_layout(layout, subject=subject, preload=True, extension='.edf')

            # drop eeg and marker channels
            eeg_electrode_list = load_eeg_chs(subject)
            eeg_electrode_list = [item for item in eeg_electrode_list if isinstance(item, str)]
            if Task_Tag == "LexicalDecRepNoDelay":
                # This part is temporary. It aims at solving a problem that in BIDS coding some patients had the trigger channel named "" in channel.tsv, which causes the problem of dropping all the channels when executing raw.drop_channels. The real trigger channel name should be "Trigger", and it is confirmed by checking the original data and the events.tsv. So we add "Trigger" to the drop channel list for these patients. After we confirm that all the patients have the correct trigger channel name in channel.tsv, we can remove this part.
                # But the ultimate solution should be fixing the channel.tsv in BIDS coding instead of adding this temporary solution in the code, which may cause confusion and potential problems in the future. So please check the channel.tsv for these patients and fix the trigger channel name if it is wrong.
                if subject!='D0103' and subject!='D0121' and subject!='D0128' and subject!='D0133' and subject!='D0134'  and subject!='D0137'  and subject!='D0138'  and subject!='D0139' and subject!='D0140':
                    eeg_electrode_list.append('Trigger')
            elif Task_Tag == "LexicalDecRepDelay":
                if subject!='D0103':
                    eeg_electrode_list.append('Trigger')
            raw.drop_channels(eeg_electrode_list)

            # line noise filtering
            line_filter(raw, mt_bandwidth=10., n_jobs=-1, copy=False, verbose=10,
                        filter_length='700ms', freqs=[60], notch_widths=20)
            line_filter(raw, mt_bandwidth=10., n_jobs=-1, copy=False, verbose=10,
                        filter_length='20s', freqs=[60, 120, 180, 240],
                        notch_widths=20)

            # crop and save data
            if Task_Tag=="LexicalDecRepDelay" and subject=="D0079":
                raw1 = crop_empty_data(raw)
                del raw
                raw = raw1
            if not os.path.exists(os.path.join(bids_root, "derivatives")):
                os.mkdir(os.path.join(bids_root, "derivatives"))
                os.mkdir(os.path.join(bids_root, "derivatives", "clean"))
            elif not os.path.exists(os.path.join(bids_root, "derivatives", "clean")):
                os.mkdir(os.path.join(bids_root, "derivatives", "clean"))
            save_derivative(raw, layout, "clean", True)
            del raw
            del layout

            # remove "bad boundary" in events.tsv
            tsv_loc = os.path.join(LAB_root, BIDS_Tag, 'BIDS', 'derivatives', 'clean', f'sub-{subject}',
                                   'ieeg')
            update_tsv(subject, tsv_loc, Task_Tag)
            log_file.write(f"{datetime.datetime.now()}, {subject}, Line noise filter %%% completed %%% \n")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            lineno = exc_tb.tb_lineno
    
            error_msg = f"Error Type: {exc_type.__name__}, Error: {e}, File: {fname}, Line: {lineno}"
            while exc_tb.tb_next:
                exc_tb = exc_tb.tb_next
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            lineno = exc_tb.tb_lineno
            log_file.write(f"{datetime.datetime.now()}, {subject}, Line noise filter !!! failed with error !!! : {str(e)}\n")
            log_file.write(f"{datetime.datetime.now()}, {subject}, !!! Error !!! : {error_msg}\n")
            log_file.write(f"real error: {fname} line {lineno}\n")
            log_file.close()

    if "outlierchs" in processing_type:

        print('=========================\n')
        print(f'Outlier chs removal {subject}\n')
        print('=========================\n')

        log_file = open(os.path.join(log_file_path,f'{subject}.txt'), 'a')
        try:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Executing outlier chs removal\n")

            ## Mark outlier channels
            layout = get_data(Task_Tag, root=LAB_root)
            raw = raw_from_layout(layout.derivatives['derivatives/clean'], subject=subject, desc='clean', extension='.edf',
                                  preload=True)

            # mark outlier
            derivative_loc = os.path.join(LAB_root, BIDS_Tag,"BIDS","derivatives","clean",f"sub-{subject}","ieeg")
            is_outlier = detect_outlier(subject,derivative_loc,Task_Tag)
            if is_outlier == 1:
                raise ValueError(
                    f"Outlier channels for the {subject} have been removed. Skip outlier channels removal now. If you want to re-do it, mark all the channels in the derivative as good and n/a for status first."
                )
            else:
                raw.info['bads'] = channel_outlier_marker(raw, 3, 2)
                update(raw, layout, "outlier")
                log_file.write(f"{datetime.datetime.now()}, {subject}, Outlier chs removal %%% completed %%% \n")
           
            del raw
            del layout

        except Exception as e:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Outlier chs removal !!! failed with error !!! : {str(e)}\n")
        log_file.close()

    if "wavelet" in processing_type:

        print('=========================\n')
        print(f'Wavelet {subject}\n')
        print('=========================\n')

        ## Wavelet
        reref=True
        log_file = open(os.path.join(log_file_path,f'{subject}.txt'), 'a')
        try:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Executing wavelet\n")

            # load data
            layout = get_data(Task_Tag, root=LAB_root)
            raw1 = raw_from_layout(layout.derivatives['derivatives/clean'], subject=subject, desc='clean', extension='.edf',
                                  preload=False)

            # drop bad channels
            raw = raw1.copy().drop_channels(raw1.info['bads'])
            del raw1
            raw.load_data()

            # ref to average
            ch_type = raw.get_channel_types(only_data_chs=True)[0]
            if reref:
                raw.set_eeg_reference(ref_channels="average", ch_type=ch_type)

            # make direction
            if not os.path.exists(os.path.join(save_dir, subject)):
                os.mkdir(os.path.join(save_dir, subject))
            if not os.path.exists(os.path.join(save_dir, subject, 'wavelet')):
                os.mkdir(os.path.join(save_dir, subject, 'wavelet'))

            # wavelet
            if Task_Tag=="LexicalDecRepDelay":
                wavelet_eventzip=zip(
                    ('Cue/CORRECT', 'Auditory_stim/CORRECT','Go/CORRECT','Resp/CORRECT'),
                    ((-0.5, 3), (-0.5, 3),  (-0.5, 1), (-0.5, 1)),
                    ('Cue', 'Auditory','Go','Resp'))
            elif Task_Tag=="LexicalDecRepNoDelay":
                wavelet_eventzip=zip(
                    ('Cue/Repeat/CORRECT', 'Auditory_stim/Repeat/CORRECT', 'Resp/Repeat/CORRECT'),
                    ((-0.5, 3), (-0.5, 1), (-0.5, 1)),
                    ('Cue', 'Auditory', 'Resp')
                )
            elif Task_Tag=="RetroCue":
                wavelet_eventzip=zip(
                    (['Audio1/REP_BTH/CORRECT','Audio1/REP_1ST/CORRECT','Audio1/REP_2ND/CORRECT','Audio1/REV_BTH/CORRECT'],
                     ['Audio2/REP_BTH/CORRECT', 'Audio2/REP_1ST/CORRECT', 'Audio2/REP_2ND/CORRECT','Audio2/REV_BTH/CORRECT'],
                     ['Retro_Cue/REP_BTH/CORRECT', 'Retro_Cue/REP_1ST/CORRECT', 'Retro_Cue/REP_2ND/CORRECT','Retro_Cue/REV_BTH/CORRECT'],
                     ['Go/REP_BTH/CORRECT', 'Go/REP_1ST/CORRECT', 'Go/REP_2ND/CORRECT','Go/REV_BTH/CORRECT'],
                     ['Resp/REP_BTH/CORRECT', 'Resp/REP_1ST/CORRECT', 'Resp/REP_2ND/CORRECT', 'Resp/REV_BTH/CORRECT']),
                    ((-0.5, 0.7+0.4),(-0.3, 0.7+0.4+1.5), (-0.5, 0.7+1.5), (-0.5, 1), (-0.5, 1)), # Audio1 + Delay, Audio2 + Delay + Delay1, RetroCue + Delay1, Go, Resp
                    ('Auditory1','Auditory2','Cue', 'Go','Resp'))

            for epoch, t, tag in wavelet_eventzip:

                # Get the spectras
                t1 = t[0] - 0.5
                t2 = t[1] + 0.5
                times = (t1, t2)
                trials = trial_ieeg(raw, epoch, times, preload=True)
                outliers_to_nan(trials, outliers=10)

                spectra_wavelet = wavelet_scaleogram(trials, n_jobs=-1, decim=int(
                    raw.info['sfreq'] / 200))  # 1/10 of the timepionts, don't take too long
                crop_pad(spectra_wavelet, "0.5s")  # cut the first and final 0.5s, change to zero

                # Get the baseline
                if Task_Tag == "LexicalDecRepDelay" or Task_Tag == "LexicalDecRepNoDelay":
                    if 'Cue' in epoch:
                        base_wavelet = spectra_wavelet.copy().crop(-0.5, 0)
                        base_wavelet = base_wavelet.average(lambda x: np.nanmean(x, axis=0), copy=True)
                elif Task_Tag=="RetroCue":
                    if 'Audio1' in epoch[0]:
                        base_wavelet = spectra_wavelet.copy().crop(-0.5, 0)
                        base_wavelet = base_wavelet.average(lambda x: np.nanmean(x, axis=0), copy=True)

                # Baseline correction
                spectra_wavelet = spectra_wavelet.average(lambda x: np.nanmean(x, axis=0), copy=True)
                spectra_wavelet = rescale(spectra_wavelet, base_wavelet, copy=True, mode='ratio')
                spectra_wavelet._data = np.log10(spectra_wavelet._data) * 20

                # Save spectras
                filename = os.path.join(save_dir, subject, 'wavelet', f'{tag}-tfr.h5')
                mne.time_frequency.write_tfrs(filename, spectra_wavelet, overwrite=True)

                # Make spectrograms
                chan_grids = chan_grid(spectra_wavelet, size=(20, 10), vlim=(-2, 2), cmap=parula_map)

                # Save spectrograms
                fig_count = 0
                for fig in chan_grids:
                    if not reref:
                        tag = tag + '_noref'
                    figdir = os.path.join(save_dir, subject, 'wavelet', f'{tag}_{fig_count + 1}.jpg')
                    chan_grids[fig_count].savefig(figdir, dpi=300)
                    plt.close(fig)
                    fig_count += 1

                # Clean memory
                del spectra_wavelet, filename, chan_grids, trials

            del base_wavelet, raw, layout
            log_file.write(f"{datetime.datetime.now()}, {subject}, Wavelet  %%% completed %%% \n")

        except Exception as e:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Wavelet  !!! failed with error !!! : {str(e)}\n")

        log_file.close()

    if "multitaper" in processing_type:

        print('=========================\n')
        print(f'Multitaper {subject}\n')
        print('=========================\n')

        reref=True

        log_file = open(os.path.join(log_file_path,f'{subject}.txt'), 'a')
        try:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Executing multitaper\n")    
            ## Multitaper

            # read muscle artifact channels and update
            tsv_loc = os.path.join(LAB_root, BIDS_Tag, 'BIDS', 'derivatives', 'clean', f'sub-{subject}',
                        'ieeg')
            update_muscle_chs(subject, tsv_loc,Task_Tag)
            
            # load data
            layout = get_data(Task_Tag, root=LAB_root)
            raw1 = raw_from_layout(layout.derivatives['derivatives/clean'], subject=subject, desc='clean', extension='.edf',
                                    preload=False)

            # drop bad channels
            raw = raw1.copy().drop_channels(raw1.info['bads'])
            del raw1
            raw.load_data()

            # ref to average
            
            ch_type = raw.get_channel_types(only_data_chs=True)[0]
            if reref:
                raw.set_eeg_reference(ref_channels="average", ch_type=ch_type)

            # make direction
            if not os.path.exists(os.path.join(save_dir, subject)):
                os.mkdir(os.path.join(save_dir, subject))
            if not os.path.exists(os.path.join(save_dir, subject, 'multitaper_4cons')):
                os.mkdir(os.path.join(save_dir, subject, 'multitaper_4cons'))

            # run multitaper
            if Task_Tag=="LexicalDecRepDelay":
                multitap_task_zip=zip(('Repeat', 'Yes_No'), ('Rep', 'YN'))
            elif Task_Tag=="LexicalDecRepNoDelay":
                multitap_task_zip=zip(('Repeat', 'Yes_No',':=:'), ('Rep','YN','Silence'))
            elif Task_Tag == "RetroCue":
                multitap_task_zip=zip(('DRP_BTH', 'REP_1ST', 'REP_2ND', 'REP_BTH', 'REV_BTH'),
                                      ('DRP_BTH', 'REP_1ST', 'REP_2ND', 'REP_BTH', 'REV_BTH'))

            for task, task_Tag_multitap in multitap_task_zip:
                for word, word_Tag in zip(('Word', 'Nonword'), ('wrd', 'nwrd')):
                    if Task_Tag == "LexicalDecRepDelay":
                        multitap_evnt_zip = zip(
                            ('Cue/' + task + '/' + word + '/CORRECT',
                             'Auditory_stim/' + task + '/' + word + '/CORRECT',
                             'Go/' + task + '/' + word + '/CORRECT',
                             'Resp/' + task + '/' + word + '/CORRECT'),
                            ((-0.5, 3), (-0.5, 3), (-0.5, 1), (-0.5, 1)),
                            ('Cue-' + task_Tag_multitap + '-' + word_Tag,
                             'Auditory-' + task_Tag_multitap + '-' + word_Tag,
                             'Go-' + task_Tag_multitap + '-' + word_Tag,
                             'Resp-' + task_Tag_multitap + '-' + word_Tag)
                        )
                    elif Task_Tag == "LexicalDecRepNoDelay":
                        if task == 'Repeat':
                            multitap_evnt_zip = zip(
                                ('Cue/' + task + '/' + word + '/CORRECT',
                                 'Auditory_stim/' + task + '/' + word + '/CORRECT',
                                 'Resp/' + task + '/' + word + '/CORRECT'),
                                ((-0.5, 3), (-0.5, 2), (-0.5, 1)),
                                ('Cue-' + task_Tag_multitap + '-' + word_Tag,
                                 'Auditory-' + task_Tag_multitap + '-' + word_Tag,
                                 'Resp-' + task_Tag_multitap + '-' + word_Tag)
                            )
                        elif task == ':=:' or task == 'Yes_No':
                            multitap_evnt_zip = zip(
                                ('Cue/' + task + '/' + word + '/CORRECT',
                                 'Auditory_stim/' + task + '/' + word + '/CORRECT'),
                                ((-0.5, 3), (-0.5, 2)),
                                ('Cue-' + task_Tag_multitap + '-' + word_Tag,
                                 'Auditory-' + task_Tag_multitap + '-' + word_Tag))
                    elif Task_Tag == "RetroCue" and word_Tag == 'nwrd':
                            break #avoid repeat execution
                    elif Task_Tag == "RetroCue":
                        if task == 'DRP_BTH':
                            multitap_evnt_zip = zip(
                                ('Audio1/' + task + '/CORRECT',
                                 'Audio2/' + task + '/CORRECT',
                                 'Retro_Cue/' + task + '/CORRECT'),
                                ((-0.5, 1.2), (-0.3, 0.7 + 1.5), (-0.5, 0.7 + 1.5)),# Audio1, Audio2 + Delay1, RetroCue + Delay1
                                ('Auditory1', 'Auditory2', 'Cue'))
                        else:
                            multitap_evnt_zip = zip(
                                ('Audio1/' + task + '/CORRECT',
                                 'Audio2/' + task + '/CORRECT',
                                 'Retro_Cue/' + task + '/CORRECT',
                                 'Go/' + task + '/CORRECT',
                                 'Resp/' + task + '/CORRECT'),
                                ((-0.5, 0.7+0.4),(-0.3, 0.7+0.4+1.5), (-0.5, 0.7+1.5), (-0.5, 1), (-0.5, 1)),
                                ('Auditory1', 'Auditory2', 'Cue', 'Go', 'Resp'))

                    from scipy.interpolate import interp1d
                    def chan_grid_psd(psd_data, freqs, ch_names, size=(4, 5), vlim=(0.7, 1.4), save_dir=None, prefix=''):
                        n_chans = len(ch_names)
                        rows, cols = size
                        chans_per_fig = rows * cols
                        n_figs = int(np.ceil(n_chans / chans_per_fig))
                        
                        for i in range(n_figs):
                            fig, axes = plt.subplots(rows, cols, figsize=(20, 12), constrained_layout=True)
                            axes = axes.flatten()
                            
                            start_idx = i * chans_per_fig
                            end_idx = min((i + 1) * chans_per_fig, n_chans)
                            
                            for j, ch_idx in enumerate(range(start_idx, end_idx)):
                                ax = axes[j]
                                ax.plot(freqs, psd_data[ch_idx], color='k', linewidth=1.5)
                                
                                ax.set_title(ch_names[ch_idx], fontsize=10)
                                ax.set_ylim(vlim)
                                ax.set_xlim(freqs[0], freqs[-1])
                                ax.axhline(1, color='r', linestyle='--', linewidth=0.8, alpha=0.5)
                                
                                if j >= (rows - 1) * cols: ax.set_xlabel("Freq (Hz)")
                                if j % cols == 0: ax.set_ylabel("Power Ratio")

                            for k in range(len(range(start_idx, end_idx)), len(axes)):
                                axes[k].axis('off')

                            if save_dir:
                                figdir = os.path.join(save_dir, f'{prefix}_{i + 1}.jpg')
                                fig.savefig(figdir, dpi=300)
                                plt.close(fig)
                            else:
                                plt.show()

                    baseline_data = None 
                    baseline_freqs = None

                    for epoch, t, tag in multitap_evnt_zip:

                        t1 = t[0] - 0.5
                        t2 = t[1] + 0.5
                        times = (t1, t2)
                        trials = trial_ieeg(raw, epoch, times, preload=True)
                        outliers_to_nan(trials, outliers=10)

                        if reref:
                            freq = np.linspace(0.5, 200, num=80)
                            kwargs = dict(average=False, n_jobs=-1, freqs=freq, return_itc=False,
                                        n_cycles=freq / 2, time_bandwidth=4, decim=20)
                            
                            spectra_multitaper = trials.compute_tfr(method="multitaper", **kwargs)
                            crop_pad(spectra_multitaper, "0.5s")

                            if Task_Tag in ["LexicalDecRepDelay", "LexicalDecRepNoDelay"]:
                                if 'Cue' in epoch:
                                    base_temp = spectra_multitaper.copy().crop(-0.5, 0)
                                    baseline_data = base_temp.average(lambda x: np.nanmean(x, axis=0), copy=True)
                                    del base_temp
                            elif Task_Tag == "RetroCue":
                                if 'Audio1' in epoch:
                                    base_temp = spectra_multitaper.copy().crop(-0.5, 0)
                                    baseline_data = base_temp.average(lambda x: np.nanmean(x, axis=0), copy=True)
                                    del base_temp

                            spectra_multitaper = spectra_multitaper.average(lambda x: np.nanmean(x, axis=0), copy=True)
                            
                            if baseline_data is not None:
                                spectra_multitaper = rescale(spectra_multitaper, baseline_data, copy=True, mode='ratio')
                            
                            save_path = os.path.join(save_dir, subject, 'multitaper_4cons')
                            if not os.path.exists(save_path): os.makedirs(save_path)
                            
                            filename = os.path.join(save_path, f'{tag}-tfr.h5')
                            mne.time_frequency.write_tfrs(filename, spectra_multitaper, overwrite=True)

                            chan_grids = chan_grid(spectra_multitaper, size=(20, 10), vlim=(0.7, 1.4), cmap=parula_map)
                            
                            fig_count = 0
                            for fig in chan_grids:
                                figdir = os.path.join(save_path, f'{tag}_{fig_count + 1}.jpg')
                                chan_grids[fig_count].savefig(figdir, dpi=300)
                                plt.close(fig)
                                fig_count += 1
                                
                            del spectra_multitaper, chan_grids

                        else:
                            psd_kwargs = dict(method='multitaper', fmin=0.5, fmax=200, 
                                            bandwidth=4, n_jobs=-1, verbose=False)
                            
                            spectrum_obj = trials.compute_psd(tmin=t[0], tmax=t[1], **psd_kwargs)
                            
                            psd_all = spectrum_obj.get_data()
                            psd_active = psd_all.mean(axis=0)
                            freqs_active = spectrum_obj.freqs

                            if (Task_Tag in ["LexicalDecRepDelay", "LexicalDecRepNoDelay"] and 'Cue' in epoch) or \
                            (Task_Tag == "RetroCue" and 'Audio1' in epoch):
                                
                                base_obj = trials.compute_psd(tmin=-0.5, tmax=0, **psd_kwargs)
                                base_all = base_obj.get_data()
                                baseline_data = base_all.mean(axis=0)
                                baseline_freqs = base_obj.freqs
                                
                            if baseline_data is not None:
                                if psd_active.shape[1] != baseline_data.shape[1]:
                                    interp_func = interp1d(baseline_freqs, baseline_data, kind='linear', 
                                                        axis=1, fill_value="extrapolate")
                                    baseline_resampled = interp_func(freqs_active)
                                    temp_base = baseline_resampled.copy()
                                else:
                                    temp_base = baseline_data.copy()

                                temp_base[temp_base == 0] = np.nan
                                psd_corrected = psd_active / temp_base
                            else:
                                psd_corrected = psd_active

                            save_path = os.path.join(save_dir, subject, 'multitaper_psd_spectrum')
                            if not os.path.exists(save_path): os.makedirs(save_path)
                            
                            filename = os.path.join(save_path, f'{tag}-psd.npy')
                            np.save(filename, {'power': psd_corrected, 'freqs': freqs_active, 'ch_names': trials.info['ch_names']})

                            chan_grid_psd(
                                psd_data=psd_corrected,
                                freqs=freqs_active,
                                ch_names=trials.info['ch_names'],
                                size=(4, 5),
                                vlim=(0.25, 2.5),
                                save_dir=save_path,
                                prefix=tag
                            )

                            del spectrum_obj, psd_active, psd_corrected
                            if 'psd_all' in locals(): del psd_all

                        del trials
            del raw, layout
            log_file.write(f"{datetime.datetime.now()}, {subject}, Multitaper  %%% completed %%% \n")

        except Exception as e:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Multitaper !!! failed with error !!! : {str(e)}\n")

        log_file.close()

    if "gamma" in processing_type:

        print('=========================\n')
        print(f'Gamma band-pass filter and permutation {subject}\n')
        print('=========================\n')
    
        ## Gamma_pool
        log_file = open(os.path.join(log_file_path,f'{subject}.txt'), 'a')
        try:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Executing Gamma band-pass filter and permutation \n")

            # read muscle artifact channels and update
            tsv_loc = os.path.join(LAB_root, BIDS_Tag, 'BIDS', 'derivatives', 'clean', f'sub-{subject}',
                        'ieeg')
            update_muscle_chs(subject, tsv_loc,Task_Tag)

            # load data
            layout = get_data(Task_Tag, root=LAB_root)
            raw1 = raw_from_layout(layout.derivatives['derivatives/clean'], subject=subject, desc='clean', extension='.edf',
                                  preload=False)

            # drop bad channels
            raw = raw1.copy().drop_channels(raw1.info['bads'])
            del raw1
            raw.load_data()

            # ref to average
            ch_type = raw.get_channel_types(only_data_chs=True)[0]
            raw.set_eeg_reference(ref_channels="average", ch_type=ch_type)

            # make direction
            if not os.path.exists(os.path.join(save_dir, subject)):
                os.mkdir(os.path.join(save_dir, subject))
            if not os.path.exists(os.path.join(save_dir, subject, 'gamma')):
                os.mkdir(os.path.join(save_dir, subject, 'gamma'))
            
            subj_gamma_dir=os.path.join(save_dir, subject, 'gamma')

            if not os.path.exists(os.path.join(bids_root, "derivatives", "stats")):
                os.mkdir(os.path.join(bids_root, "derivatives", "stats"))
                os.mkdir(os.path.join(bids_root, "derivatives", "stats",subject))
            elif not os.path.exists(os.path.join(bids_root, "derivatives", "stats", subject)):
                os.mkdir(os.path.join(bids_root, "derivatives", "stats",subject))

            subj_gamma_stats_dir=os.path.join(bids_root, "derivatives", "stats", subject)

            # gamma and permutation
            if Task_Tag == "LexicalDecRepDelay":

                # gamma_epoc_zip = zip(
                #     ('Auditory_stim/Repeat/CORRECT', 'Delay/Repeat/CORRECT','Go/Repeat/CORRECT', 'Resp/Repeat/CORRECT', 'Auditory_stim/Yes_No/CORRECT', 'Go/Yes_No/CORRECT', 'Resp/Yes_No/CORRECT','Delay/Yes_No/CORRECT'),
                #     ('Cue/Repeat/CORRECT', 'Cue/Repeat/CORRECT','Cue/Repeat/CORRECT', 'Cue/Repeat/CORRECT', 'Cue/Yes_No/CORRECT', 'Cue/Yes_No/CORRECT', 'Cue/Yes_No/CORRECT','Cue/Yes_No/CORRECT'),
                #     ((-2.5, 4),(-0.5, 1.5),(-4.5, 2), (-5, 1.5), (-2.5, 4), (-4.5, 2), (-5, 1.5), (-0.5, 1.5)),
                #     ('Auditory_inRep', 'Delay_inRep', 'Go_inRep', 'Resp_inRep', 'Auditory_inYN', 'Go_inYN', 'Resp_inYN','Delay_inYN'),
                #     (True, True, True, True, True, True, True,True)
                # )

                gamma_epoc_zip = zip(
                    ('Delay/Yes_No/CORRECT',),
                    ('Delay/Repeat/CORRECT',),
                    ((-0.5, 1.5),),
                    ('Delay_YN-Rep',),
                    (False, )
                )

            elif Task_Tag == "LexicalDecRepNoDelay":
                # gamma_epoc_zip=zip(
                #     ('Cue/Repeat/CORRECT','Auditory_stim/Repeat/CORRECT','Resp/Repeat/CORRECT','Cue/:=:/CORRECT','Auditory_stim/:=:/CORRECT','Cue/Yes_No/CORRECT','Auditory_stim/Yes_No/CORRECT','Resp/Yes_No/CORRECT'),
                #     ('Cue/Repeat/CORRECT','Cue/Repeat/CORRECT','Cue/Repeat/CORRECT','Cue/:=:/CORRECT','Cue/:=:/CORRECT','Cue/Yes_No/CORRECT','Cue/Yes_No/CORRECT','Cue/Yes_No/CORRECT'),
                #     ((-0.5, 3), (-2, 2), (-2, 1),(-0.5, 3), (-2, 2),(-0.5, 3), (-2, 2), (-2, 1)),
                #     ('Cue_inRep', 'Auditory_inRep','Resp_inRep','Cue_inSilence','Auditory_inSilence','Cue_inYN','Auditory_inYN','Resp_inYN'),
                #     (True, True, True,True, True,True, True,True)
                #  )
                gamma_epoc_zip=zip(
                    ('Resp/Yes_No/CORRECT',),
                    ('Cue/Yes_No/CORRECT',),
                    ((-2, 1),),
                    ('Resp_inYN',),
                    (True,)
                 )
            elif Task_Tag == "RetroCue":
                gamma_epoc_zip = zip(
                    ('Audio1/DRP_BTH/CORRECT','Audio2/DRP_BTH/CORRECT','Retro_Cue/DRP_BTH/CORRECT',
                     'Audio1/REP_1ST/CORRECT','Audio2/REP_1ST/CORRECT','Retro_Cue/REP_1ST/CORRECT','Go/REP_1ST/CORRECT','Resp/REP_1ST/CORRECT',
                     'Audio1/REP_2ND/CORRECT','Audio2/REP_2ND/CORRECT','Retro_Cue/REP_2ND/CORRECT','Go/REP_2ND/CORRECT','Resp/REP_2ND/CORRECT',
                     'Audio1/REP_BTH/CORRECT','Audio2/REP_BTH/CORRECT','Retro_Cue/REP_BTH/CORRECT','Go/REP_BTH/CORRECT','Resp/REP_BTH/CORRECT',
                     'Audio1/REV_BTH/CORRECT','Audio2/REV_BTH/CORRECT','Retro_Cue/REV_BTH/CORRECT','Go/REV_BTH/CORRECT','Resp/REV_BTH/CORRECT'),
                    (['Audio1/DRP_BTH/CORRECT'] * 3 +
                     ['Audio1/REP_1ST/CORRECT'] * 5 +
                     ['Audio1/REP_2ND/CORRECT'] * 5 +
                     ['Audio1/REP_BTH/CORRECT'] * 5 +
                     ['Audio1/REV_BTH/CORRECT'] * 5),
                    ((-0.5, 0.7+0.4),(-0.3, 0.7+0.4+1.5), (-0.5, 0.7+1.5),
                     (-0.5, 0.7+0.4),(-0.3, 0.7+0.4+1.5), (-0.5, 0.7+1.5), (-0.5, 1), (-0.5, 1),
                     (-0.5, 0.7+0.4),(-0.3, 0.7+0.4+1.5), (-0.5, 0.7+1.5), (-0.5, 1), (-0.5, 1),
                     (-0.5, 0.7+0.4),(-0.3, 0.7+0.4+1.5), (-0.5, 0.7+1.5), (-0.5, 1), (-0.5, 1),
                     (-0.5, 0.7+0.4),(-0.3, 0.7+0.4+1.5), (-0.5, 0.7+1.5), (-0.5, 1), (-0.5, 1)),
                    ('Auditory1_in_DRP_BTH', 'Auditory2_in_DRP_BTH', 'Cue_in_DRP_BTH',
                     'Auditory1_in_REP_1ST', 'Auditory2_in_REP_1ST', 'Cue_in_REP_1ST', 'Go_in_REP_1ST', 'Resp_in_REP_1ST',
                     'Auditory1_in_REP_2ND', 'Auditory2_in_REP_2ND', 'Cue_in_REP_2ND', 'Go_in_REP_2ND', 'Resp_in_REP_2ND',
                     'Auditory1_in_REP_BTH', 'Auditory2_in_REP_BTH', 'Cue_in_REP_BTH', 'Go_in_REP_BTH', 'Resp_in_REP_BTH',
                     'Auditory1_in_REV_BTH', 'Auditory2_in_REV_BTH', 'Cue_in_REV_BTH', 'Go_in_REV_BTH', 'Resp_in_REV_BTH'))

            for epoch_phase, baseline_tag, t_phase, tag_phase, is_bsl_correct in gamma_epoc_zip:

                if (Task_Tag == "LexicalDecRepDelay") and ("Repeat" not in epoch_phase) and (subject=="D0115"):
                    break # Patient D0115 has wrong YesNo task responses, so skip it

                out = []
                # If it is baseline correction, the sig2 only contains the first 0.5s of the baseline epoch (marked as baseline_tag).
                if is_bsl_correct:
                    bsl_t=(-0.5, 0)
                else:
                    bsl_t=t_phase

                # extract gamma
                for epoch, t, tag in zip(
                        (baseline_tag, epoch_phase),
                        (bsl_t, t_phase),
                        ('Baseline',tag_phase)):

                    # Get the spectras
                    t1 = t[0] - 0.5
                    t2 = t[1] + 0.5
                    times = (t1, t2)
                    trials = trial_ieeg(raw, epoch, times, preload=True, reject_by_annotation=False)
                    outliers_to_nan(trials, outliers=10)

                    gamma.extract(trials, copy=False, n_jobs=-1)
                    utils.crop_pad(trials, "0.5s")
                    trials.resample(100)
                    trials.filenames = raw.filenames
                    out.append(trials)
                    del trials

                # Get and cut baseline
                base = out.pop(0)

                # Permutation parameters
                nperm = 100000

                # run permutation: pool gamma

                mask = dict()
                data = []
                sig2 = base.get_data(copy=True)

                epoch = out[0]
                t = t_phase
                tag = tag_phase
                epoch.save(subj_gamma_stats_dir + f"/{tag}_rawpower-epo.fif", overwrite=True,fmt='double')

                # baseline correction
                power = scaling.rescale(epoch, base, 'mean', copy=True)
                z_score = scaling.rescale(epoch, base, 'zscore', copy=True) # average of the baseline by trial and by time
                power.save(subj_gamma_stats_dir + f"/{tag}_power-epo.fif", overwrite=True,fmt='double')
                z_score.save(subj_gamma_stats_dir + f"/{tag}_zscore-epo.fif", overwrite=True,fmt='double')

                sig1 = epoch.get_data(tmin=t[0], tmax=t[1], copy=True)

                is_perm=True
                if is_perm:
                    # time-perm  (test whether signal is greater than baseline, p=0.05 as it is a one-tailed test)
                    # if Task_Tag=='LexicalDecRepDelay' and (epoch_phase=='Auditory_inYN' or epoch_phase=='Go_inYN' or epoch_phase=='Resp_inYN'):
                    #     p_thresh_time_perm_cluster=0.05
                    # else:
                    #     p_thresh_time_perm_cluster=0.025
                    p_thresh_time_perm_cluster=0.025
                    mask[tag], p_act = stats.time_perm_cluster(
                        sig1, sig2, p_thresh=p_thresh_time_perm_cluster, axis=0, tails=1, n_perm=nperm, n_jobs=-10,
                        ignore_adjacency=1)
                    epoch_mask = mne.EvokedArray(mask[tag], epoch.average().info,
                                                tmin=t[0])

                    # plot mask
                    plot_save_gammamask(mask[tag],epoch_mask,subj_gamma_dir,f'{tag}.jpg')

                    # Calculate the p-value
                    p_vals = mne.EvokedArray(p_act, epoch_mask.info, tmin=t[0])

                    data.append((tag, epoch_mask.copy(),p_vals.copy()))

                    for tag, epoch_mask, p_vals in data:
                        epoch_mask.save(subj_gamma_stats_dir + f"/{tag}_mask-ave.fif", overwrite=True)
                        p_vals.save(subj_gamma_stats_dir + f"/{tag}_pval-ave.fif", overwrite=True)


                    if is_bsl_correct:
                        base.save(subj_gamma_stats_dir + f"/base-epo.fif", overwrite=True)
                del data, sig1, sig2, base, mask

            log_file.write(f"{datetime.datetime.now()}, {subject}, Gamma band-pass and permutation  %%% completed %%% \n")

        except Exception as e:
            log_file.write(f"{datetime.datetime.now()}, {subject}, Gamma band-pass and permutation !!! failed with error !!! : {str(e)}\n")

        log_file.close()
# %%
