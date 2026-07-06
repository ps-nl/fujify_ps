#!/usr/bin/env python3
"""
Fujify DNG - macOS command-line port of Fujify's core ExifTool step.

Unlocks Fujifilm film simulation profiles in Lightroom for DNG files by
tagging them with Fujifilm camera-profile metadata via ExifTool. Assumes
your files are already DNG (no RAW->DNG conversion is performed).

Requires ExifTool: brew install exiftool
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = "X-T5"


def build_exiftool_tags(model: str) -> list[str]:
    full_model = f"Fujifilm {model}"
    return [
        "-CameraProfilesMake=FUJIFILM",
        f"-CameraProfilesModel={model}",
        f"-CameraProfilesUniqueCameraModel={full_model}",
        "-CameraProfilesCameraRawProfile=True",
        f"-UniqueCameraModel={full_model}",
    ]


def find_dng_files(folder: Path, recursive: bool) -> list[Path]:
    files = folder.rglob("*") if recursive else folder.glob("*")
    return sorted(p for p in files if p.is_file() and p.suffix.lower() == ".dng")


def process_file(
    exiftool_path: str,
    filepath: Path,
    tags: list[str],
    output_dir: Path | None,
    backup: bool,
) -> tuple[bool, str]:
    cmd = [exiftool_path, *tags]

    if output_dir is not None:
        dest = output_dir / filepath.name
        if dest.exists():
            dest.unlink()
        cmd += ["-o", str(dest)]
    elif not backup:
        cmd.append("-overwrite_original")

    cmd.append(str(filepath))

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout
    if result.returncode == 0 and (
        "image files updated" in output or "image files created" in output
    ):
        return True, output.strip()
    return False, (result.stderr or output).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Unlock Fujifilm film simulation profiles on a folder of DNG "
            "files using ExifTool."
        )
    )
    parser.add_argument("folder", type=Path, help="Folder containing DNG files")
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        help=f"Fujifilm camera model to spoof (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Write processed files here instead of overwriting in place",
    )
    parser.add_argument(
        "-b",
        "--backup",
        action="store_true",
        help=(
            "Keep a backup of each original file (ExifTool adds a "
            "'_original' suffix) instead of overwriting in place. Ignored "
            "if --output-dir is set."
        ),
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into subfolders",
    )
    parser.add_argument(
        "--exiftool",
        default="exiftool",
        help="Name or path of the exiftool binary (default: assumes it's on PATH)",
    )
    args = parser.parse_args()

    exiftool_path = shutil.which(args.exiftool)
    if exiftool_path is None:
        sys.exit(
            f"error: could not find '{args.exiftool}' on PATH. "
            "Install it with: brew install exiftool"
        )

    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        sys.exit(f"error: {folder} is not a directory")

    output_dir = None
    if args.output_dir:
        output_dir = args.output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    dng_files = find_dng_files(folder, args.recursive)
    if not dng_files:
        sys.exit(f"No .dng files found in {folder}")

    tags = build_exiftool_tags(args.model)

    print(f"Applying Fujifilm {args.model} film simulation profile to {len(dng_files)} DNG file(s)...")

    failures = []
    for filepath in dng_files:
        ok, message = process_file(exiftool_path, filepath, tags, output_dir, args.backup)
        print(f"[{'OK' if ok else 'FAILED'}] {filepath.name}")
        if not ok:
            failures.append((filepath, message))

    if failures:
        print(f"\n{len(failures)} file(s) failed:")
        for filepath, message in failures:
            print(f"  {filepath.name}: {message}")
        sys.exit(1)

    print("\nDone. Import the files into Lightroom and select the Fujifilm profile from the Camera Matching tab.")


if __name__ == "__main__":
    main()
