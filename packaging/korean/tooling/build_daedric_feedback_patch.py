"""Build a complete Korean mod folder with repaired Daedric shrine subtitles and scrolls.

Requires the installed/released Korean mod directory and the three unmodified
Morrowind/Tribunal/Bloodmoon ESM files. Source inputs are never written to.
The output directory must not exist; any failed validation leaves it absent.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ESP = "Morrowind_Korean_ReTranslation.esp"
HERE = Path(__file__).resolve().parent


def run(script, *args):
    command = [sys.executable, str(HERE / script), *(str(arg) for arg in args)]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(
            f"{script} failed (exit {completed.returncode}):\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return completed.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-mod", required=True, type=Path)
    ap.add_argument("--master", action="append", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    source = args.source_mod.resolve()
    output = args.output.resolve()
    masters = [path.resolve() for path in args.master]
    if output.exists():
        ap.error("Output directory already exists; choose a new directory")
    if not source.is_dir() or not (source / ESP).is_file():
        ap.error("--source-mod must be a Korean mod directory containing the ESP")
    if source == output or source in output.parents:
        ap.error("Output must be outside the input mod directory")
    if len(masters) != 3 or {x.name.lower() for x in masters} != {
        "morrowind.esm", "tribunal.esm", "bloodmoon.esm"
    } or not all(x.is_file() for x in masters):
        ap.error("Pass the three installed Morrowind.esm, Tribunal.esm and Bloodmoon.esm files")
    masters = [next(x for x in masters if x.name.lower() == name)
               for name in ("morrowind.esm", "tribunal.esm", "bloodmoon.esm")]
    main_master = masters[0]
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="daedric-feedback-", dir=output.parent) as tmp:
        stage = Path(tmp) / "quest"
        quest_report = run(
            "patch_daedric_shrine_dialogue.py", "--source-mod", source,
            "--master", main_master, "--output", stage,
        )
        repaired_esp = Path(tmp) / "repaired.esp"
        scroll_report = run(
            "restore_daedric_book_glyphs.py",
            *(arg for master in masters for arg in ("--master", master)),
            "--translation", stage / ESP,
            "--output", repaired_esp,
            "--report", Path(tmp) / "scrolls.json",
        )
        run(
            "verify_daedric_shrine_dialogue.py", "--master", main_master,
            "--source-esp", source / ESP, "--patched-esp", stage / ESP,
        )
        run(
            "verify_daedric_scrolls.py",
            *(arg for master in masters for arg in ("--master", master)),
            "--plugin", repaired_esp,
        )
        shutil.copy2(repaired_esp, stage / ESP)
        (stage / "daedric-scroll-verification.json").write_text(
            (Path(tmp) / "scrolls.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        stage.rename(output)

    print(json.dumps({
        "output": str(output),
        "shrine": json.loads(quest_report),
        "scroll": json.loads(scroll_report),
        "validated": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
