from onepix.hardware.display_timing import frame_multiple_hint


def test_whole_numbers_of_frames_are_accepted():
    for t in (16.667, 33.333, 50.0, 100.0):
        assert frame_multiple_hint(t, 60.0) is None
    assert frame_multiple_hint(33.3, 119.8) is None                 # 4 frames at 120 Hz too


def test_one_frame_is_accepted_whatever_the_detected_rate_is():
    # xrandr reports 59.92 Hz for a 60.004 Hz mode: one frame of it is 16.689 ms, 16.667 is one frame
    assert frame_multiple_hint(16.667, 59.92) is None
    assert frame_multiple_hint(33.333, 59.92) is None


def test_other_times_get_the_closest_whole_number_of_frames():
    assert frame_multiple_hint(30.0, 60.0) == 33.333
    assert frame_multiple_hint(40.0, 60.0) == 33.333
    assert frame_multiple_hint(45.0, 60.0) == 50.0
    assert frame_multiple_hint(5.0, 60.0) == 16.667                 # shorter than a frame: one frame
