"""Export ONE-PIX results as FAIR data packages in open formats.

A result saved by ONE-PIX (measure/*.json) is exported as a folder:

    <name>/
        <name>.h5            HDF5   - self-describing, dimension scales, all metadata as attributes
        <name>.npz           NumPy  - arrays + metadata_json (Python)
        <name>.mat           MATLAB - variables + metadata struct
        <name>.hdr + .img    ENVI   - the hyperspectral standard (QGIS, ENVI, SPy...)
        <name>.tif           TIFF   - ImageJ/Fiji hyperstack, one slice per wavelength
        <name>.json          the ONE-PIX file itself, unchanged
        ro-crate-metadata.json   machine-readable description (RO-Crate 1.1 / schema.org JSON-LD)
        README.md            human-readable description and how to open each file
        checksums.sha256     SHA-256 of every file (fixity)

Findable    a unique identifier, title, keywords and a JSON-LD description harvestable as is.
Accessible  open, documented formats; nothing needs ONE-PIX to be read.
Interoperable  units, axes and wavelengths are stored the standard way of each format.
Reusable    licence, author, instrument, acquisition parameters and software versions are included.
"""
import json
import logging
import math
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from onepix import fair, utils

logger = logging.getLogger(__name__)

EXPORTER = "onepix.export/1"
RO_CRATE_CONTEXT = "https://w3id.org/ro/crate/1.1/context"
RO_CRATE_SPEC = "https://w3id.org/ro/crate/1.1"


# ======================================================================
# data model
# ======================================================================
@dataclass
class Dataset:
    source: Path
    sha256: str
    raw: dict
    metadata: dict
    fair: dict
    cube: object = None                  # (rows, columns, bands) ndarray or None
    wavelengths: object = None           # (bands,) ndarray in nm, or None
    arrays: dict = field(default_factory=dict)       # every other ndarray of the result
    diagnostics: dict = field(default_factory=dict)  # every non-array entry of the result


def jsonable(obj):
    """`obj` made of JSON types only (arrays become lists, NaN/inf become null)."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return jsonable(obj.tolist())
    if isinstance(obj, np.generic):
        return jsonable(obj.item())
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


def load_dataset(path, config=None):
    """Read a ONE-PIX result file and gather what an export needs."""
    path = Path(path)
    config = config or fair.load_fair_config()
    sha = fair.sha256_file(path)
    raw = utils.load_dict_json(path)

    metadata = dict(raw.get("metadata") or {})
    fair_meta = metadata.pop("fair", None)
    if not fair_meta:
        # Saved before ONE-PIX recorded this: described with the current configuration, and an
        # identifier derived from the content so that exporting twice gives the same one.
        fair_meta = fair.fair_block(config, identifier=fair.identifier_from_content(sha))
        fair_meta["recorded_at"] = "export"
    # the licence/author of a data are the ones at acquisition; fill what it did not record
    fair_meta.setdefault("identifier", fair.identifier_from_content(sha))

    cube = raw.get("reconstructed_data")
    cube = cube if isinstance(cube, np.ndarray) and cube.ndim == 3 else None
    wavelengths = raw.get("wavelengths")
    wavelengths = np.asarray(wavelengths, dtype=float).ravel() if wavelengths is not None else None
    if cube is not None and (wavelengths is None or wavelengths.size != cube.shape[2]):
        wavelengths = None

    arrays, diagnostics = {}, {}
    for key, value in raw.items():
        if key in ("metadata", "reconstructed_data", "wavelengths"):
            continue
        if isinstance(value, np.ndarray):
            arrays[key] = value
        else:
            diagnostics[key] = jsonable(value)
    if cube is None and wavelengths is not None:
        arrays["wavelengths"] = wavelengths

    return Dataset(path, sha, raw, metadata, fair_meta, cube, wavelengths, arrays, diagnostics)


# ======================================================================
# description
# ======================================================================
def _created(ds):
    stamp = ds.metadata.get("acquisition_datetime")
    return stamp or datetime.fromtimestamp(ds.source.stat().st_mtime).isoformat(timespec="seconds")


def _method(ds):
    return ds.metadata.get("imaging_method_name") or ds.raw.get("imaging_method_name") or "unknown"


def _axes(ds):
    if ds.cube is None:
        return []
    return [
        {"name": "y", "size": int(ds.cube.shape[0]), "unit": "pixel"},
        {"name": "x", "size": int(ds.cube.shape[1]), "unit": "pixel"},
        {"name": "wavelength", "size": int(ds.cube.shape[2]), "unit": "nm"},
    ]


def title_of(ds):
    kind = "datacube" if ds.cube is not None else "result"
    return f"ONE-PIX {_method(ds)} {kind}, {_created(ds)}"


def description_of(ds):
    if ds.cube is not None:
        rows, cols, bands = ds.cube.shape
        wl = ""
        if ds.wavelengths is not None and ds.wavelengths.size:
            wl = f", {ds.wavelengths.min():.0f}-{ds.wavelengths.max():.0f} nm"
        return (
            f"Hyperspectral datacube of {rows} x {cols} pixels and {bands} spectral bands{wl}, "
            f"acquired by single-pixel imaging with the ONE-PIX instrument "
            f"(imaging method: {_method(ds)}). Values are the uncalibrated detector signal "
            f"(arbitrary units) reconstructed from the measured patterns."
        )
    return f"Result produced by the ONE-PIX instrument (imaging method: {_method(ds)})."


def describe(ds, fmt=None):
    """The complete description of a dataset, embedded in each format and used by the crate."""
    hardware = ds.metadata.get("hardware") or {}
    cube = ds.cube
    return jsonable({
        "schema": fair.SCHEMA,
        "identifier": ds.fair.get("identifier"),
        "title": title_of(ds),
        "description": description_of(ds),
        "created": _created(ds),
        "creator": ds.fair.get("creator"),
        "contact_email": ds.fair.get("contact_email"),
        "project": ds.fair.get("project"),
        "keywords": ds.fair.get("keywords"),
        "license": ds.fair.get("license"),
        "instrument": {
            "name": "ONE-PIX single-pixel hyperspectral imager",
            "spectrometer": hardware.get("spectrometer_name"),
            "spectrometer_device": hardware.get("spectrometer_device"),
            "camera": hardware.get("camera_name"),
            "imaging_method": _method(ds),
        },
        "data": {
            "quantity": "detector signal, uncalibrated (arbitrary units)",
            "dtype": str(cube.dtype) if cube is not None else None,
            "axes": _axes(ds),
            "wavelength_unit": "nm",
            "wavelength_range_nm": (
                [float(ds.wavelengths.min()), float(ds.wavelengths.max())]
                if ds.wavelengths is not None and ds.wavelengths.size else None
            ),
        },
        "acquisition": ds.metadata,
        "diagnostics": ds.diagnostics,
        "software": ds.fair.get("software"),
        "provenance": {
            "source_file": ds.source.name,
            "source_sha256": ds.sha256,
            "fair_metadata_recorded_at": ds.fair.get("recorded_at", "acquisition"),
        },
        "export": {"format": fmt, "exporter": EXPORTER, "datetime": datetime.now().isoformat(timespec="seconds")},
    })


# ======================================================================
# writers: each returns the list of files it wrote
# ======================================================================
def _write_hdf5(ds, out, base):
    import h5py
    path = out / f"{base}.h5"
    doc = describe(ds, "hdf5")
    with h5py.File(path, "w") as f:
        f.attrs["title"] = doc["title"]
        f.attrs["description"] = doc["description"]
        f.attrs["identifier"] = doc["identifier"] or ""
        f.attrs["created"] = doc["created"]
        f.attrs["license"] = (doc["license"] or {}).get("id", "")
        f.attrs["license_url"] = (doc["license"] or {}).get("url", "")
        f.attrs["creator"] = ((doc["creator"] or {}).get("name") or "")
        f.attrs["imaging_method"] = _method(ds)
        f.attrs["onepix_version"] = (doc["software"] or {}).get("onepix") or ""
        f.attrs["conventions"] = "ONE-PIX FAIR export; HDF5 dimension scales for the axes"
        f.attrs["metadata_json"] = json.dumps(doc, ensure_ascii=False)

        if ds.cube is not None:
            cube = f.create_dataset(
                "datacube", data=ds.cube, compression="gzip", compression_opts=4,
                chunks=(min(32, ds.cube.shape[0]), min(32, ds.cube.shape[1]), ds.cube.shape[2]),
            )
            cube.attrs["long_name"] = "reconstructed hyperspectral datacube"
            cube.attrs["units"] = "arbitrary units (uncalibrated detector signal)"
            cube.attrs["dimension_names"] = ["y", "x", "wavelength"]
            y = f.create_dataset("y", data=np.arange(ds.cube.shape[0]))
            x = f.create_dataset("x", data=np.arange(ds.cube.shape[1]))
            for scale, name in ((y, "y"), (x, "x")):
                scale.make_scale(name)
                scale.attrs["units"] = "pixel"
            cube.dims[0].attach_scale(y)
            cube.dims[1].attach_scale(x)
            if ds.wavelengths is not None:
                wl = f.create_dataset("wavelength", data=ds.wavelengths)
                wl.make_scale("wavelength")
                wl.attrs["units"] = "nm"
                wl.attrs["long_name"] = "wavelength"
                cube.dims[2].attach_scale(wl)
            for i, label in enumerate(("y", "x", "wavelength")):
                cube.dims[i].label = label

        if ds.arrays:
            group = f.create_group("arrays")
            for name, array in ds.arrays.items():
                group.create_dataset(name, data=array, compression="gzip" if array.size > 1024 else None)
        diag = f.create_group("diagnostics")
        for key, value in ds.diagnostics.items():
            if value is None:
                continue
            diag.attrs[key] = value if isinstance(value, (str, int, float, bool)) else json.dumps(value)
    return [path]


def _write_npz(ds, out, base):
    path = out / f"{base}.npz"
    doc = describe(ds, "npz")
    payload = {}
    if ds.cube is not None:
        payload["datacube"] = ds.cube
    if ds.wavelengths is not None:
        payload["wavelengths_nm"] = ds.wavelengths
    for name, array in ds.arrays.items():
        payload.setdefault(name, array)
    payload["metadata_json"] = np.array(json.dumps(doc, ensure_ascii=False))
    np.savez_compressed(path, **payload)
    return [path]


def _matlab_safe(obj):
    """`obj` in a shape scipy.io.savemat writes as a struct: valid field names, no None."""
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            name = re.sub(r"\W", "_", str(key))
            name = (name if re.match(r"[A-Za-z]", name) else f"f_{name}")[:63]
            out[name] = _matlab_safe(value)
        return out
    if obj is None:
        return np.array([])
    if isinstance(obj, bool):
        return np.array(obj)
    if isinstance(obj, (list, tuple)):
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in obj):
            return np.array(obj, dtype=float)
        return json.dumps(obj, ensure_ascii=False)
    return obj


def _write_mat(ds, out, base):
    from scipy.io import savemat
    path = out / f"{base}.mat"
    doc = describe(ds, "mat")
    variables = {}
    if ds.cube is not None:
        variables["datacube"] = ds.cube
    if ds.wavelengths is not None:
        variables["wavelengths_nm"] = ds.wavelengths
    for name, array in ds.arrays.items():
        key = re.sub(r"\W", "_", name)
        variables.setdefault(key if re.match(r"[A-Za-z]", key) else f"v_{key}", array)
    variables["metadata"] = _matlab_safe(doc)
    variables["metadata_json"] = json.dumps(doc, ensure_ascii=False)
    savemat(path, variables, do_compression=True, oned_as="column", long_field_names=True)
    return [path]


def _write_envi(ds, out, base):
    if ds.cube is None:
        raise ValueError("no datacube in this result")
    from spectral import envi
    hdr = out / f"{base}.hdr"
    doc = describe(ds, "envi")
    metadata = {
        "description": f"{doc['title']}. {doc['description']}".replace("{", "(").replace("}", ")"),
        "sensor type": f"ONE-PIX ({doc['instrument']['spectrometer'] or 'spectrometer'})",
        "acquisition time": doc["created"],
        "identifier": doc["identifier"] or "",
        "license": (doc["license"] or {}).get("id", ""),
        "data units": "arbitrary units",
    }
    if ds.wavelengths is not None:
        metadata["wavelength"] = [float(w) for w in ds.wavelengths]
        metadata["wavelength units"] = "Nanometers"
    envi.save_image(str(hdr), ds.cube.astype(np.float32, copy=False), dtype=np.float32,
                    interleave="bip", metadata=metadata, force=True, ext=".img")
    return [hdr, out / f"{base}.img"]


def _write_tiff(ds, out, base):
    if ds.cube is None:
        raise ValueError("no datacube in this result")
    import tifffile
    path = out / f"{base}.tif"
    stack = np.moveaxis(ds.cube.astype(np.float32, copy=False), 2, 0)      # (bands, rows, columns)
    metadata = {"axes": "ZYX"}
    if ds.wavelengths is not None:
        metadata["Labels"] = [f"{w:.1f} nm" for w in ds.wavelengths]
    tifffile.imwrite(path, stack, imagej=True, metadata=metadata)
    return [path]


def _write_json(ds, out, base):
    path = out / f"{base}.json"
    shutil.copyfile(ds.source, path)
    return [path]


# id -> (label, extension(s), writer, python module needed, mime, how to open)
FORMATS = {
    "hdf5": ("HDF5", ".h5", _write_hdf5, "h5py", "application/x-hdf5"),
    "npz": ("NumPy (Python)", ".npz", _write_npz, None, "application/octet-stream"),
    "mat": ("MATLAB", ".mat", _write_mat, "scipy", "application/x-matlab-data"),
    "envi": ("ENVI (.hdr + .img)", ".hdr, .img", _write_envi, "spectral", "application/octet-stream"),
    "tiff": ("TIFF stack (ImageJ / Fiji)", ".tif", _write_tiff, "tifffile", "image/tiff"),
    "json": ("ONE-PIX JSON (original)", ".json", _write_json, None, "application/json"),
}
NEEDS_CUBE = {"envi", "tiff"}
MIME = {".hdr": "text/plain", ".img": "application/octet-stream", ".md": "text/markdown",
        ".sha256": "text/plain"}


def available_formats():
    """The formats, with whether the library each needs is installed (for the interface)."""
    import importlib.util
    out = []
    for fmt, (label, ext, _, module, _mime) in FORMATS.items():
        ok = module is None or importlib.util.find_spec(module) is not None
        out.append({"id": fmt, "label": label, "extension": ext, "available": ok,
                    "needs_datacube": fmt in NEEDS_CUBE})
    return out


# ======================================================================
# package: README, RO-Crate, checksums
# ======================================================================
HOW_TO_OPEN = {
    "hdf5": ("Python (h5py)",
             "import h5py\nwith h5py.File('{f}', 'r') as f:\n    cube = f['datacube'][:]            # rows x columns x bands\n"
             "    wavelengths = f['wavelength'][:]   # nm\n    print(f.attrs['metadata_json'])"),
    "npz": ("Python (NumPy)",
            "import numpy as np, json\nd = np.load('{f}')\ncube, wl = d['datacube'], d['wavelengths_nm']\n"
            "metadata = json.loads(str(d['metadata_json']))"),
    "mat": ("MATLAB",
            "d = load('{f}');\ncube = d.datacube;        % rows x columns x bands\nwl = d.wavelengths_nm;   % nm\nd.metadata"),
    "envi": ("Python (SPy) - also QGIS, ENVI, Spectronon",
             "import spectral\nimg = spectral.open_image('{f}')   # the .hdr file; the .img is next to it\ncube = img.load()"),
    "tiff": ("ImageJ / Fiji", "File > Open the .tif: one slice per wavelength (the slice label gives it)."),
    "json": ("Python (ONE-PIX)", "from onepix import utils\nresult = utils.load_dict_json('{f}')"),
}


def _readme(ds, doc, files, skipped):
    lines = [f"# {doc['title']}", "", doc["description"], "",
             f"- **Identifier**: `{doc['identifier']}` (unique, but not a DOI: deposit the data in a repository, e.g. Zenodo, to get a persistent one)",
             f"- **Acquired**: {doc['created']}",
             f"- **Instrument**: {doc['instrument']['name']}"
             + (f", spectrometer {doc['instrument']['spectrometer']}" if doc['instrument']['spectrometer'] else "")
             + (f", camera {doc['instrument']['camera']}" if doc['instrument']['camera'] else ""),
             f"- **Imaging method**: {doc['instrument']['imaging_method']}"]
    creator = (doc.get("creator") or {})
    lines.append(f"- **Author**: {creator.get('name') or 'not specified'}"
                 + (f" ({creator['affiliation']})" if creator.get("affiliation") else "")
                 + (f" - {creator['orcid']}" if creator.get("orcid") else ""))
    lic = doc.get("license") or {}
    lines.append(f"- **Licence**: {lic.get('id', 'not specified')} {lic.get('url', '')}".rstrip())
    sw = doc.get("software") or {}
    lines.append(f"- **Produced with**: ONE-PIX {sw.get('onepix')}, Python {sw.get('python')}")
    if doc["provenance"]["fair_metadata_recorded_at"] == "export":
        lines.append("- **Note**: this measurement was saved before ONE-PIX recorded the author and licence; "
                     "they are the ones configured when it was exported, and the software versions are those "
                     "installed at that time.")
    if doc["data"]["axes"]:
        lines += ["", "## Data", "", "| axis | size | unit |", "|---|---|---|"]
        lines += [f"| {a['name']} | {a['size']} | {a['unit']} |" for a in doc["data"]["axes"]]
        lines += ["", f"Quantity: {doc['data']['quantity']}."]
    lines += ["", "## Files", ""]
    lines += [f"- `{f}`" for f in files]
    lines += ["", "`ro-crate-metadata.json` describes all of them in a machine-readable way (RO-Crate 1.1, "
                  "schema.org JSON-LD); `checksums.sha256` lets you verify them (`sha256sum -c checksums.sha256`).",
              "The complete acquisition parameters and the software versions are stored in each data file "
              "(`metadata_json`) and in the ONE-PIX JSON."]
    if skipped:
        lines += ["", "Not exported: " + ", ".join(f"{k} ({v})" for k, v in skipped.items())]
    lines += ["", "## How to open", ""]
    for fmt, files_of_fmt in _by_format(files).items():
        if fmt in HOW_TO_OPEN:
            title, code = HOW_TO_OPEN[fmt]
            lines += [f"### {title}", "", "```", code.format(f=files_of_fmt), "```", ""]
    return "\n".join(lines) + "\n"


def _by_format(files):
    ext = {".h5": "hdf5", ".npz": "npz", ".mat": "mat", ".hdr": "envi", ".tif": "tiff", ".json": "json"}
    out = {}
    for f in files:
        fmt = ext.get(Path(f).suffix)
        if fmt and not f.startswith("ro-crate"):
            out[fmt] = f
    return out


def _ro_crate(ds, doc, files, out):
    license_ = doc.get("license") or {}
    creator = doc.get("creator") or {}
    graph = [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
         "conformsTo": {"@id": RO_CRATE_SPEC}, "about": {"@id": "./"}},
    ]
    root = {
        "@id": "./", "@type": "Dataset",
        "name": doc["title"], "description": doc["description"],
        "identifier": doc["identifier"],
        "datePublished": datetime.now().date().isoformat(),
        "dateCreated": doc["created"],
        "keywords": doc.get("keywords") or [],
        "measurementTechnique": f"single-pixel hyperspectral imaging ({doc['instrument']['imaging_method']})",
        "instrument": doc["instrument"]["name"],
        "variableMeasured": doc["data"]["quantity"],
        "hasPart": [{"@id": f} for f in files],
    }
    if license_.get("url"):
        root["license"] = {"@id": license_["url"]}
        graph.append({"@id": license_["url"], "@type": "CreativeWork", "name": license_.get("id")})
    if creator.get("name"):
        person_id = creator.get("orcid") or "#creator"
        root["creator"] = {"@id": person_id}
        person = {"@id": person_id, "@type": "Person", "name": creator["name"]}
        if creator.get("affiliation"):
            person["affiliation"] = creator["affiliation"]
        if doc.get("contact_email"):
            person["email"] = doc["contact_email"]
        graph.append(person)
    if doc.get("project"):
        root["isPartOf"] = doc["project"]
    graph.insert(1, root)
    for name in files:
        path = out / name
        graph.append({
            "@id": name, "@type": "File", "name": name,
            "encodingFormat": MIME.get(path.suffix) or next(
                (m for _, (_l, e, _w, _mod, m) in FORMATS.items() if path.suffix in e.split(", ")), "application/octet-stream"),
            "contentSize": str(path.stat().st_size),
            "sha256": fair.sha256_file(path),
        })
    return {"@context": RO_CRATE_CONTEXT, "@graph": graph}


def export_dataset(source, formats, out_root, config=None):
    """Export the result file `source` in each of `formats`, as a package folder under `out_root`.

    Returns {"folder": Path, "files": [names], "skipped": {format: reason}}. A format that cannot be
    produced (library missing, no datacube for ENVI/TIFF) is reported in "skipped" and does not stop
    the others."""
    ds = load_dataset(source, config)
    base = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(source).stem)
    folder = Path(out_root) / base
    folder.mkdir(parents=True, exist_ok=True)

    written, skipped = [], {}
    for fmt in formats:
        if fmt not in FORMATS:
            skipped[fmt] = "unknown format"
            continue
        label, _ext, writer, _module, _mime = FORMATS[fmt]
        try:
            written += [p.name for p in writer(ds, folder, base)]
        except ImportError as exc:
            skipped[fmt] = f"library missing ({exc.name})"
        except ValueError as exc:
            skipped[fmt] = str(exc)
        except Exception as exc:                      # a broken writer must not lose the others
            logger.exception("Export to %s failed", fmt)
            skipped[fmt] = f"failed: {exc}"

    doc = describe(ds, ",".join(f for f in formats if f not in skipped))
    (folder / "README.md").write_text(_readme(ds, doc, written, skipped), encoding="utf-8")
    written.append("README.md")
    (folder / "ro-crate-metadata.json").write_text(
        json.dumps(_ro_crate(ds, doc, written, folder), indent=2, ensure_ascii=False), encoding="utf-8")
    written.append("ro-crate-metadata.json")
    (folder / "checksums.sha256").write_text(
        "".join(f"{fair.sha256_file(folder / n)}  {n}\n" for n in written), encoding="utf-8")
    written.append("checksums.sha256")
    return {"folder": folder, "files": written, "skipped": skipped}
