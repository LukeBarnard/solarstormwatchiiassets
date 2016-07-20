import glob
import os
import asset_production_tools as apt
import numpy as np
import pandas as pd
import scipy.interpolate as interp
import scipy.ndimage as ndimage
import sunpy.map as smap
import sunpy.image.coalignment as coalign
import matplotlib.pyplot as plt

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

    hi_path = os.path.join(proj_dirs['hi_data'], background_tag, craft_tag, camera_tag)

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


def filter_stars(img, thresh, res=512):
    """
    Function to supress bright stars in the HI field of view. Is purely data based and does not use star-maps. Looks for
    large (high gradient) peaks by calculating the laplacian of the image. Then uses morphological closing to identify
    the bright "tops" of stars, inside the high-gradient region. Then uses cubic interpolation (scipy.interp.bisplrep)
    to fill in pixels identified as a star. This is done in blocks over the image. This has only been developed with HI1
    data - unsure how it will behave with HI2.
    :param img: An array containing the HI image data.
    :param thresh: Float value containing the threshold used to identify the large gradients associated with stars.
                `  The threshold should be the chosen percentile of the brightness gradient distribution e.g. 90.
    :param res: Int value of block size (in pixels) to iterate over the image in.
    :return out_img: Star suppressed HI image.
    """

    # Get del2 of image, to find horrendous gradients
    del2 = ndimage.filters.laplace(img)
    # Find threshold of data, excluding NaNs
    thresh2 = np.percentile(del2[np.isfinite(del2)], thresh)
    abv_thresh = del2 > thresh2
    # Use binary closing to fill in big stars
    abv_thresh = ndimage.binary_closing(abv_thresh, structure=np.ones((3, 3)))

    if np.any(abv_thresh):
        star_r, star_c = np.nonzero(abv_thresh)
        good_vals = np.isfinite(img)
        nostar_r, nostar_c = np.nonzero(np.logical_and(~abv_thresh, good_vals))
    else:
        print('No points above threhsold')
        out_img = img.copy()
        return out_img

    # Get interpolation block sizes.
    dr = res
    drp = 10
    dc = res
    dcp = 10
    out_img = img.copy()
    edge_pad = 5
    for r in range(0, img.shape[0], dr):

        if r == 0:
            # Add 5 pixel window at edge
            row_id_stars = np.logical_and(star_r >= r + edge_pad, star_r <= r + dr)
            row_id_nostars= np.logical_and(nostar_r >= r - drp, nostar_r <= r + dr + drp)
        elif r > 0 and r < img.shape[0] - dr:
            row_id_stars = np.logical_and(star_r >= r, star_r <= r + dr)
            row_id_nostars = np.logical_and(nostar_r >= r - drp, nostar_r <= r + dr + drp)
        elif r == img.shape[0] - dr:
            # Add 5 pixel window at edge
            row_id_stars = np.logical_and(star_r >= r, star_r <= r + dr - edge_pad)
            row_id_nostars = np.logical_and(nostar_r >= r - drp, nostar_r <= r + dr + drp)

        for c in range(0, img.shape[1], dr):

            if c == 0:
                # Add 5 pixel window at edge
                col_id_stars = np.logical_and(star_c > c + edge_pad, star_c < c + dc)
                col_id_nostars = np.logical_and(nostar_c > c - dcp, nostar_c < c + dc + dcp)
            elif c > 0 and c < img.shape[1] - dc:
                col_id_stars = np.logical_and(star_c > c, star_c < c + dc)
                col_id_nostars = np.logical_and(nostar_c > c - dcp, nostar_c < c + dc + dcp)
            elif c == img.shape[1] - dc:
                # Add 5 pixel window at edge
                col_id_stars = np.logical_and(star_c > c, star_c < c + dc - edge_pad)
                col_id_nostars = np.logical_and(nostar_c > c - dcp, nostar_c < c + dc + dcp)

            # Interpolate the padded image region.
            id_find = np.logical_and(row_id_nostars, col_id_nostars)
            X = nostar_c[id_find]
            Y = nostar_r[id_find]
            f = interp.bisplrep(X, Y, img[Y, X], kx=3, ky=3)
            id_find = np.logical_and(row_id_stars, col_id_stars)
            X = star_c[id_find]
            Y = star_r[id_find]
            for y, x in zip(Y, X):
                out_img[y, x] = interp.bisplev(x, y, f)

    return out_img

def get_approx_star_field(img):
    """This function returns a binary array that provides a rough estimate of the locations of stars in the HI1 fov.
     All points above a fixed threshold are 1s, all points below are 0s. Used in the align_image, which is based
    on template matching against the background star-field.
    :param img: A HI image array
    :return img_stars: A binary image showing estimated locations of stars.
    """
    img_stars = img.copy()
    img_stars[~np.isfinite(img_stars)] = 0
    # TODO: THERE IS SOMETHING WRONG HERE. NOT ALL SMALL VALUES SET TO ZERO.
    img_stars[img_stars>np.percentile(img_stars,97.5)] = 1
    return img_stars

def align_image(src_map,dst_map):
    """
    Function to align two hi images. src_map is shifted by interpolation into the coordinates of dst_map. The
    transformation required to do this is calculated by pattern matching an approximation of the star field between
    frames in a subset of the HI image.
    :param src_map: A SunPy Map of the HI image to shift the coordinates of
    :param dst_map: A SunPy Map of the HI image to match coordinates against
    :return out_img: Array of src_map image shifted into coordinates of dst_map
    """
    MC = smap.MapCube([src_map,dst_map])
    shifts = coalign.calculate_match_template_shift(MC,layer_index=1,func=get_approx_star_field)
    xshift = (shifts['x'].to('deg') / MC[0].scale.x)
    yshift = (shifts['y'].to('deg') / MC[0].scale.y)
    to_shift = [-yshift[0].value, -xshift[0].value]
    src_img = coalign.repair_image_nonfinite(src_map.data)
    out_img = ndimage.interpolation.shift(src_img, to_shift, mode='constant',cval=np.NaN)
    return out_img

def hi_image_plain(file, star_suppress=False):

    if not isinstance(star_suppress,bool):
        print("Error: star_suppress should be true or false. Defaulting to false")
        star_suppress = False

    hi_map = smap.Map(file)

    if star_suppress:
        new_img = filter_stars(hi_map.data.copy(), 99, res=512)
        hi_map.data = new_img

    return hi_map
