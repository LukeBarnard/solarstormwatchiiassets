import asset_production_tools as apt
import os
import pandas as pd
import glob
def find_hi_files(t_start, t_stop, craft="sta", camera="hi1", background_type=1):
    """
    Function to find a subset of the STEREO Heliospheric imager data.
    :param t_start: Datetime giving start time of data window requested
    :param t_stop: Datetime giving stop time of data window requested
    :param craft: String ['sta', 'stb'] to select data from either STEREO-A or STEREO-B.
    :param craft: String ['hi1', 'hi2'] to select data from either HI1 or HI2.
    :param background_type:  Integer [1, 11] to decide between selecting one or eleven day background subtraction.
    :return:
    """
    # STEREO HI data is stored on a directory tree with the following format:
    # level > background_type > craft > img > camera > daily_directories > hi_data_files

    #Get HI dir.
    proj_dirs = apt.project_info()

    # Check the input arguments:
    if craft not in set(['sta', 'stb']):
        print("Error: camera should be set to either 'sta', or 'stb'. Defaulting to 'stb'")
        camera = 'sta'

    if camera not in set(['hi1','hi2']):
        print("Error: camera should be set to either 'hi1', or 'hi2'. Defaulting to 'hi1'")
        camera = 'hi1'

    if not isinstance(background_type,int):
        print("Error: background_type should be an integer, either 1 or 11. Defaulting to 1")
        background_type = 1

    if background_type not in set([1,11]):
        print("Error: background_type is invalid. Should be either 1, or 11. Defaulting to 1")
        background_type = 1

    # Work out the right directory names to get to the right part of data tree
    background_tag = "L2_" + str(background_type) + "_25"
    # Get path up to craft
    if craft == 'sta':
        craft_tag = 'a\img'
    elif craft == 'stb':
        craft_tag = 'b\img'

    # Get path up to craft
    if camera == 'hi1':
        camera_tag = 'hi_1'
    elif craft == 'hi2':
        camera_tag = 'hi_2'
    data_path = background_tag + '\\' +  craft_tag + '\\' + camera_tag
    hi_path = os.path.join(proj_dirs['hi_data'], data_path)

    # Use t_start/stop to get list of days to get data
    day_list = [t.strftime('%Y%m%d') for t in pd.date_range(t_start.date(),t_stop.date(), freq='1D')]

    all_files = []
    for day in day_list:
        path = os.path.join(hi_path,day + '\\*.fts')
        all_files.extend(glob.glob(path))

    # Out_files contains all files on dates corresponding to t_start/stop. Now restrict to the exact time window.
    t_min = t_start.strftime('%Y%m%d_%H%M%S')
    t_max = t_stop.strftime('%Y%m%d_%H%M%S')
    out_files = []
    for file_path in all_files:
        # Get the filename without full path
        file_name = os.path.basename(file_path)
        # HI files follow naming convention of yyyymmdd_hhmmss_datatag.fts. So first 15 elements give a time string.
        # TODO: Better way to pull out the timestring?
        time_tag = file_name[:15]
        if (time_tag <= t_min) | (time_tag <= t_max):
            out_files.append(file_path)

    return out_files

