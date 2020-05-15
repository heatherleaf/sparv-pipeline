"""Model-related util functions like reading and writing data."""

import gzip
import logging
import os
import pickle
import urllib.request
import zipfile

from sparv.core.paths import models_dir, pipeline_path

log = logging.getLogger(__name__)


def get_model_path(name: str):
    """Get full path to model file."""
    # Check if name includes path to models dir
    if models_dir in name:
        return name
    else:
        return pipeline_path / models_dir / name


def write_model_data(name, data):
    """Write arbitrary string data to models directory."""
    file_path = get_model_path(name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w") as f:
        f.write(data)
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    log.info("Wrote %d bytes: %s", len(data), file_path)


def read_model_data(name: str):
    """Read arbitrary string data from file in models directory."""
    file_path = get_model_path(name)

    with open(file_path, "r") as f:
        data = f.read()
    log.info("Read %d bytes: %s", len(data), name)
    return data


def write_model_pickle(name, data, protocol=-1):
    """Dump data to pickle file in models directory."""
    file_path = get_model_path(name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:
        pickle.dump(data, f, protocol=protocol)
    # Update file modification time even if nothing was written
    os.utime(file_path, None)
    log.info("Wrote %d bytes: %s", len(data), file_path)


def read_model_pickle(name: str):
    """Read pickled data from file in models directory."""
    file_path = get_model_path(name)

    with open(file_path, "rb") as f:
        data = pickle.load(f)
    log.info("Read %d bytes: %s", len(data), name)
    return data


def download_model(url: str, name: str):
    """Download file from url and save to modeldir/filename."""
    file_path = get_model_path(name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        urllib.request.urlretrieve(url, file_path)
        log.info("Successfully downloaded %s", file_path)
    except Exception as e:
        log.error("Download from %s failed", url)
        raise e


def unzip_model(zip_file: str):
    """Unzip zip_file inside modeldir."""
    file_path = get_model_path(zip_file)
    out_dir = os.path.dirname(file_path)
    with zipfile.ZipFile(file_path, "r") as z:
        z.extractall(out_dir)
    log.info("Successfully unzipped %s", file_path)


def ungzip_model(gzip_file: str, out: str):
    """Unzip gzip_file inside modeldir."""
    file_path = get_model_path(gzip_file)
    with gzip.open(file_path, "rb") as z:
        data = z.read()
        with open(out, "wb") as f:
            f.write(data)
    log.info("Successfully unzipped %s", out)


def remove_model_files(files: list, raise_errors: bool = False):
    """Remove files from disk."""
    for f in files:
        file_path = get_model_path(f)
        try:
            os.remove(file_path)
        except FileNotFoundError as e:
            if raise_errors:
                raise e
