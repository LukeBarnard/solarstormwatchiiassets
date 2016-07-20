import os
import numpy as np
import pandas as pd
import asset_production_tools as apt
import hi_processing as hip

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
               't_ace_obs': pd.to_datetime, 't_ace_wsa': pd.to_datetime, 't_earth_si':pd.to_datetime, 'diff': str}

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
    swpc_cmes  = load_swpc_events()
    # Loop over each event, and create a directory in outdata with a unique event name, from swpc id and ssw id
    for idx, cme in swpc_cmes.iterrows():
        label = "ssw_{0:03d}_swpc_{1:03d}".format(idx, cme['event_id'])
        path = os.path.join(proj_dirs['out_data'], label)
        # If this directory doesnt exist, make it
        if not os.path.exists(path):
            os.mkdir(path)
        else:
            print(path + " exists already.")

    return

def make_ssw_assets():
    """
    Function to loop over the swpc CMEs, find all relevant HI1A and HI1B 1-day background images, and produce
    plain, differenced and relative difference images.
    :return:
    """

    # Get project directories
    proj_dirs = apt.project_info()
    # Get the swpc cme database
    swpc_cmes = load_swpc_events()

    # Loop over the swpc_cmes and estimate HI1A\B start and stop times
    for idx, cme in swpc_cmes.iterrows():
        # cmes['t_start'] gives swpc estimate time CME at 0.1 AU. Assume HI1 start is 1hr before this, and leaves HI1
        # 24hr after
        t_start = cme['t_start'] - pd.Timedelta(hours=1)
        t_stop = cme['t_start'] + pd.Timedelta(hours=24)
        print t_start, t_stop

        t_stop.strftime('%Y%m%d')