import matplotlib.pyplot as plt
import numpy as np
import imutils
import cv2
import json
import os
from tkinter.messagebox import showinfo
import screeninfo
import sys

from onepix.hardware.Projection import get_display_configuration
from onepix.hardware.gui_thread import gui_thread

hardware_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(hardware_path)

from CameraBridge import *

screenWidth, proj_shape = get_display_configuration()

hardware_json_path = os.path.abspath(
    hardware_path + f"{os.sep}..{os.sep}..{os.sep}conf/hardware_config.json"
)

with open(hardware_json_path) as file:
    hardware_dict = json.load(file)

camera = CameraBridge(hardware_dict["name_camera"])


def order_corners(pts):
    """
    Given the four points found for our contour, order them into
    Top Left, Top Right, Bottom Right, Bottom Left
    This order is important for perspective transforms
    :param pts: Contour points to be ordered correctly
    """
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def get_reference_image(
    img_resolution=(proj_shape.width, proj_shape.height), grayscale=50
):
    """
    Build the image we will be searching for.  In this case, we just want a
    large white box (full screen)
    :param img_resolution: this is our screen/projector resolution
    """
    width, height = img_resolution
    img = grayscale * np.ones((height, width, 1), np.uint8)
    return img


def get_destination_array(rect):
    """
    Given a rectangle return the destination array
    :param rect: array of points  in [top left, top right, bottom right, bottom left] format
    """
    (tl, tr, br, bl) = rect  # Unpack the values
    # Compute the new image width
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))

    # Compute the new image height
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))

    # Our new image width and height will be the largest of each
    max_width = max(int(width_a), int(width_b))
    max_height = max(int(height_a), int(height_b))

    # Create our destination array to map to top-down view
    dst = np.array(
        [
            [0, 0],  # Origin of the image, Top left
            [max_width - 1, 0],  # Top right point
            [max_width - 1, max_height - 1],  # Bottom right point
            [0, max_height - 1],  # Bottom left point
        ],
        dtype="float32",
    )
    return dst, max_width, max_height


def find_edges(frame):
    """
    Given a frame, find the edges
    :param frame: Camera Image
    :return: Found edges in image
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)  # Add some blur
    edged = cv2.Canny(gray, 30, 200)  # Find our edges
    return edged


def manual_get_region_corners(frame):
    """
    User selects the four corners of our projected region and return them in
    the proper order
    :param frame: Camera Image
    :return: Projection region rectangle
    """
    fig = plt.figure()
    plt.imshow(frame)
    plt.title("Projection corners selection")
    # ginput()'s default timeout is 30s - comfortably too short for
    # "walk over to the physical projected screen and click its four
    # corners" (the window just opened; the user hasn't even seen it
    # yet). timeout=0 waits indefinitely instead. Without this, it
    # silently returns whatever was clicked so far (often nothing) once
    # time runs out, rather than erroring - that's what produced the
    # "cannot reshape array of size 0 into shape (4,2)" crash below.
    screen_contours = plt.ginput(n=4, timeout=0)
    plt.close(fig)

    if len(screen_contours) != 4:
        raise RuntimeError(
            f"Expected 4 corner clicks, got {len(screen_contours)} "
            "(the calibration window was likely closed before all four "
            "corners were clicked). Run the calibration again and click "
            "all four corners in order: top-left, top-right, "
            "bottom-right, bottom-left."
        )

    pts = np.asarray(screen_contours, dtype=np.int32).reshape(4, 2)
    rect = order_corners(pts)
    # Uncomment these lines to see the contours on the image

    cv2.drawContours(frame, [pts], -1, (255, 0, 0), 3)
    plt.figure()
    plt.imshow(frame)
    plt.show(block=False)
    return rect


def get_region_corners(frame):
    """
    Find the four corners of our projected region and return them in
    the proper order
    :param frame: Camera Image
    :return: Projection region rectangle
    """
    edged = find_edges(frame)
    # findContours is destructive, so send in a copy
    contours, hierarchy = cv2.findContours(
        edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    # Sort our contours by area, and keep the 10 largest
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    screen_contours = None

    for c in contours:
        # Approximate the contour
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        # If our contour has four points, we probably found the screen
        if len(approx) == 4:
            screen_contours = approx
            break
    else:
        print("Did not find contour")
    # Uncomment these lines to see the contours on the image
    # cv2.drawContours(frame, [screen_contours], -1, (0, 255, 0), 3)
    # cv2.imshow('Screen', frame)
    # cv2.waitKey(0)
    pts = screen_contours.reshape(4, 2)
    rect = order_corners(pts)
    return rect


def show_full_frame(frame):
    """
    Given a frame, display the image in full screen
    :param frame: image to display full screen

    All OpenCV HighGUI calls must run on gui_thread's dedicated thread
    (see onepix/hardware/gui_thread.py) - OpenCV's Qt backend binds its
    internal QObjects to whichever thread first touches them. Calling
    these directly from here used to bind them to whatever thread calls
    show_full_frame() (e.g. a Flask request thread, since "has" calls
    this during pattern creation before any acquisition thread exists),
    after which every later call made correctly through gui_thread
    (e.g. from Projection.py) would hang forever trying to marshal onto
    that first, non-GUI-pumping thread.
    """
    gui_thread.run(cv2.namedWindow, "FullScreen", cv2.WND_PROP_FULLSCREEN)
    gui_thread.run(cv2.setWindowProperty, "FullScreen", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    gui_thread.run(cv2.moveWindow, "FullScreen", proj_shape.x, proj_shape.y)
    gui_thread.run(cv2.imshow, "FullScreen", frame)


def hide_full_frame(window="FullScreen"):
    """
    Kill a named window, the default is the window named 'FullScreen'
    :param window: Window name if different than default
    """
    gui_thread.run(cv2.destroyWindow, window)
    gui_thread.run(cv2.waitKey, 1)


def get_perspective_transform(
    tag, screen_resolution=(proj_shape.width, proj_shape.height), prop_file=None
):
    """
    Determine the perspective transform for the current physical layout
    return the perspective transform, max_width, and max_height for the
    projected region

    """
    # camera.camera_open()
    with open(hardware_json_path) as f:
        setup_dict = json.load(f)
    corregistration_array = setup_dict["corregistration_array"]
    max_width = setup_dict["max_width"]
    max_height = setup_dict["max_height"]

    if corregistration_array == []:
        tag = "init"
    else:
        corregistration_array = np.reshape(corregistration_array, (3, 3))

    if tag == "init":
        reference_image = get_reference_image(screen_resolution)

        # Display the reference image
        show_full_frame(reference_image)
        # Delay execution a quarter of a second to make sure the image is displayed
        # Don't use time.sleep() here, we want the IO loop to run.  Sleep doesn't do that
        gui_thread.run(cv2.waitKey, 500)

        # Grab a photo of the frame

        camera.get_image(tag)

        save_path = f"./{tag}.png"
        frame = cv2.imread(save_path)
        os.remove(save_path)

        # We're going to work with a smaller image, so we need to save the scale
        ratio = frame.shape[0] / 300.0

        # Undistort the camera image
        # frame = undistort_image(frame, prop_file=prop_file)
        pict = frame.copy()
        # Resize our image smaller, this will make things a lot faster
        frame = imutils.resize(frame, height=300)

        rect = get_region_corners(frame)
        rect *= ratio  # We shrank the image, so now we have to scale our points up

        dst, max_width, max_height = get_destination_array(rect)
        # Remove the reference image from the display
        hide_full_frame()

        corregistration_array = cv2.getPerspectiveTransform(rect, dst)
        showinfo(message="Initialisation du vidéoprojecteur réussie.")

        with open(hardware_json_path, "r") as file:
            setup_dict = json.load(file)

        setup_dict["corregistration_array"] = corregistration_array.tolist()
        setup_dict["max_width"] = max_width
        setup_dict["max_height"] = max_height

        with open(hardware_json_path, "w") as f:
            json.dump(setup_dict, f, indent=4)

    else:

        # Grab a photo of the frame
        camera.get_image(tag)
        save_path = f"./{tag}.png"
        pict = cv2.imread(save_path)
        os.remove(save_path)

    # Uncomment the lines below to see the transformed image
    wrap = cv2.resize(
        cv2.warpPerspective(pict, corregistration_array, (max_width, max_height)),
        (proj_shape.width, proj_shape.height),
    )
    cv2.imwrite(save_path, wrap)


def coregistration_calibration(screen_resolution=(proj_shape.width, proj_shape.height)):
    """
    Function allow to calibrate teh coregistration between video projector and the PI camera

    """
    screenWidth, proj_shape = get_display_configuration()
    reference_image = get_reference_image(screen_resolution)
    show_full_frame(reference_image)
    # Delay execution a quarter of a second to make sure the image is displayed
    # Don't use time.sleep() here, we want the IO loop to run.  Sleep doesn't do that
    gui_thread.run(cv2.waitKey, 500)

    # Grab a photo of the frame
    save_path = "init.png"

    camera.get_image("calibration", save_path)
    
    frame = cv2.imread(save_path)
    os.remove(save_path)

    # We're going to work with a smaller image, so we need to save the scale
    ratio = frame.shape[0] / 300.0

    # Undistort the camera image
    # frame = undistort_image(frame, prop_file=prop_file)
    pict = frame.copy()
    # Resize our image smaller, this will make things a lot faster
    frame = imutils.resize(frame, height=300)
    """"
    try:
        rect = get_region_corners(frame)
    except AttributeError:
        print("Lancement de la coregistration manuelle")
    """
    rect = manual_get_region_corners(frame)

    rect *= ratio  # We shrank the image, so now we have to scale our points up

    dst, max_width, max_height = get_destination_array(rect)
    # Remove the reference image from the display
    hide_full_frame()

    corregistration_array = cv2.getPerspectiveTransform(rect, dst)

    with open(hardware_json_path, "r") as file:
        setup_dict = json.load(file)

    setup_dict["corregistration_array"] = corregistration_array.tolist()
    setup_dict["max_width"] = max_width
    setup_dict["max_height"] = max_height

    with open(hardware_json_path, "w") as file:
        json.dump(setup_dict, file, indent=4)


def capture_calibration_photo(screen_resolution=(proj_shape.width, proj_shape.height)):
    """
    Project the white reference pattern and photograph it - camera and
    projector interaction only, no local display/click interaction.
    Pairs with save_coregistration_from_corners(): together they let
    the corner-clicking happen in a browser instead of a local
    matplotlib window, so this calibration doesn't need physical
    access to this machine's own screen - see
    coregistration_calibration() above for the original, fully
    interactive, local-display version this is an alternative route
    to the same result, not a replacement for it.
    """
    reference_image = get_reference_image(screen_resolution)
    show_full_frame(reference_image)
    # Delay execution so the projector has time to actually display the
    # pattern before the photo is taken - see coregistration_calibration()
    # above for why this isn't a time.sleep() call.
    gui_thread.run(cv2.waitKey, 500)

    save_path = "calibration_capture.png"
    camera.get_image("calibration", save_path)
    frame = cv2.imread(save_path)
    os.remove(save_path)

    hide_full_frame()

    return frame


def save_coregistration_from_corners(frame, corners):
    """
    corners: 4 (x, y) pixel points in frame's own pixel coordinates -
    any order; order_corners() below sorts them into top-left,
    top-right, bottom-right, bottom-left itself, the same as it
    already does for the interactive flow's clicks. Computes and
    saves corregistration_array exactly like
    coregistration_calibration() does, just from points collected
    some other way (a browser-side click UI) instead of a local
    plt.ginput() window.
    """
    points = np.asarray(corners, dtype="float32")

    if points.shape != (4, 2):
        raise ValueError(
            f"Expected exactly 4 (x, y) points, got shape {points.shape}."
        )

    height, width = frame.shape[:2]

    if not np.all(
        (points[:, 0] >= 0) & (points[:, 0] <= width)
        & (points[:, 1] >= 0) & (points[:, 1] <= height)
    ):
        raise ValueError(
            "One or more points fall outside the captured photo "
            f"({width}x{height})."
        )

    rect = order_corners(points)

    dst, max_width, max_height = get_destination_array(rect)

    corregistration_array = cv2.getPerspectiveTransform(rect, dst)

    with open(hardware_json_path, "r") as file:
        setup_dict = json.load(file)

    setup_dict["corregistration_array"] = corregistration_array.tolist()
    setup_dict["max_width"] = max_width
    setup_dict["max_height"] = max_height

    with open(hardware_json_path, "w") as file:
        json.dump(setup_dict, file, indent=4)


def apply_corregistration(img):
    """
    Function allow to resize image of the pi with coregistration with the video projector
    """

    with open(hardware_json_path) as f:
        setup_dict = json.load(f)
    corregistration_array = setup_dict["corregistration_array"]
    corregistration_array = np.asarray(corregistration_array)

    if corregistration_array.tolist() != []:
        # These used to be hardcoded to 619x719 regardless of what the
        # calibration actually computed and saved alongside
        # corregistration_array (get_destination_array()'s max_width/
        # max_height, sized to the actual clicked/detected projection
        # area - see coregistration_calibration() and
        # save_coregistration_from_corners()). warpPerspective's output
        # canvas has to match the size that transform was built for, or
        # the warped image only fills part of it (correctly transformed
        # content in one corner, the rest blank) before the final
        # resize stretches that mismatch across the full frame - which
        # is exactly what a wrong fixed size here produces.
        max_width = setup_dict.get("max_width")
        max_height = setup_dict.get("max_height")

        if not max_width or not max_height:
            raise RuntimeError(
                "corregistration_array is set but max_width/max_height "
                "are missing from hardware_config.json - recalibrate "
                "the coregistration."
            )

        wrap = cv2.resize(
            cv2.warpPerspective(img, corregistration_array, (max_width, max_height)),
            (proj_shape.width, proj_shape.height),
        )
    else:
        wrap = img
    return wrap
