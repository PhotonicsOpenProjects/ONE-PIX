"""FAIR metadata of ONE-PIX data (Findable, Accessible, Interoperable, Reusable).

What this module provides to the rest of ONE-PIX:

  * a user-editable configuration (conf/fair_config.json): who produced the data, under which
    licence, with which keywords - the descriptive metadata no instrument can know;
  * fair_block(): the "fair" entry written in the metadata of every acquisition (Acquisition.
    build_metadata), so that each saved measurement carries a unique identifier, its author, its
    licence and the exact versions of the software that produced it;
  * helpers used by onepix.export when the data are exported in an open format.

The identifier is a UUID (urn:uuid:...): unique and stable, but not a DOI. A persistent identifier
that resolves on the web only exists once the data are deposited in a repository (Zenodo, Recherche
Data Gouv...), which the export package is meant to be ready for.
"""
import hashlib
import json
import logging
import platform
import re
import sys
import uuid
from functools import lru_cache
from importlib import metadata as importlib_metadata
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA = "onepix-fair/1"
CONF_DIR = Path(__file__).resolve().parent.parent / "conf"
FAIR_CONFIG_PATH = CONF_DIR / "fair_config.json"

# Licences offered in the interface. The default is a suggestion: the data belong to whoever
# measured them, who should check it (Data manager > FAIR metadata).
LICENSES = {
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC-BY-NC-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "ODbL-1.0": "https://opendatacommons.org/licenses/odbl/1-0/",
}

DEFAULT_CONFIG = {
    "creator_name": "",
    "creator_orcid": "",
    "affiliation": "",
    "contact_email": "",
    "project": "",
    "keywords": ["hyperspectral imaging", "single-pixel imaging", "ONE-PIX"],
    "license": "CC-BY-4.0",
}

ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ----------------------------------------------------------------------
# configuration
# ----------------------------------------------------------------------
def load_fair_config(path=None):
    """The FAIR configuration: DEFAULT_CONFIG updated by conf/fair_config.json when it exists."""
    config = dict(DEFAULT_CONFIG)
    path = Path(path or FAIR_CONFIG_PATH)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                config.update(json.load(f))
        except (OSError, ValueError) as exc:
            logger.warning("FAIR configuration %s ignored: %s", path, exc)
    return config


def validate_config(values):
    """The configuration made of `values` (a dict, possibly partial), cleaned up; ValueError with
    a readable message when a field is not acceptable."""
    config = dict(DEFAULT_CONFIG)
    config.update({k: values[k] for k in DEFAULT_CONFIG if k in values})
    for key in ("creator_name", "creator_orcid", "affiliation", "contact_email", "project"):
        config[key] = str(config[key] or "").strip()
    if config["creator_orcid"] and not ORCID_RE.match(config["creator_orcid"]):
        raise ValueError("orcid")
    if config["contact_email"] and not EMAIL_RE.match(config["contact_email"]):
        raise ValueError("email")
    keywords = config["keywords"]
    if isinstance(keywords, str):
        keywords = keywords.split(",")
    config["keywords"] = [k.strip() for k in keywords if str(k).strip()]
    if config["license"] not in LICENSES:
        raise ValueError("license")
    return config


def save_fair_config(values, path=None):
    config = validate_config(values)
    path = Path(path or FAIR_CONFIG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return config


# ----------------------------------------------------------------------
# provenance
# ----------------------------------------------------------------------
@lru_cache(maxsize=1)
def software_versions():
    """Versions of what produced the data: Python, the platform, ONE-PIX and every installed
    ONE-PIX plugin (imaging methods, spectrometers, cameras...)."""
    plugins = {}
    for dist in importlib_metadata.distributions():
        name = dist.metadata["Name"] or ""
        if name.lower().startswith("onepix") or name.lower() in ("fis-common-function", "analysis-pipeline"):
            plugins[name] = dist.version
    onepix = plugins.pop("onepix", None)
    return {
        "onepix": onepix,
        "plugins": dict(sorted(plugins.items())),
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.machine()}",
    }


def new_identifier():
    """A new unique identifier for a measurement."""
    return f"urn:uuid:{uuid.uuid4()}"


def identifier_from_content(sha256_hex):
    """An identifier derived from the content of a file: exporting the same file twice gives the
    same identifier, which is what a data that was not given one at acquisition needs."""
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'onepix:sha256:' + sha256_hex)}"


def sha256_file(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def creator_block(config):
    creator = {"name": config["creator_name"] or None}
    if config["creator_orcid"]:
        creator["orcid"] = f"https://orcid.org/{config['creator_orcid']}"
    if config["affiliation"]:
        creator["affiliation"] = config["affiliation"]
    return creator


def fair_block(config=None, identifier=None):
    """The "fair" entry of an acquisition's metadata: who, which licence, which software, and an
    identifier. Written when the data are produced, so it describes the measurement as it was."""
    config = config or load_fair_config()
    return {
        "schema": SCHEMA,
        "identifier": identifier or new_identifier(),
        "creator": creator_block(config),
        "contact_email": config["contact_email"] or None,
        "project": config["project"] or None,
        "keywords": list(config["keywords"]),
        "license": {"id": config["license"], "url": LICENSES[config["license"]]},
        "software": software_versions(),
    }
