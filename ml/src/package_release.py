"""Package the three verified serving bundles and their evaluation reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path

import joblib

from ml.src.antenatal import CONTEXT, OUT
from ml.src.artifacts import validate_bundle
from ml.src.dataset import COHORTS


def package(destination: Path | None = None) -> None:
    files = []
    manifest = {"format_version": 1, "models": {}}
    for cohort in COHORTS:
        path = OUT / cohort / "selected.joblib"
        bundle = joblib.load(path)
        validate_bundle(bundle, cohort)
        report = json.loads(path.with_suffix(".json").read_text())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != report["sha256"]:
            raise ValueError(f"{cohort}: the exported artifact and report hashes differ.")
        manifest["models"][cohort] = {
            "sha256": digest,
            "target": bundle["target"],
            "algorithm": bundle["algorithm"],
            "prediction_context": bundle.get("prediction_context"),
            "contract_hash": bundle["contract_hash"],
        }
        files.extend([path, path.with_suffix(".json")])
        validation = path.parent / "country_validation.json"
        if validation.exists():
            files.append(validation)
    encoded = json.dumps(manifest, indent=2).encode()
    identifier = hashlib.sha256(encoded).hexdigest()[:12]
    destination = destination or OUT / f"release-{identifier}.tar.gz"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as archive:
        import io

        info = tarfile.TarInfo("manifest.json")
        info.size = len(encoded)
        archive.addfile(info, io.BytesIO(encoded))
        for path in files:
            archive.add(path, arcname=str(path.relative_to(OUT)))
    print(destination)
    print("SHA-256", hashlib.sha256(destination.read_bytes()).hexdigest())


def install(archive_path: Path, destination: Path = OUT) -> None:
    """Install a verified release when building an API image from a fresh checkout."""
    with tempfile.TemporaryDirectory() as temporary:
        staged = Path(temporary)
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(staged, filter="data")
        manifest = json.loads((staged / "manifest.json").read_text())
        if manifest.get("format_version") != 1 or set(manifest["models"]) != set(COHORTS):
            raise ValueError("The release manifest must contain all three supported cohorts.")
        for cohort in COHORTS:
            model_path = staged / cohort / "selected.joblib"
            digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
            report = json.loads(model_path.with_suffix(".json").read_text())
            if digest != manifest["models"][cohort]["sha256"] or digest != report["sha256"]:
                raise ValueError(f"{cohort}: the packaged model checksum does not match.")
            bundle = joblib.load(model_path)
            validate_bundle(bundle, cohort)
            if bundle.get("prediction_context") != CONTEXT:
                raise ValueError("The API release requires antenatal-history models.")
        for cohort in COHORTS:
            target = destination / cohort
            target.mkdir(parents=True, exist_ok=True)
            for source in (staged / cohort).iterdir():
                shutil.copyfile(source, target / source.name)
    print("Installed verified antenatal release", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument(
        "--install", type=Path, help="Install a packaged release into ml/models/antenatal."
    )
    operation.add_argument("--output", type=Path, help="Write the release archive to this path.")
    args = parser.parse_args()
    if args.install:
        install(args.install)
    else:
        package(args.output)
