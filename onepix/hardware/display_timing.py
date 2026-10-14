"""Display timing helpers - refresh rate detection and the integration-time
floor it implies for a single-chip DLP projector with a spinning colour
filter wheel.

Why this matters
-----------------
A single-chip DLP projector doesn't hold a pattern's pixels at a constant
light level the way an LCD panel does. Colour is produced by spinning a
red/green/blue (sometimes +white/+cyan/+yellow) filter wheel in front of
one white lamp, and grey levels are produced by pulse-width-modulating the
DMD mirrors within each colour segment. So even a perfectly static pattern
is, physically, flickering at the wheel's rotation rate (commonly
2x-6x the input frame rate, i.e. very roughly 100-400 Hz, though the exact
figure is projector-model-specific and generally undocumented).

A spectrometer integration window shorter than one full wheel rotation
captures a random *slice* of that flicker rather than the pattern's true
time-averaged value - the slice depends on exactly when, relative to the
wheel's continuous, free-running rotation, the window happened to start,
which our software has no way to control or even observe directly. That
turns every measurement into a mix of the real signal and a essentially
random phase error, which shows up as extra pattern-to-pattern noise on
top of (and independent from) the stale-scan issue that
SpectrometerBridge.thread_singlepixel_measure() already guards against.

The fix doesn't require detecting or locking to the wheel's phase at all:
by construction, every full *input frame* period contains a whole number
of complete wheel rotations and DMD bit-plane sequences (a new frame's
grey levels have to finish their whole PWM sequence before the next frame
can start). So integrating for a few whole frame periods - regardless of
what phase that window starts at - always averages over a whole number of
full colour-wheel cycles, and the essentially-random starting phase stops
mattering.
"""

import logging
import os
import re
import subprocess

logger = logging.getLogger(__name__)


def get_refresh_rate_hz(default=60.0, timeout_s=2.0):
    """Best-effort detection of the currently active display mode's
    refresh rate via `xrandr` (X11), e.g. so the recommended minimum
    integration time can be based on how this projector is actually being
    driven rather than an assumed 60 Hz.

    Never raises: falls back to `default` if xrandr isn't installed, the
    session isn't X11 (e.g. Wayland, or no display at all), or parsing
    fails for any reason - detection is a nice-to-have, not something
    that should be able to break acquisition startup.
    """

    try:
        env = dict(os.environ)
        env.setdefault("DISPLAY", ":0")

        result = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )

        # The line for the currently active mode is marked with a
        # trailing "*", e.g. "  1024x768      59.92*+". Take the first
        # one found - the active output is what we're actually
        # projecting through.
        match = re.search(r"(\d+\.\d+)\*", result.stdout)

        if match:
            return float(match.group(1))

        logger.warning(
            "get_refresh_rate_hz(): no active (*) mode found in xrandr "
            f"output, defaulting to {default} Hz"
        )

    except Exception as exc:
        logger.warning(
            f"get_refresh_rate_hz(): xrandr detection failed ({exc}), "
            f"defaulting to {default} Hz"
        )

    return default


def frame_period_ms(refresh_rate_hz=None):
    """Duration (ms) of one input frame at the given (or auto-detected)
    refresh rate - an upper bound on the projector's colour-wheel
    rotation period, since the wheel has to complete at least one full
    cycle within the time one frame is displayed."""

    if refresh_rate_hz is None:
        refresh_rate_hz = get_refresh_rate_hz()

    return 1000.0 / refresh_rate_hz


def recommended_min_integration_time_ms(refresh_rate_hz=None, frame_periods=3):
    """Minimum spectrometer integration time (ms) recommended to average
    out colour-wheel/DMD-PWM flicker regardless of its (unknown, free-
    running) phase: `frame_periods` whole input-frame periods.

    3 is a conservative default (comfortably covers projectors whose
    wheel spins slower than the frame rate, which shouldn't normally
    happen, while keeping the floor a matter of tens of ms, not
    hundreds). Use app/cli/probe_projection_frequency.py to measure the
    *actual* flicker period on a given projector and tune this down (or
    confirm it's already safe) instead of guessing.
    """

    return frame_periods * frame_period_ms(refresh_rate_hz)
