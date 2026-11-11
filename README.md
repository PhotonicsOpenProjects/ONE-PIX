<p align="center">
<img src="imgs/logo.png" alt="logo" width="200"/>
</p>

# ONE-PIX

<p align="center">
Open-source modular hyperspectral single-pixel imaging ecosystem
</p>

<p align="center">
Acquisition • Reconstruction • Spectral Analysis • Plugin-Based Architecture
</p>

---

<p align="center">
<a href="https://one-pix.readthedocs.io/">Documentation</a> •
<a href="https://github.com/PhotonicsOpenProjects/ONE-PIX/wiki">Wiki</a> •
<a href="https://github.com/PhotonicsOpenProjects/ONE-PIX">GitHub</a> •
<a href="https://github.com/PhotonicsOpenProjects/ONE-PIX/issues">Issues</a>
</p>

## Introduction

The ONE-PIX project is an open-source hyperspectral camera based on single-pixel imaging principles. It enables the acquisition of hyperspectral datacubes in the visible range and can be extended toward infrared wavelengths depending on the hardware configuration.

Designed as a highly modular ecosystem, ONE-PIX supports multiple imaging methods, spectrometers, cameras and processing workflows through a plugin-based architecture. The project aims to provide an extensible platform for research, education and experimentation around computational imaging and hyperspectral acquisition.

The ONE-PIX ecosystem can be used for:

- hyperspectral imaging research
- computational imaging experiments
- rapid prototyping of custom imaging systems
- teaching and discovery of single-pixel imaging
- low-cost hyperspectral acquisition
- development of custom spectral processing pipelines

The project was originally developed to remain accessible and reproducible using affordable hardware and open-source software. It can run on Raspberry Pi devices for embedded acquisitions or on standard computers for higher performance workflows and advanced processing pipelines.

To learn more about the single-pixel imaging theory used for hyperspectral imaging, you can read our [article](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7070961/).

### Working principle

The ONE-PIX system uses a video projector and a single-pixel detector such as a spectrometer with superimposed fields of view.

<p align="center">
<img src="imgs/principle.png" alt="ONE-PIX principle" width="500"/>
</p>

During acquisition, a sequence of structured light patterns is projected onto the scene. For each projected pattern, the detector measures the integrated reflected spectrum of the scene. Reconstruction algorithms then recover the spatial and spectral information from these measurements to generate a hyperspectral datacube.

The acquisition workflow is orchestrated by the ONE-PIX core framework, while imaging methods, hardware drivers and analysis pipelines can be extended independently through the modular plugin ecosystem.


## Quick Installation

### Requirements

ONE-PIX is installed from a clone of this repository (below): the configuration
(`conf/`) and the applications (`app/`) live next to the `onepix` package and are
not part of what `pip` builds, so `pip install onepix` alone does not give a
working installation.

`onepix` requires Python 3.9 or later. Release 3.0.0 was tested with Python 3.11 on Windows.

Make sure you are using `pip >= 21.0` to install dependencies correctly.

### Clone the repository

```bash
git clone https://github.com/PhotonicsOpenProjects/ONE-PIX.git
cd ONE-PIX
```

### Create a Python environment (recommended)

Linux / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
```

In PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

### Install ONE-PIX

```bash
python install.py
```

The installation script automatically detects the current platform and installs the appropriate dependencies and hardware configuration.

On standard desktop systems (Windows/Linux/macOS), the installer deploys:

- the ONE-PIX core framework
- default imaging methods
- analysis pipeline dependencies
- scientific Python packages

On Raspberry Pi systems, the installer additionally configures the embedded acquisition environment required for hardware operation, including:

- OpenCV system dependencies
- USB and spectrometer communication
- display and projector management
- embedded acquisition configuration

For more information about Raspberry Pi hardware setup and acquisition configuration, please refer to the dedicated installation guides and wiki documentation.


## Quick Usage

### Launch the graphical interface

The easiest way to use ONE-PIX is through the Flask-based graphical interface.

From the root repository directory, launch the GUI with:

```bash
python app/GUI/flask/run.py
```

The graphical interface provides access to:

- hyperspectral acquisitions
- reconstruction workflows
- hardware configuration
- imaging method selection
- spectral analysis tools

### Run as a systemd service on Raspberry Pi

After installing dependencies, run from the repository root (also works over SSH):

```bash
bash install/install_service.sh
# Or select the Python environment explicitly:
bash install/install_service.sh "$PWD/.venv/bin/python"
```

The script requests sudo, adapts `install/onepix.service` to the current user,
repository location and selected Python, installs it in
`/etc/systemd/system/onepix.service`, enables startup at boot and restarts it.
Run as your application user, with the usual Python environment activated.
From the `install` directory, use `bash install_service.sh`.
Stop any manually launched instance first to free port 5000. A previous user
service is disabled automatically when running the installer without sudo.

```bash
sudo systemctl status onepix
sudo journalctl -u onepix -f
sudo systemctl restart onepix
sudo systemctl stop onepix
sudo systemctl disable --now onepix
```

The installer also creates `/etc/default/onepix` (readable by root only) with
`ONEPIX_HOST=0.0.0.0` and a random `ONEPIX_WEB_TOKEN`, and prints the token once:
the web interface can start acquisitions and change the configuration, so it
asks for that token (see [Network access and security](#network-access-and-security)).

Installation does not require DISPLAY in the terminal. The service sets
`DISPLAY=:0`; ONE-PIX still detects screens at import time, so runtime requires
an accessible graphical display. If necessary, adjust DISPLAY and XAUTHORITY
with `sudo systemctl edit onepix`, then restart the service.
The app runs its existing Flask server on port 5000 with debug disabled.


---

### Python API

Advanced users can directly interact with the ONE-PIX Python API to build custom acquisition, reconstruction and analysis workflows.

```python
from onepix.Acquisition import Acquisition
from onepix.Reconstruction import Reconstruction
from onepix.Analysis import Analysis

# Acquisition
acq = Acquisition(
    imaging_method_name="has"
)

acq.thread_acquisition()

# Reconstruction
rec = Reconstruction(
    acquisition_dict=acq.acquisition_results
)

rec.data_reconstruction()

# Analysis
ana = Analysis(
    reconstruction_dict=rec.reconstruction_results
)

ana.data_analysis()
```

More complete acquisition and analysis workflows are available in:

- `app/python_code_examples/`
- the API documentation
- the project wiki

## ONE-PIX Central Framework

The ONE-PIX repository is the central framework of the ecosystem. It provides the core orchestration layer used to manage hyperspectral acquisitions, reconstructions and analysis workflows independently from the underlying hardware or imaging methods.

The core framework is responsible for:

- acquisition workflow orchestration
- reconstruction workflow management
- analysis pipeline integration
- hardware abstraction
- imaging method management
- configuration handling
- graphical interface integration
- plugin interoperability

ONE-PIX is designed around a modular architecture where imaging methods, hardware drivers and processing pipelines can evolve independently while remaining compatible through shared interfaces and standardized data structures.

The framework can operate on both embedded acquisition systems such as Raspberry Pi devices and standard desktop environments for advanced reconstruction and spectral processing workflows.

## Network access and security

The web interface can start acquisitions, rewrite the hardware configuration,
read and delete measurements and install plugins. It therefore listens on this
machine only (`127.0.0.1:5000`) unless you open it explicitly:

| Variable | Role |
|---|---|
| `ONEPIX_HOST` | Address to listen on. Default `127.0.0.1`. Use `0.0.0.0` to reach it from another machine. |
| `ONEPIX_PORT` | Port. Default `5000`. |
| `ONEPIX_WEB_TOKEN` | Shared secret. **Required** when `ONEPIX_HOST` is not a loopback address: the server refuses to start without it. When set, every request must carry it. |
| `ONEPIX_WS_TOKEN` | Shared secret of the Socket.IO server (`app/websocket_server`), which refuses every connection without it. |
| `ONEPIX_WS_CORS_ORIGINS` | Browser origins allowed to reach the Socket.IO server. None by default. |
| `FLASK_DEBUG` | `1` enables Flask's debugger. Never on a shared network. |

```bash
export ONEPIX_HOST=0.0.0.0
export ONEPIX_WEB_TOKEN=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
python app/GUI/flask/run.py
```

A browser is sent to a sign-in page and keeps a `SameSite=Strict` session
cookie; scripts send `Authorization: Bearer <token>`. The interface does not
use HTTPS: on an untrusted network, put it behind a reverse proxy that does, or
use an SSH tunnel. See [SECURITY.md](SECURITY.md) to report a vulnerability.

## Ecosystem Architecture

| Component | Role |
|---|---|
| [ONE-PIX](https://github.com/PhotonicsOpenProjects/ONE-PIX) | Central framework orchestrating acquisition, reconstruction and analysis workflows |
| [onepix_plugins](https://gitlab.com/photonics-open-projects/onepix_plugins) | Main plugin ecosystem containing imaging methods, spectrometers, RGB cameras and analysis plugin families |
| [onepix_plugins_manager](https://gitlab.com/photonics-open-projects/onepix_plugins_manager) | Command-line plugin installation and ecosystem management system |
| Imaging Method Plugins | Plugins implementing acquisition, reconstruction and analysis workflows for single-pixel imaging methods |
| Spectrometer Plugins | Plugins implementing spectrometer hardware interfaces |
| RGB Camera Plugins | Plugins implementing RGB and auxiliary camera interfaces |
| pipeline-analysis | Abstract spectral processing and analysis framework |
| Analysis Plugins | Spectral processing and machine learning plugin family compatible with the analysis pipeline ecosystem |

## Core Architecture

ONE-PIX is organized around a modular workflow architecture separating:

- hyperspectral acquisition
- image reconstruction
- spectral analysis
- hardware management
- imaging method integration

This architecture allows imaging methods, hardware interfaces and analysis workflows to evolve independently while remaining interoperable inside the ONE-PIX ecosystem.

The framework supports interchangeable spectrometers, RGB cameras and single-pixel imaging strategies through a modular plugin-based ecosystem.

### Repository Architecture

```text
ONE-PIX/
├── app/
├── onepix/
├── conf/
├── install/
├── autodoc/
├── imgs/
└── logs/
```

| Directory | Role |
|---|---|
| app/ | User-facing applications including the Flask GUI, Python API examples and remote control services |
| onepix/ | Central acquisition, reconstruction and analysis framework |
| conf/ | JSON configuration files for acquisition parameters, hardware setup and calibration data |
| install/ | Platform-specific installation scripts and dependencies |
| autodoc/ | Documentation generation sources |
| imgs/ | README and documentation assets |
| logs/ | Acquisition and execution logs |

## Documentation

The ONE-PIX ecosystem documentation is primarily available through the project Wiki.

The Wiki contains detailed guides and technical documentation for:

- hardware installation
- Raspberry Pi setup
- acquisition workflows
- imaging methods
- plugin development
- spectral analysis pipelines
- calibration procedures
- remote control interfaces
- troubleshooting
- advanced API usage

### Documentation Links

- [Project Wiki](https://github.com/PhotonicsOpenProjects/ONE-PIX/wiki)
- [API Documentation](https://one-pix.readthedocs.io/)
- [Issues & Support](https://github.com/PhotonicsOpenProjects/ONE-PIX/issues)

## Contributing

ONE-PIX is an open and modular ecosystem designed for experimentation, research and community-driven development.

Contributions are welcome at multiple levels of the ecosystem, including:

- new imaging methods
- spectrometer integrations
- RGB camera integrations
- spectral analysis plugins
- processing pipelines
- hardware improvements
- documentation and tutorials
- bug fixes and performance improvements

The plugin-based architecture allows contributors to develop and distribute independent packages without modifying the central ONE-PIX framework.

For contribution guidelines, plugin development and technical discussions, please refer to the project Wiki and GitHub Issues.
