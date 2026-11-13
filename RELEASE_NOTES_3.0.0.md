# ONE-PIX 3.0.0: a new base for hyperspectral imaging

**English** · [Français](docs/release_3.0.0/release_notes.fr.md) · [Español](docs/release_3.0.0/release_notes.es.md) · [Deutsch](docs/release_3.0.0/release_notes.de.md)

ONE-PIX 3.0.0 turns a set of desktop applications into a hyperspectral camera you drive from a browser, extend with plugins and whose data you reuse outside the project. Acquisition, reconstruction and analysis stay at the centre, with a web interface, a reorganised `onepix` Python core and independent plugins for imaging methods, hardware and analysis.

## Highlights

- **Web interface in 4 languages** (English, French, Spanish, German): acquisition, analysis, data, plugins, logs and hardware/software settings, with a dark mode and interactive spectra charts. Remote use of a headless Raspberry Pi.
- **Plugins installed from the interface.** Imaging methods, spectrometers, cameras and analysis pages are pip packages; a plugins manager installs, updates and removes them.
- **Analysis pipelines.** Chain processing steps (crop, smoothing, normalisation, spectral indices...), normalise to reflectance from a reference zone or a stored reference datacube, and keep the history of the steps in the metadata.
- **Cleaner measurements.** Live integration-time tuning with advice, per-pattern dynamic integration time, gray-level response linearisation, projector-to-camera coregistration calibration and HDMI-CEC projector control.
- **FAIR, reusable data.** Every acquisition records an identifier, author, licence and software versions; export to HDF5, NumPy, MATLAB, ENVI and TIFF stacks, as RO-Crate packages with SHA-256 checksums, for Python, MATLAB, QGIS or Fiji.
- **Smaller files.** Saved JSON measurements are 3 to 6 times smaller and load much faster, without loss.
- **Remote control.** A Socket.IO server with token authentication configures and starts measurements, for connected applications and IoT.

## Under the hood

`onepix` package installed with pip; plugin architecture discovered through entry points; more than 190 tests and a CI on three Python versions; logging; atomic configuration writes; unified installer (`install.py`) and a systemd service on Raspberry Pi.

## Fixes worth knowing

Thread deadlock between acquisition, projection and spectrometer; silent data loss when saving some arrays as JSON; write to a closed file in two hardware modules; Flask debug mode off by default; Socket.IO authentication; cross-site requests refused.

## Migrating from the previous version

1. Install the plugins you need: no imaging method is included in the repository any more.
2. Replace `core.*` by `onepix.*` in your scripts.
3. Use the web interface: the Tkinter applications are removed.
4. A program that reads the saved JSON without `onepix.utils` must use `ONEPIX_COMPACT_JSON=0`. Re-reading V2 result files has not been tested.

The web interface has no sign-in and listens on all interfaces: use it on a trusted network (see [SECURITY.md](SECURITY.md)).

Full details: [CHANGELOG.md](CHANGELOG.md).
