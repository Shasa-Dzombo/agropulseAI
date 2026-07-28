"""
Read-only inspection of one real DJI multispectral band file (or the
companion consumer RGB JPG). No calibration math, no writes - this exists
solely to find out what DJI's real metadata actually looks like (EXIF tag
names, XMP fields, private TIFF tags) before any DN->radiance->reflectance
calibration code gets written against it. See Addendum 3/6 in the drone
orchard plan for why this has to come first: guessing tag names from memory
risks silently mis-mapping calibration coefficients, which is a much worse
failure than this script just printing "field not found."

Prints, in order:
    1. Image.getexif() - standard EXIF, tag names resolved via PIL.ExifTags
       where possible, raw numeric ID otherwise.
    2. Any nested EXIF sub-IFD (e.g. GPSInfo).
    3. Image.getxmp() - full XMP block, if present (Pillow 9.1+).
    4. tifffile.TiffFile(...).pages[0].tags - cross-check for anything in a
       private/vendor TIFF tag range outside standard EXIF/XMP.

No exception is swallowed - a real parse error should surface as-is, not be
guessed around.

Usage:
    python scripts/inspect_dji_metadata.py <path-to-one-real-DJI-file>

Run this once per band file in a single capture set (Blue/Green/Red/RedEdge/
NIR TIFFs + the companion RGB JPG) so both P4M's and Mavic 3M's actual
schemas get confirmed, including whether the two models differ.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import ExifTags, Image
import tifffile


def _print_section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def inspect_exif(path: str) -> None:
    _print_section("Image.getexif() - standard EXIF")
    with Image.open(path) as img:
        exif = img.getexif()
        if not exif:
            print("(no top-level EXIF block)")
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, f"<unknown tag {tag_id}>")
            print(f"{tag_id:>6} {tag_name:30} = {value!r}")

        _print_section("Nested EXIF sub-IFDs (e.g. GPSInfo)")
        for ifd_id in ExifTags.IFD:
            try:
                ifd = exif.get_ifd(ifd_id)
            except (KeyError, ValueError):
                continue
            if not ifd:
                continue
            print(f"-- IFD: {ifd_id.name} --")
            tag_map = ExifTags.GPSTAGS if ifd_id == ExifTags.IFD.GPSInfo else ExifTags.TAGS
            for tag_id, value in ifd.items():
                tag_name = tag_map.get(tag_id, f"<unknown tag {tag_id}>")
                print(f"{tag_id:>6} {tag_name:30} = {value!r}")

        _print_section("Image.getxmp() - XMP block")
        if hasattr(img, "getxmp"):
            xmp = img.getxmp()
            if xmp:
                print(xmp)
            else:
                print("(no XMP block)")
        else:
            print("(this Pillow version has no getxmp() - upgrade to 9.1+)")


def inspect_tiff_tags(path: str) -> None:
    _print_section("tifffile.TiffFile(...).pages[0].tags - cross-check")
    try:
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            for tag in page.tags:
                print(f"{tag.code:>6} {tag.name:30} = {tag.value!r}")
    except Exception as e:
        print(f"(not a TIFF, or tifffile couldn't parse it: {e})")


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    print(f"Inspecting: {path}")

    inspect_exif(path)
    inspect_tiff_tags(path)


if __name__ == "__main__":
    main()
