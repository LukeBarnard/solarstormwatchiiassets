import asset_production as ap


def main():

    ap.make_output_directory_structure()
    ap.make_ssw_assets()
    # ap.test_scaling()
    # ap.test_interpolation()
    # ap.test_alignment()
    # ap.test_diff_image()
    # ap.test_image_orientation()
    return

if __name__ == '__main__':
    main()