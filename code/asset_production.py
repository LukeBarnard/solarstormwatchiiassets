import os
import numpy as np
import pandas as pd
import asset_production_tools as apt
import hi_processing as hip
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
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
        for craft in ['sta', 'stb']:
            path = os.path.join(proj_dirs['out_data'], label, craft)
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
    #swpc_cmes = swpc_cmes[1:]
    # Loop over the swpc_cmes and estimate HI1A\B start and stop times
    for idx, cme in swpc_cmes.iterrows():
        # cmes['t_start'] gives swpc estimate time CME at 0.1 AU. Assume HI1 start is 1hr before this, and leaves HI1
        # 24hr after
        t_start = cme['t_start'] - pd.Timedelta(hours=1)
        t_stop = cme['t_start'] + pd.Timedelta(hours=24)

        #Get event label
        event_label = "ssw_{0:03d}_swpc_{1:03d}".format(idx, cme['event_id'])

        for craft in ['sta', 'stb']:
            hi_files = hip.find_hi_files(t_start, t_stop, craft=craft, camera='hi1', background_type=1)
            print(len(hi_files))
            # Loop over the hi_files and make plain, differenced and relative difference images.
            for file in hi_files:

                hi_map = hip.get_image_plain(file, star_suppress=False)
                out_file = event_label + '_' + craft + '_hi1_' + hi_map.date.strftime('%Y%m%d_%H%M%S') + '_stars_keep.png'
                path = os.path.join(proj_dirs['out_data'], event_label, craft, out_file)
                vmin = 0
                vmax = 0.5
                mpimg.imsave(path, hi_map.data, vmin = vmin, vmax=vmax, cmap = 'gray')
                # TODO: Find out why this is hanging on the second event. Is to do with the interpolation during star removal
                hi_map = hip.get_image_plain(file, star_suppress=True)
                out_file = event_label + '_' + craft + '_hi1_' + hi_map.date.strftime('%Y%m%d_%H%M%S') + '_stars_remove.png'
                path = os.path.join(proj_dirs['out_data'], event_label, craft, out_file)
                mpimg.imsave(path, hi_map.data, vmin=vmin, vmax=vmax, cmap='gray')

            # Now makes gifs of each image type and join into a joint gif using a shell script for imagemagick
            out_dir = os.path.join(proj_dirs['out_data'], event_label, craft)
            shell_dir = os.path.join(proj_dirs['code'], 'combine_images.sh')
            sbp.call([shell_dir, out_dir], shell=True)
        break

def test_scaling():
    """
    Function to loop over the SWPC CMEs, find all relevant HI1A and HI1B 1-day background images, and produce
    plain, differenced and relative difference images.
    :return:
    """
    # Get project directories
    t_start = pd.datetime(year=2008,month=1,day=1)
    t_stop = t_start + pd.Timedelta(days=30)
    hi_files = hip.find_hi_files(t_start, t_stop, craft='sta', camera='hi1', background_type=1)
    # Loop over the hi_files and make plain, differenced and relative difference images.
    percentiles = np.arange(90,99,0.5)
    out_data = np.zeros((len(percentiles),len(hi_files)),dtype=float)
    for i,file in enumerate(hi_files):
        hi_map = hip.get_image_plain(file, star_suppress=False)
        out_data[:,i] = np.percentile((hi_map.data[np.isfinite(hi_map.data)]), percentiles)

    plt.figure(figsize=(15,10))
    for i in range(0,len(percentiles)):
        plt.plot(out_data[i,:],'k-')

    #TODO: label the figure up.
    print zip(percentiles,np.median(out_data,axis=1),np.mean(out_data,axis=1))

    plt.show()

def test_interpolation():
    """
    Function to loop over the SWPC CMEs, find all relevant HI1A and HI1B 1-day background images, and produce
    plain, differenced and relative difference images.
    :return:
    """
    # Get project directories
    t_start = pd.datetime(year=2008,month=1,day=1)
    t_stop = t_start + pd.Timedelta(days=1)

    hi_files = hip.find_hi_files(t_start, t_stop, craft='sta', camera='hi1', background_type=1)

    # Loop over the hi_files and make plain, differenced and relative difference images.
    hi_map = smap.Map(hi_files[0])
    hip.filter_stars(hi_map.data, 98, res=512)


    plt.show()