import glob
import os
import numpy as np
import pandas as pd
import asset_production_tools as apt
import hi_processing as hip
import matplotlib as mpl
import matplotlib.pyplot as plt
import PIL.Image as Image
import sunpy.map as smap
import subprocess as sbp


def load_swpc_events():
    """
    Function to load in the excel file containing the SWPC CMEs provided by Curt. Import as a pandas dataframe. There is
    no official source for this data.
    :return:
    """
    # TODO: Ask Curt for source and acknowledgement for this data?
    proj_dirs = apt.project_info()
    # the swpc cmes has column names [event_id	t_appear	t_start	t_submission	lat	lon	half_width	vel	t_ace_obs
    # 	t_ace_wsa	diff	late_or_early	t_earth_si	Comment]. Get converters for making sure times ported correctly
    # Column 'diff' is awkward, as is a time delta, so handle seperately, by parsing to string first
    convert = {'t_appear': pd.to_datetime, 't_start': pd.to_datetime, 't_submission': pd.to_datetime,
               't_ace_obs': pd.to_datetime, 't_ace_wsa': pd.to_datetime, 't_earth_si': pd.to_datetime, 'diff': str}

    swpc_cmes = pd.read_excel(proj_dirs['swpc_data'], header=0, index_col=None, converters=convert)
    swpc_cmes['diff'] = pd.to_timedelta(swpc_cmes['diff'], unit='h')
    return swpc_cmes


def make_output_directory_structure():
    """
    Function to create the output directory structure, given the set of SWPC CMEs
    to analyse.
    :return:
    """
    # Get project directories
    proj_dirs = apt.project_info()
    # Get the swpc cme database
    swpc_cmes = load_swpc_events()
    # Loop over each event, and create a directory in outdata with a unique event name, from swpc id and ssw id
    for idx, cme in swpc_cmes.iterrows():
        label = "ssw_{0:03d}_swpc_{1:03d}".format(idx, cme['event_id'])
        for craft in ['sta', 'stb']:
            for type in ['norm', 'diff', 'animations']:
                path = os.path.join(proj_dirs['out_data'], label, craft, type)
                # If this directory doesnt exist, make it
                if not os.path.exists(path):
                    os.makedirs(path)
                else:
                    print(path + " exists already.")

    return


def make_ssw_assets():
    """
    Function to loop over the SWPC CMEs, find all relevant HI1A and HI1B 1-day background images, and produce
    plain, differenced and relative difference images.
    :return:
    """

    # Get project directories
    proj_dirs = apt.project_info()
    # Get the swpc cme database
    swpc_cmes = load_swpc_events()

    # TODO: Should I add this into hi_processing? what about a hip.save_img(diff=True)???
    plain_normalise = mpl.colors.Normalize(vmin=0.0, vmax=0.5)
    diff_normalise = mpl.colors.Normalize(vmin=-0.05, vmax=0.05)

    # Loop over the swpc_cmes and estimate HI1A\B start and stop times
    for idx, cme in swpc_cmes.iterrows():
        # cmes['t_start'] gives swpc estimate time CME at 0.1 AU. Assume HI1 start is 1hr before this, and leaves HI1
        # 24hr after
        t_start = cme['t_start'] - pd.Timedelta(hours=1)
        t_stop = cme['t_start'] + pd.Timedelta(hours=24)

        # Get event label
        event_label = "ssw_{0:03d}_swpc_{1:03d}".format(idx, cme['event_id'])
        print event_label
        for craft in ['sta', 'stb']:
            hi_files = hip.find_hi_files(t_start, t_stop, craft=craft, camera='hi1', background_type=1)

            # Loop to make plain and diff images
            for type in ['norm', 'diff']:
                # Loop over the hi_files, make each image type
                files_c = hi_files[1:]
                files_p = hi_files[0:-1]
                for fc, fp in zip(files_c, files_p):

                    if type == 'norm':
                        # Get Sunpy map of the image, convert to grayscale image with plain_normalise
                        # TODO: Should flipud the image, as no origin lower option with PIL?
                        hi_map = hip.get_image_plain(fc, star_suppress=False)
                        out_img = mpl.cm.gray(plain_normalise(hi_map.data), bytes=True)
                        out_img = Image.fromarray(out_img)
                    elif type == 'diff':
                        # TODO: Add in check that frames are only 1 cadence apart.
                        # TODO: What should scaling be for differenced images? What structuing element for median filter?
                        hi_map = hip.get_image_diff(fc, fp, align=True, smoothing=True)
                        out_img = mpl.cm.gray(diff_normalise(hi_map.data), bytes=True)
                        out_img = Image.fromarray(out_img)

                    out_name = "_".join([event_label, craft, type, hi_map.date.strftime('%Y%m%d_%H%M%S'), '.jpg'])
                    out_path = os.path.join(proj_dirs['out_data'], event_label, craft, type, out_name)
                    out_img.save(out_path, optimize=True)

                # Now create the manifest for this event/craft/type
                make_manifest(event_label, craft, type, n=3)

            # Now makes gifs of each image type and join into a joint gif using a shell script for imagemagick
            norm_dir = os.path.join(proj_dirs['out_data'], event_label, craft, 'norm')
            diff_dir = os.path.join(proj_dirs['out_data'], event_label, craft, 'diff')
            ani_dir = os.path.join(proj_dirs['out_data'], event_label, craft, 'animations')
            shell_dir = os.path.join(proj_dirs['code'], 'combine_images.sh')
            sbp.call([shell_dir, norm_dir, diff_dir, ani_dir], shell=True)


def make_manifest(event, craft, type, n=3):
    """
    This function produces the manifest to serve the ssw assets. This has the format of a CSV file with:
    asset_name,file1,file2,...fileN.
    Asset names will be given the form of sswN_swpcM_craft_type_t1_t3, where t1 and t3 correspond to the times of the
    first and third image in sets of three.
    :param event: String of the event label, as taken from asset_production.make_assets
    :param craft: String of the craft label ['sta', 'stb'], as taken from asset_production.make_assets
    :param type: String of the data type ['norm', 'diff'], as taken from asset_production.make_assets
    :param n:  Number of images to link together in the manifest for each asset.
    :return: Outputs a "manifest.csv" file in the event/craft/type directory of these images.
    """
    proj_dirs = apt.project_info()

    if not isinstance(n, int):
        print("Error: n should be integer. Converting")
        n = int(n)

    if not isinstance(event, str):
        print("Error: event_label type should be str")

    if not isinstance(craft, str):
        print("Error: craft type should be str")

    if not isinstance(type, str):
        print("Error: craft type should be str")

    # Get all the files for this event/craft combo
    data_dir = os.path.join(proj_dirs['out_data'], event, craft, type)
    # Check the data dir exists,
    if not os.path.exists(data_dir):
        print("Error: data_dir path does not exist.")

    # Form first part of asset name, get list of files.
    asset_name_part1 = "_".join([event, craft, type])
    files = glob.glob( os.path.join(data_dir, '*' + type +'.jpg'))
    # get only filename not full path
    files = [os.path.basename(f) for f in files]
    # Make sure files are time sorted.
    files.sort()
    # Make the manifest file
    manifest_path = os.path.join(data_dir,'manifest.csv')
    with open(manifest_path, 'w') as manifest:
        i=0
        while (i+n) < len(files):
            # File names have format ssw_aaa_swpc_bbb_craft_camera_yyyymmdd_HHMMSS_type.jpg
            # Pull out the times of the first and nth file to be linked to make asset name
            i_n = i + n
            fi = files[i].split('_')
            ti = fi[6] + 'T' + fi[7]
            fn = files[i_n].split('_')
            tn = fn[6] + 'T' + fn[7]
            # Form full asset name
            asset_name_part2 = ti + '_' + tn
            asset_name_full = "_".join([asset_name_part1,asset_name_part2])
            manifest_elements =[asset_name_full]
            # Add on the subset of files
            manifest_elements.extend(files[i: i_n])
            # Write out as comma sep list.
            manifest.write(",".join(manifest_elements) + "\n")
            i = i_n
            # TODO: Add in check to make sure all files are processed? Or add in staement to say which files werent?


def test_scaling():
    """
    Function to loop over the SWPC CMEs, find all relevant HI1A and HI1B 1-day background images, and produce
    plain, differenced and relative difference images.
    :return:
    """
    # Get project directories
    proj_dirs = apt.project_info()

    # Setup time span of HI data subset
    t_start = pd.datetime(year=2008, month=1, day=1)
    t_stop = t_start + pd.Timedelta(days=3)
    # Setup a 4 panel plot, for STA and STb with Norm and Diff images.
    fig, ax = plt.subplots(2, 2, figsize=(17, 12))
    for i, craft in enumerate(['sta', 'stb']):
        hi_files = hip.find_hi_files(t_start, t_stop, craft=craft, camera='hi1', background_type=1)
        # Loop over the hi_files and make plain, differenced and relative difference images.
        percentiles = np.array([1, 2.5, 5, 10, 90, 95, 97.5, 99])
        norm_data = np.zeros((len(hi_files), len(percentiles)), dtype=float)*np.NaN
        diff_data = np.zeros((len(hi_files), len(percentiles)), dtype=float)*np.NaN
        hi_c = hi_files[1:]
        hi_p = hi_files[0:-1]

        for j, (fc, fp) in enumerate(zip(hi_c, hi_p)):
            hi_map = hip.get_image_plain(fc, star_suppress=False)
            norm_data[j, :] = np.percentile((hi_map.data[np.isfinite(hi_map.data)]), percentiles)
            hi_map = hip.get_image_diff(file_c=fc, file_p=fp, star_suppress=False, align=True, smoothing=True)
            diff_data[j, :] = np.percentile((hi_map.data[np.isfinite(hi_map.data)]), percentiles)

        ax[i, 0].plot(norm_data, '-')
        ax[i, 0].set_ylabel('Normal Img. intensity')
        ax[i, 1].plot(diff_data, '-')
        ax[i, 1].set_ylabel('Diff Img. intensity')

    for asub in [ax[:, 0], ax[:, 1]]:
        ymn = np.min([a.get_ylim()[0] for a in asub])
        ymx = np.max([a.get_ylim()[1] for a in asub])
        for a in asub:
            a.set_ylim(ymn, ymx)

    plt.subplots_adjust(left=0.075, right=0.98, bottom=0.075, top=0.98, wspace=0.1, hspace=0.1)
    name = os.path.join(proj_dirs['figs'], 'scaling_testing.png')
    plt.savefig(name)
    plt.close('all')


def test_interpolation():
    """
    Function to loop over the SWPC CMEs, find all relevant HI1A and HI1B 1-day background images, and produce
    plain, differenced and relative difference images.
    :return:
    """
    # Get project directories
    t_start = pd.datetime(year=2008, month=1, day=1)
    t_stop = t_start + pd.Timedelta(days=1)

    hi_files = hip.find_hi_files(t_start, t_stop, craft='sta', camera='hi1', background_type=1)

    # Loop over the hi_files and make plain, differenced and relative difference images.
    hi_map = smap.Map(hi_files[0])
    hip.suppress_starfield(hi_map.data)
    plt.show()


def test_alignment():
    """
        Function to test the error handling is behaving as expected in hi_processing.align
        :return:
        """
    hp = smap.Map(r"E:\STEREO\ares.nrl.navy.mil\lz\L2_1_25\b\img\hi_1\20111022\20111022_172901_14h1B.fts")
    hc = smap.Map(r"E:\STEREO\ares.nrl.navy.mil\lz\L2_1_25\b\img\hi_1\20111022\20111022_180901_14h1B.fts")
    hp = hip.align_image(hp, hc)
    print hp


def test_diff_image():
    """
    Function to test the error handling is behaving as expected in hi_processing.get_image_diff
    :return:
    """
    t_start = pd.datetime(year=2008, month=1, day=1)
    t_stop = t_start + pd.Timedelta(days=1)

    hi1a_files = hip.find_hi_files(t_start, t_stop, craft='sta', camera='hi1', background_type=1)
    hi2a_files = hip.find_hi_files(t_start, t_stop, craft='sta', camera='hi2', background_type=1)

    # Test cadence
    # This should return an error message and blank frame, as files more than one cadence apart.
    himap = hip.get_image_diff(hi1a_files[2], hi1a_files[0], star_suppress=False, align=True, smoothing=True)
    himap.peek()
    # Test detector match
    # This should return an error message and blank frame, as files from different detectors.
    hip.get_image_diff(hi1a_files[2], hi2a_files[1], star_suppress=False, align=True, smoothing=True)
    himap = hip.get_image_diff(hi1a_files[2], hi1a_files[1], star_suppress=False, align=True, smoothing=True)
    himap.peek()


