"""
Extracts usable nadir (straight-down) still frames from drone video.

Why the filtering exists: the canopy-vigor pipeline
(app/services/canopy_vigor_assessment.py) assumes a straight-down view. On an
oblique frame the Excess-Green index can't tell a crop from the treeline
behind it, and ground scale changes from the foreground to the background of
the same image, so any area figure derived from it is wrong. Feeding oblique
frames in produces confident-looking nonsense, so they're rejected here
rather than silently analyzed.

DJI records gimbal pitch in a .SRT sidecar or an embedded data track, but
neither is guaranteed to be present (and reading the embedded track needs
ffmpeg). When no telemetry is available this falls back to judging the
picture itself: a straight-down frame contains no sky and no horizon. That
is a heuristic, not a measurement - it can only say "this frame doesn't look
like it's pointing at the horizon", never "the gimbal was at -90 degrees".

Also drops near-duplicate frames, since a hovering aircraft yields hundreds
of essentially identical stills.

Usage:
    python scripts/extract_nadir_frames.py \\
        --video "C:\\Users\\you\\Drones\\DJI_0002_W.MP4" \\
        --output-folder "C:\\Users\\you\\Drones\\frames" \\
        [--sample-interval-s 1.0] [--max-sky-fraction 0.08] [--report-only]

    # every video in a folder
    python scripts/extract_nadir_frames.py --video-folder "C:\\Users\\you\\Drones" \\
        --output-folder "C:\\Users\\you\\Drones\\frames"

--report-only scores the footage and prints the verdict without writing any
files - use it first to find out whether a clip contains nadir frames at all.
"""

import argparse
import os
import sys

import cv2
import numpy as np

_VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")

# Top fraction of the frame inspected for sky. A horizon appearing lower
# than this in a genuinely downward-looking shot isn't realistic.
_SKY_BAND_FRACTION = 0.30

# HSV thresholds for "sky-like": bright and washed out (overcast/cloud) or
# bright and blue. Deliberately broad - the cost of wrongly rejecting a good
# frame is one lost still; the cost of wrongly accepting an oblique one is a
# bogus area measurement downstream.
_SKY_MIN_VALUE = 150
_SKY_MAX_SATURATION = 60
_BLUE_HUE_LOW, _BLUE_HUE_HIGH = 90, 130
_BLUE_MIN_SATURATION = 60

# Mean absolute pixel difference below which two frames are "the same shot".
_DUPLICATE_DIFF_THRESHOLD = 12.0


def sky_fraction(frame: np.ndarray) -> float:
    """Fraction of the frame's upper band that looks like sky. Near zero for
    a straight-down shot; substantial once the horizon is in view."""
    height = frame.shape[0]
    band = frame[: max(1, int(height * _SKY_BAND_FRACTION))]
    hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)
    hue, saturation, value = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    bright_and_washed_out = (value >= _SKY_MIN_VALUE) & (saturation <= _SKY_MAX_SATURATION)
    bright_blue = (
        (hue >= _BLUE_HUE_LOW) & (hue <= _BLUE_HUE_HIGH)
        & (saturation >= _BLUE_MIN_SATURATION) & (value >= _SKY_MIN_VALUE)
    )
    return float(np.count_nonzero(bright_and_washed_out | bright_blue)) / band[:, :, 0].size


def is_duplicate(frame: np.ndarray, previous_small: np.ndarray):
    """Compares downscaled greyscale frames so a hovering aircraft doesn't
    produce hundreds of copies of one still."""
    small = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY)
    if previous_small is None:
        return False, small
    difference = float(np.mean(cv2.absdiff(small, previous_small)))
    return difference < _DUPLICATE_DIFF_THRESHOLD, small


def process_video(path: str, output_folder: str, sample_interval_s: float, max_sky_fraction: float, report_only: bool) -> dict:
    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        print(f"  ! could not open {path}")
        return {"opened": False}

    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(round(fps * sample_interval_s)))
    stem = os.path.splitext(os.path.basename(path))[0]

    checked = kept = rejected_sky = rejected_duplicate = 0
    sky_scores = []
    previous_small = None

    for index in range(0, total_frames, step):
        capture.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = capture.read()
        if not ok:
            continue
        checked += 1

        score = sky_fraction(frame)
        sky_scores.append(score)
        if score > max_sky_fraction:
            rejected_sky += 1
            continue

        duplicate, previous_small = is_duplicate(frame, previous_small)
        if duplicate:
            rejected_duplicate += 1
            continue

        kept += 1
        if not report_only:
            timestamp_s = index / fps
            out_path = os.path.join(output_folder, f"{stem}_t{timestamp_s:07.2f}s.jpg")
            cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    capture.release()
    return {
        "opened": True, "checked": checked, "kept": kept,
        "rejected_sky": rejected_sky, "rejected_duplicate": rejected_duplicate,
        "median_sky": float(np.median(sky_scores)) if sky_scores else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--video", help="One video file")
    source.add_argument("--video-folder", help="Every video in this folder")
    parser.add_argument("--output-folder", required=True)
    parser.add_argument("--sample-interval-s", type=float, default=1.0)
    parser.add_argument(
        "--max-sky-fraction", type=float, default=0.08,
        help="Reject a frame when more than this fraction of its upper band looks like sky (default 0.08)",
    )
    parser.add_argument("--report-only", action="store_true", help="Score the footage without writing frames")
    args = parser.parse_args()

    if args.video:
        videos = [args.video]
    else:
        videos = [
            os.path.join(args.video_folder, name)
            for name in sorted(os.listdir(args.video_folder))
            if name.lower().endswith(_VIDEO_EXTENSIONS)
        ]
    if not videos:
        sys.exit("No video files found.")

    if not args.report_only:
        os.makedirs(args.output_folder, exist_ok=True)

    total_kept = 0
    for path in videos:
        print(f"\n{os.path.basename(path)}")
        result = process_video(
            path, args.output_folder, args.sample_interval_s, args.max_sky_fraction, args.report_only
        )
        if not result.get("opened"):
            continue
        total_kept += result["kept"]
        print(
            f"  checked {result['checked']} frames | kept {result['kept']} | "
            f"rejected {result['rejected_sky']} (sky/horizon), {result['rejected_duplicate']} (duplicate) | "
            f"median sky score {result['median_sky']:.3f}"
        )
        if result["checked"] and result["kept"] == 0:
            print("  -> No nadir-looking frames. This clip appears to be shot obliquely;")
            print("     fly a mapping/survey mission with the gimbal at -90 degrees for usable stills.")

    print(f"\nTotal frames kept: {total_kept}")
    if args.report_only:
        print("(--report-only: nothing written)")
    elif total_kept:
        print(f"Written to: {args.output_folder}")


if __name__ == "__main__":
    main()
