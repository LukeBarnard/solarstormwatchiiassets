import os
import glob


def project_info():
    """
    A function to load in dictionary of project directories stored in a config.txt file stored in the
    :return proj_dirs: Dictionary of project directories, with keys 'data','figures','code', and 'results'.
    """
    files = glob.glob('config.txt')

    if len(files) != 1:
        # If too few or too many config files, guess projdirs
        print('Error: Cannot find correct config file with project directories. Assuming typical structure')
        proj_dirs = {'data': os.path.join(os.getcwd(), 'data'), 'figs': os.path.join(os.getcwd(), 'figures'),
                     'code': os.path.join(os.getcwd(), 'code'), 'results': os.path.join(os.getcwd(), 'results'),
                     'hi_data': os.path.join(os.getcwd(), r'STEREO\ares.nrl.navy.mil\lz\L2_1_25'),
                     'out_data': os.path.join(os.getcwd(), 'out_data')}

    else:
        # Open file and extract
        with open(files[0], "r") as f:
            lines = f.read().splitlines()
            proj_dirs = {l.split(',')[0]: l.split(',')[1] for l in lines}

    # Just check the directories exist.
    for val in proj_dirs.itervalues():
        if not os.path.exists(val):
            print('Error, invalid path, check config: '+val)

    return proj_dirs

