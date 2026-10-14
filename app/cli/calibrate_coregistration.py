"""Calibrate the projector<->camera coregistration: the perspective
transform that maps what the camera photographs onto the area the
projector lights.

WHY IT MATTERS
--------------
Any imaging method that photographs the scene and then projects
patterns onto it (for instance to address zones picked on that photo)
needs the camera's and the projector's pixel grids to agree on where
things are - any mechanical offset between the camera and the projector
placed next to it has to be corrected in software first. That
correction is the "corregistration_array" this script finds, stored in
conf/hardware_config.json and applied through
onepix.hardware.coregistration_lib's apply_corregistration().

The "Calibrate coregistration" button on the GUI's Hardware settings
page does the same thing from a browser, without needing this device's
own screen.

WHAT THIS SCRIPT DOES
----------------------
1. Projects a full-white reference image.
2. Photographs it with the configured camera.
3. Opens an interactive matplotlib window and asks you to click, in
   order, the top-left, top-right, bottom-right and bottom-left
   corners of the *projected* area as it appears in that photo.
4. Computes the perspective transform those four points imply and
   saves it to conf/hardware_config.json.

This needs a real display attached to this machine (the projected
reference image and the corner-click window both require one) and
only works correctly run directly on the device, not relayed over a
remote desktop/SSH X11 forward with meaningful latency - take your
time clicking, there's no timeout.

USAGE
-----
Run from the repository root directory (the one containing the app/
folder) - `-m` resolves app.cli.calibrate_coregistration as a
package relative to the current directory, not to this file's own
location, so it fails with "No module named 'app'" from anywhere else,
including from inside app/GUI/flask (where the GUI's own README has you
cd to, to run run.py):

    cd /path/to/ONE-PIX_V3
    python -m app.cli.calibrate_coregistration

Running the file directly also works from any directory (no -m,
no package resolution involved):

    python /path/to/ONE-PIX_V3/app/cli/calibrate_coregistration.py

Make sure nothing else (the Flask app's own acquisition/tuning, another
script) is using the camera/projector at the same time. Once the
corner-click window opens, take your time - it waits indefinitely, it
will not close or give up on its own.
"""

from onepix.hardware.coregistration_lib import coregistration_calibration

import cv2


def main():

    print("-" * 100)
    print(
        "Projecting a reference image and photographing it - a "
        "window will open shortly asking you to click the four "
        "corners of the projected area (top-left, top-right, "
        "bottom-right, bottom-left, in that order)."
    )
    print("-" * 100)

    try:

        coregistration_calibration()

    finally:

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    print("-" * 100)
    print(
        "Done - corregistration_array saved to "
        "conf/hardware_config.json."
    )
    print("-" * 100)


if __name__ == "__main__":
    main()
