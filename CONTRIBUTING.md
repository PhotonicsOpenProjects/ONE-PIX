# Contributing to ONE-PIX

Thank you for helping. ONE-PIX is a hyperspectral single-pixel imaging framework
that drives hardware (projector, spectrometer, camera); most contributions are
imaging methods, hardware plugins, analysis, documentation and bug fixes.

By taking part you agree to follow the [code of conduct](CODE_OF_CONDUCT.md).

**Questions, bugs and ideas: please use GitHub issues**, so that the answers help
everyone. Write to community@photonics-open-projects.com only for what has to stay private: a security problem
(see [SECURITY.md](SECURITY.md), and do not describe it in a public issue) or a
conduct concern.

## Set up

```bash
git clone https://github.com/PhotonicsOpenProjects/ONE-PIX.git
cd ONE-PIX
python -m venv .venv && source .venv/bin/activate
python install.py          # or: pip install -e . pytest
python app/GUI/flask/run.py
```

Python 3.9 or later. ONE-PIX is run from a clone: `conf/` and `app/` are not part
of the pip package. On a Raspberry Pi, `install/install_rpi.sh` installs the
system packages (see the README).

## Run the tests

```bash
python -m pytest test
```

No hardware is needed: the tests use the stub spectrometer and camera plugins.
A few tests (`acquisition_test.py`, `acquisition_hardware_routes_test.py`,
`hardware_tuning_test.py`) open OpenCV windows for the projection and need a
display (`xvfb-run -a python -m pytest ...` on a server).

When you fix a bug, add the test that fails without the fix. When you add a
setting, give it a label and a help text in `app/GUI/flask/i18n.py` for the
four languages (en, fr, es, de).

## Plugins

Imaging methods, spectrometers, cameras and analysis pages are separate Python
packages found through entry points (`onepix.imaging_methods`,
`onepix.spectrometers`, `onepix.cameras`, `onepix.analysis_pages`). Most
contributions belong in a plugin repository rather than here; the project wiki
describes how to write one.

## Pull requests

- One change per pull request, with a message that says what changes and why
  (imperative mood, e.g. "Close the spectrometer after each acquisition").
- The tests pass, including the ones you added.
- Do not commit measurements, logs, `.orig` backups, bytecode or personal
  configuration (`measure/`, `logs/` and `conf/fair_config.json` are ignored).
- Note incompatible changes (a renamed setting, a changed file format) in
  `CHANGELOG.md`.
