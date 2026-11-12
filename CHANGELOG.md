# Changelog

All notable changes to ONE-PIX are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses
[semantic versioning](https://semver.org/).

## [3.0.0] - unreleased

The first release since the V2 snapshot (`main`): ONE-PIX becomes an installable
`onepix` package with a web interface and plugins installed with pip.

### Added
- Web interface (Flask): Acquisition, Analysis, Data, Logs and Plugins pages, with
  Hardware and Software settings.
- Plugin architecture: imaging methods, spectrometers, cameras and analysis pages
  are pip packages found through entry points (`onepix.imaging_methods`,
  `onepix.spectrometers`, `onepix.cameras`, `onepix.analysis_pages`). A Plugins
  page installs, updates and removes them.
- Analysis page with chained processing steps, reflectance normalisation from a
  reference zone or a reference hypercube, zone segmentation tools and an
  optional spectral-indices page.
- Interactive spectra charts, dark mode, and four interface languages (English,
  French, Spanish, German).
- Projector-to-camera coregistration calibration (command line and browser).
- Live integration-time tuning with advice, and command-line probes for the
  projector (gray response, settle time, projection frequency).
- Gray-level response linearisation, a maximum gray level and early display of
  the next pattern.
- Projector HDMI-CEC panel (Hardware settings): power on, standby, bus scan and
  display information.
- Reference datacubes: acquire and store a reference measurement from Software
  settings > Normalisation.
- FAIR data: every acquisition records an identifier, author, licence and
  software versions (set in Data > FAIR metadata); Data > Export writes HDF5,
  NumPy, MATLAB, ENVI, TIFF stacks and the original JSON as RO-Crate packages
  with a README and SHA-256 checksums.
- Socket.IO server and Python client, with token authentication
  (`ONEPIX_WS_TOKEN`).
- Unified installer (`install.py`), Raspberry Pi installer and a systemd service.
- A test suite, a GitHub Actions workflow, and the community files (contributing
  guide, code of conduct, security policy, issue and pull request templates).
- `ONEPIX_SERVER=waitress` runs the web interface with waitress, a production server
  (`pip install "onepix[server]"`), instead of Flask's development server.

### Improved
- Dynamic integration time (`dynamic_tint`, Software settings): the time is
  re-tuned for every pattern, in whole numbers of display frames, and the dark is
  measured with the projector black and subtracted. The times used are saved as
  `integration_times_ms`.
- Measurement timing: pattern pacing with `perf_counter`, integration times in
  whole display frames, averaging inside the spectrometer when the plugin allows
  it, normalisation by the applied time.
- The spectrometer is closed after each acquisition and the projector display is
  looked up when projecting.
- A running measurement can be resumed when switching pages; progress and
  cancellation are shared by all pages.
- Settings pages: grouped fields, help texts, bounds (`max_gray_level` 1-255),
  preview of changes before saving.
- Configuration files are written atomically, and saving some settings keeps the
  others.
- Logging replaces `print`; acquisitions, reconstructions and analyses share one
  JSON format.
- Saved JSON files are 3 to 6 times smaller and load much faster: arrays of 1024 values
  or more are stored as base64 binary, without loss (a 81.6 MB measurement became 14.5 MB and
  loads in 0.2 s instead of 2.8 s). Files written before still load. A program that reads
  the files without `onepix.utils`, such as the command line of `onepix-spectral-indices`
  before its 0.1.2, needs `ONEPIX_COMPACT_JSON=0`.

### Fixed
- Thread deadlock between acquisition, projection and the spectrometer;
  acquisition synchronisation and timeouts.
- Closed-file write bug in two hardware modules; command-line scripts and four
  examples repaired.
- Coregistration ignoring the size saved by the calibration.
- A maximum gray level out of range no longer blacks out the patterns or stops the
  hardware initialisation.
- ENVI export failing with recent NumPy (`spectral` 0.22.4 is no longer pinned).
- `tkinter` is no longer required to import ONE-PIX (only the folder dialog of
  the Python API uses it).
- Saving settings with a request that carries only some of the keys no longer
  erases the others; an unknown settings category answers 404.
- Saving a result as JSON truncated to 8 bits any array shaped like an image that was
  not 8-bit: a float map larger than 64 x 64, or a cube of 1, 3 or 4 bands, came back
  as `uint8` values. Only 8-bit and boolean images are stored as PNG now; files
  already saved that way cannot be repaired.

### Security
- Path traversal closed on the data and analysis endpoints (`safe_path`).
- Flask debug mode off by default (`FLASK_DEBUG=1` to enable it).
- The Socket.IO server refuses connections without `ONEPIX_WS_TOKEN`, and
  measurements are serialised.
- File names are escaped before being inserted in pages.
- Requests that change something and that the browser reports as coming from
  another site are refused; uploads are limited to 1024 MB
  (`ONEPIX_MAX_UPLOAD_MB`).
- The web interface has no sign-in and listens on all interfaces: see
  [SECURITY.md](SECURITY.md).
- Responses carry `X-Frame-Options`, `Content-Security-Policy: frame-ancestors`,
  `X-Content-Type-Options` and `Referrer-Policy`; the language switch no longer redirects
  to another site.

### Changed
- Python 3.9 or later; the package is named `onepix`; licence CC-BY-NC-4.0.
- The `Normalisation` and `normalisation_path` settings are removed: they were only
  copied into the metadata. Older JSON files that contain them still load.
- ONE-PIX is installed from a clone of the repository: `conf/` and `app/` are not
  part of the pip package.
- `scikit-learn`, which ONE-PIX never imports, is no longer a dependency (the plugins
  that need it declare it); `Pillow`, which it does import, is declared.

### Removed
- `install/requirements.txt`, `install/rasp_requirements.txt` and `install/get_packages.py`: V2 leftovers
  (they listed `customtkinter` and other versions that contradicted `pyproject.toml`, the only
  source of the dependencies) that nothing in the repository used.

### Breaking Changes
- `core.*` is now `onepix.*`.
- Imaging methods, spectrometers and cameras are no longer in the repository:
  install them as plugins.
- The Tkinter applications are removed; use the web interface.
- The JSON result format changed; re-reading V2 files has not been tested.
