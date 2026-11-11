#!/usr/bin/env python3
"""Safely apply SHA256-pinned BSDIFF40 patches to user-owned game/mod masters.

The private patch-only archive contains a JSON manifest and BSDIFF40 patches,
NOT any copyrighted original ESM/ESP bytes. Users supply their unmodified
upstream originals separately. This executable needs Python 3 standard library
only (no bsdiff4 installation).

Manifest v1 (all paths are slash-separated, relative, never absolute):

{
  "schema_version": 1,
  "format": "BSDIFF40",
  "entries": [
    {
      "original": {"path": "standard/TR_Mainland.esm", "sha256": "<64 hex>"},
      "patch": {"path": "deltas/TR_Mainland.esm.bsdiff", "sha256": "<64 hex>"},
      "output": {"path": "common/TR_Mainland.esm", "sha256": "<64 hex>"},
      "group": "common"
    }
  ]
}

original.path resolves under --originals-dir, patch.path under the manifest's
directory, and output.path under --output-dir. Original paths can be flat
filenames. Output namespaces such as "common/", "standard/", and "rebirth/"
distinguish alternative masters. Optional group is common|standard|rebirth
(omitted = common); --mode standard (default) selects common+standard,
--mode rebirth selects common+rebirth, and --mode all selects all.
NEVER enable standard Cyr/Sky AND Rebirth compatibility masters at the same
time in an actual OpenMW game configuration.

No source or existing output is ever overwritten. All targets are first built
and verified as temporary files beside their intended destinations. Commit
uses atomic, NO-REPLACE hard-link creation (os.link) on the same filesystem;
it deliberately does not use os.replace, which could overwrite a file created
by another process between preflight and commit.

The BSDIFF40 control, diff, and extra streams are BZip2 decompressed in bounded
chunks. mmap is used read-only for potentially multi-gigabyte input/patches.
"""

from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import mmap
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

CHUNK = 1024 * 1024
COMPRESSED_CHUNK = 64 * 1024
MAX_ENTRIES = 256
MAX_OUTPUT_SIZE = 16 * 1024**3  # 16 GiB; ESM/ESP are much smaller.
MAX_CONSECUTIVE_SEEKS = 4096  # Malformed control streams must not spin without output.
MAGIC = b"BSDIFF40"
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
WINDOWS_BAD_CHARS = set('<>:"\\|?*')
WINDOWS_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"} |
    {"COM" + str(i) for i in range(1, 10)} |
    {"LPT" + str(i) for i in range(1, 10)}
)


class DeltaError(Exception):
    """A manifest, patch, source, output, or filesystem safety error."""


@dataclass(frozen=True)
class Entry:
    group: str
    original: Path
    original_sha: str
    patch: Path
    patch_sha: str
    target: Path
    target_sha: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            part = f.read(CHUNK)
            if not part:
                return h.hexdigest()
            h.update(part)


def _unique_keys(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise DeltaError("Duplicate JSON object key: " + key)
        record[key] = value
    return record


def _sha256(value, where: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise DeltaError(where + ": expected 64-character SHA256 hexadecimal string")
    return value.lower()


def _safe_relative_path(value, where: str) -> Path:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise DeltaError(where + ": nonempty relative path required")
    # Require portable manifest paths so Windows drive names and backslash
    # traversal cannot be interpreted differently across operating systems.
    if value.startswith("/") or "\\" in value or ":" in value:
        raise DeltaError(where + ": absolute, drive, or backslash paths are forbidden")
    components = value.split("/")
    if any(not c or c in {".", ".."} for c in components):
        raise DeltaError(where + ": empty, '.' or '..' path components forbidden")
    for component in components:
        if any(ord(c) < 32 or c in WINDOWS_BAD_CHARS for c in component):
            raise DeltaError(where + ": unsafe filename character")
        if component.endswith((" ", ".")):
            raise DeltaError(where + ": trailing dot/space is unsafe on Windows")
        if component.split(".")[0].upper() in WINDOWS_RESERVED:
            raise DeltaError(where + ": reserved Windows filename")
    return Path(*components)


def _contained(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _no_symlink_components(root: Path, path: Path, where: str) -> None:
    """Reject symlinked path components, including dangling symlinks."""
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise DeltaError(where + ": escaped the configured root") from exc
    cursor = root
    for component in relative.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise DeltaError(where + ": symbolic links are forbidden: " + str(cursor))
        # Windows junctions can redirect even when is_symlink() is false.
        if hasattr(cursor, "is_junction") and cursor.is_junction():
            raise DeltaError(where + ": Windows junctions are forbidden: " + str(cursor))
        if cursor.exists() and not _contained(cursor.resolve(), root):
            raise DeltaError(where + ": resolved path escapes configured root")


def _resolve_under(root: Path, relative: Path, where: str, *, must_exist: bool) -> Path:
    result = root.joinpath(relative)
    _no_symlink_components(root, result, where)
    if not _contained(result.resolve(), root):
        raise DeltaError(where + ": resolved path escapes configured root")
    if must_exist:
        if not result.is_file():
            raise DeltaError(where + ": missing or not a file: " + str(result))
    elif result.exists() or result.is_symlink():
        raise DeltaError(where + ": target already exists: " + str(result))
    return result


def _root(path: Path, name: str, *, must_exist: bool) -> Path:
    if path.is_symlink():
        raise DeltaError(name + ": root must not be a symbolic link")
    if hasattr(path, "is_junction") and path.is_junction():
        raise DeltaError(name + ": root must not be a junction")
    resolved = path.resolve()
    if must_exist and not resolved.is_dir():
        raise DeltaError(name + ": directory does not exist")
    if resolved.exists() and not resolved.is_dir():
        raise DeltaError(name + ": not a directory")
    return resolved


def load_manifest(
    manifest: Path, originals_dir: Path, output_dir: Path, mode: str = "standard"
) -> list[Entry]:
    if mode not in {"standard", "rebirth", "all"}:
        raise DeltaError("Invalid mode; choose standard, rebirth, or all")
    if manifest.is_symlink():
        raise DeltaError("Manifest must not be a symbolic link")
    if hasattr(manifest, "is_junction") and manifest.is_junction():
        raise DeltaError("Manifest must not be a junction")
    manifest = manifest.resolve(strict=True)
    if not manifest.is_file() or manifest.is_symlink():
        raise DeltaError("Manifest must be an ordinary file")
    patch_root = manifest.parent
    originals_root = _root(originals_dir, "--originals-dir", must_exist=True)
    output_root = _root(output_dir, "--output-dir", must_exist=False)
    if _contained(originals_root, output_root) or _contained(output_root, originals_root):
        raise DeltaError("Original and output directories must be disjoint")
    if _contained(manifest, output_root):
        raise DeltaError("Manifest must not be inside the output directory")
    try:
        with manifest.open("r", encoding="utf-8") as f:
            doc = json.load(f, object_pairs_hook=_unique_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DeltaError("Invalid UTF-8 JSON manifest") from exc
    if not isinstance(doc, dict) or set(doc) != {"schema_version", "format", "entries"}:
        raise DeltaError("Manifest must contain exactly schema_version, format and entries")
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise DeltaError("Unsupported manifest schema_version (expected 1)")
    if doc["format"] != "BSDIFF40":
        raise DeltaError("Manifest format must be BSDIFF40")
    records = doc["entries"]
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_ENTRIES:
        raise DeltaError("Manifest entries must be a nonempty list with at most 256 entries")

    parsed: list[Entry] = []
    original_seen, patch_seen, target_seen = set(), set(), set()
    for index, item in enumerate(records):
        prefix = "entries[" + str(index) + "]"
        mandatory = {"original", "patch", "output"}
        if (not isinstance(item, dict) or not mandatory <= set(item) or
                not set(item) <= mandatory | {"group"}):
            raise DeltaError(prefix + ": require original, patch, output; optional group")
        group = item.get("group", "common")
        if group not in ("common", "standard", "rebirth"):
            raise DeltaError(prefix + ": group must be common, standard, or rebirth")
        fields = []
        for field in ("original", "patch", "output"):
            spec = item[field]
            if not isinstance(spec, dict) or set(spec) != {"path", "sha256"}:
                raise DeltaError(prefix + "." + field + ": require path and sha256")
            relative = _safe_relative_path(spec["path"], prefix + "." + field + ".path")
            sha = _sha256(spec["sha256"], prefix + "." + field + ".sha256")
            fields.append((relative, sha))

        (source_rel, source_sha), (patch_rel, patch_sha), (target_rel, target_sha) = fields
        for rel, seen, field in (
            (source_rel, original_seen, "original"),
            (patch_rel, patch_seen, "patch"),
            (target_rel, target_seen, "output"),
        ):
            # Case-insensitive duplicate defense for Windows, even on Linux.
            folded = rel.as_posix().casefold()
            if folded in seen:
                raise DeltaError(prefix + ": duplicate " + field + " entry: " + rel.as_posix())
            seen.add(folded)
        # Never require an unselected alternative's original master to be
        # installed: standard users do not need Rebirth, and vice versa.
        # Validate every manifest path and duplicate above, even if inactive.
        if mode != "all" and group not in ("common", mode):
            continue
        source = _resolve_under(originals_root, source_rel, prefix + ".original", must_exist=True)
        patch = _resolve_under(patch_root, patch_rel, prefix + ".patch", must_exist=True)
        target = _resolve_under(output_root, target_rel, prefix + ".output", must_exist=False)
        if target in (source, patch, manifest):
            raise DeltaError(prefix + ": would overwrite a source, patch, or manifest")
        if _contained(patch, output_root):
            raise DeltaError(prefix + ": patch file must not live inside output directory")
        if not (source.suffix.lower() in {".esm", ".esp"} and
                target.suffix.lower() in {".esm", ".esp"}):
            raise DeltaError(prefix + ": original/output must be .esm or .esp files")
        parsed.append(Entry(group, source, source_sha, patch, patch_sha, target, target_sha))
    if not parsed:
        raise DeltaError("No patch entries selected for --mode " + mode)
    return parsed


def _offtin(eight: bytes) -> int:
    """BSDIFF40 signed 64-bit sign/magnitude integer, NOT struct <q."""
    if len(eight) != 8:
        raise DeltaError("Truncated BSDIFF40 signed offset")
    value = eight[7] & 0x7F
    for i in range(6, -1, -1):
        value = value * 256 + eight[i]
    return -value if eight[7] & 0x80 else value


class _Bzip2Section:
    """Read one exact bounded BSDIFF40 bz2 stream from a memory-mapped patch."""

    def __init__(self, buf: mmap.mmap, start: int, end: int, label: str):
        self.buf = buf
        self.pos = start
        self.end = end
        self.label = label
        self.dec = bz2.BZ2Decompressor()

    def _next(self, max_length: int) -> bytes:
        if self.dec.eof:
            return b""
        if self.dec.needs_input:
            if self.pos >= self.end:
                raise DeltaError(self.label + ": truncated bz2 stream")
            last = min(self.pos + COMPRESSED_CHUNK, self.end)
            part = self.buf[self.pos:last]
            self.pos = last
        else:
            part = b""
        try:
            data = self.dec.decompress(part, max_length=max_length)
        except (EOFError, OSError, ValueError) as exc:
            raise DeltaError(self.label + ": invalid bz2 stream") from exc
        if self.dec.eof and (self.dec.unused_data or self.pos != self.end):
            raise DeltaError(self.label + ": trailing bytes after bz2 stream")
        return data

    def read_exact(self, length: int) -> bytes:
        if length < 0 or length > CHUNK:
            raise DeltaError(self.label + ": invalid bounded read")
        out = bytearray()
        while len(out) < length:
            piece = self._next(length - len(out))
            if not piece:
                if self.dec.eof:
                    raise DeltaError(self.label + ": decompressed block is too short")
                continue
            out.extend(piece)
        return bytes(out)

    def control_or_eof(self) -> bytes | None:
        if self.dec.eof:
            return None
        first = self._next(24)
        if not first and self.dec.eof:
            return None
        result = bytearray(first)
        while len(result) < 24:
            if self.dec.eof:
                raise DeltaError("control: partial 24-byte triple")
            result.extend(self._next(24 - len(result)))
        return bytes(result)

    def assert_eof(self) -> None:
        while not self.dec.eof:
            if self._next(1):
                raise DeltaError(self.label + ": unexpected decompressed trailing data")
        if self.pos != self.end:
            raise DeltaError(self.label + ": mismatched compressed section size")


def _reconstruct(original: Path, patch: Path, output_handle) -> str:
    h = hashlib.sha256()
    with original.open("rb") as src, patch.open("rb") as binary:
        old_size = original.stat().st_size
        patch_size = patch.stat().st_size
        if patch_size < 32:
            raise DeltaError("Truncated BSDIFF40 patch header")
        with mmap.mmap(binary.fileno(), 0, access=mmap.ACCESS_READ) as patched:
            if patched[:8] != MAGIC:
                raise DeltaError("Not a BSDIFF40 patch")
            ctrl_size = _offtin(patched[8:16])
            diff_size = _offtin(patched[16:24])
            target_size = _offtin(patched[24:32])
            if ctrl_size <= 0 or diff_size <= 0 or not 0 <= target_size <= MAX_OUTPUT_SIZE:
                raise DeltaError("Invalid BSDIFF40 header block lengths or output size")
            ctrl_start, diff_start = 32, 32 + ctrl_size
            extra_start = diff_start + diff_size
            if extra_start >= patch_size:
                raise DeltaError("Truncated BSDIFF40 compressed sections")
            ctrl = _Bzip2Section(patched, ctrl_start, diff_start, "control")
            diff = _Bzip2Section(patched, diff_start, extra_start, "diff")
            extra = _Bzip2Section(patched, extra_start, patch_size, "extra")
            original_map = (mmap.mmap(src.fileno(), 0, access=mmap.ACCESS_READ)
                            if old_size else None)
            try:
                old_pos, new_pos = 0, 0
                consecutive_seeks = 0
                while new_pos < target_size:
                    triple = ctrl.control_or_eof()
                    if triple is None:
                        raise DeltaError("control: ran out before expected output size")
                    add_length = _offtin(triple[:8])
                    copy_length = _offtin(triple[8:16])
                    seek_length = _offtin(triple[16:])
                    if add_length < 0 or copy_length < 0:
                        raise DeltaError("control: negative diff/extra lengths")
                    # bsdiff4 legitimately emits (0, 0, nonzero_seek) control
                    # triples to reposition the *old* file without producing
                    # any bytes. All seven audited regional BSDIFF40 patches
                    # contain these, occasionally two in a row. Refuse no-op
                    # (0, 0, 0) and pathological unbounded seek-only runs.
                    if add_length == 0 and copy_length == 0:
                        if seek_length == 0:
                            raise DeltaError("control: zero diff, extra, and seek (no progress)")
                        consecutive_seeks += 1
                        if consecutive_seeks > MAX_CONSECUTIVE_SEEKS:
                            raise DeltaError("control: excessive consecutive seek-only triples")
                        old_pos += seek_length
                        continue
                    consecutive_seeks = 0
                    if add_length + copy_length > target_size - new_pos:
                        raise DeltaError("control: output would exceed pinned target size")
                    progress = 0
                    while progress < add_length:
                        n = min(CHUNK, add_length - progress)
                        result = bytearray(diff.read_exact(n))
                        old_start = old_pos + progress
                        lo, hi = max(0, old_start), min(old_size, old_start + n)
                        if lo < hi:
                            assert original_map is not None
                            old_part = original_map[lo:hi]
                            dst_start = lo - old_start
                            for i, original_byte in enumerate(old_part):
                                j = dst_start + i
                                result[j] = (result[j] + original_byte) & 0xFF
                        output_handle.write(result)
                        h.update(result)
                        progress += n
                    new_pos += add_length
                    old_pos += add_length + seek_length
                    progress = 0
                    while progress < copy_length:
                        n = min(CHUNK, copy_length - progress)
                        block = extra.read_exact(n)
                        output_handle.write(block)
                        h.update(block)
                        progress += n
                    new_pos += copy_length
                ctrl.assert_eof()
                diff.assert_eof()
                extra.assert_eof()
            finally:
                if original_map is not None:
                    original_map.close()
    return h.hexdigest()


def _verify_inputs(entries: list[Entry]) -> None:
    for i, entry in enumerate(entries):
        if sha256_file(entry.original) != entry.original_sha:
            raise DeltaError("Wrong or modified user-owned original at entry " + str(i) +
                             ": " + str(entry.original))
        if sha256_file(entry.patch) != entry.patch_sha:
            raise DeltaError("Wrong or modified BSDIFF40 patch at entry " + str(i) +
                             ": " + str(entry.patch))


def apply(manifest: Path, originals_dir: Path, output_dir: Path,
          mode: str = "standard") -> list[Path]:
    """Apply a manifest transactionally without overwriting original/targets."""
    entries = load_manifest(manifest, originals_dir, output_dir, mode)
    _verify_inputs(entries)  # no output creation before all SHA checks succeed
    output_root = _root(output_dir, "--output-dir", must_exist=False)
    staged: list[tuple[Path, Path]] = []
    committed: list[tuple[Path, Path]] = []
    try:
        for index, item in enumerate(entries):
            _no_symlink_components(output_root, item.target, "output")
            if item.target.exists() or item.target.is_symlink():
                raise DeltaError("Output already exists: " + str(item.target))
            item.target.parent.mkdir(parents=True, exist_ok=True)
            _no_symlink_components(output_root, item.target, "output")
            fd, tmp = tempfile.mkstemp(prefix=".regional-delta-", suffix=".tmp",
                                       dir=str(item.target.parent))
            temporary = Path(tmp)
            staged.append((temporary, item.target))
            with os.fdopen(fd, "wb") as dest:
                result_sha = _reconstruct(item.original, item.patch, dest)
                dest.flush()
                os.fsync(dest.fileno())
            if result_sha != item.target_sha:
                raise DeltaError("Reconstructed output SHA256 mismatch for entry " +
                                 str(index) + ": " + item.target.name)
            # Re-read after reconstructing: concurrent mutation of source or
            # patch invalidates the transaction, even if target SHA matched.
            if sha256_file(item.original) != item.original_sha:
                raise DeltaError("Original changed during reconstruction")
            if sha256_file(item.patch) != item.patch_sha:
                raise DeltaError("Patch changed during reconstruction")

        # All verified temp outputs are ready. Link creation is atomic and
        # fails with FileExistsError; unlike os.replace it NEVER overwrites.
        for temporary, target in staged:
            try:
                os.link(temporary, target)
            except FileExistsError as exc:
                raise DeltaError("Refusing to overwrite existing output: " + str(target)) from exc
            except OSError as exc:
                raise DeltaError(
                    "Atomic no-overwrite link failed (requires same-filesystem "
                    "hard-link support): " + str(target)
                ) from exc
            committed.append((temporary, target))
        return [entry.target for entry in entries]
    except BaseException:
        # Roll back files *we* published. Do not unlink a path another process
        # might have replaced; only our staged inode is eligible for cleanup.
        for temporary, target in reversed(committed):
            try:
                if temporary.exists() and target.exists() and os.path.samefile(temporary, target):
                    target.unlink()
            except OSError:
                pass
        raise
    finally:
        for temporary, _ in staged:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True,
                        help="JSON manifest (patch paths are relative to this file)")
    parser.add_argument("--originals-dir", type=Path, required=True,
                        help="Directory containing your own unmodified upstream ESM/ESP")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Separate directory for new patched ESM/ESP; no overwrite")
    parser.add_argument("--mode", choices=("standard", "rebirth", "all"),
                        default="standard",
                        help="Which master set: default standard; common always included")
    args = parser.parse_args(argv)
    try:
        completed = apply(args.manifest, args.originals_dir, args.output_dir,
                          mode=args.mode)
    except (DeltaError, OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2
    if args.mode == "all":
        print("WARNING: standard Cyr/Sky and Rebirth compatibility masters are "
              "ALTERNATIVES: never activate both in one OpenMW load order.",
              file=sys.stderr)
    for path in completed:
        print("CREATED " + str(path) + " SHA256 " + sha256_file(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
