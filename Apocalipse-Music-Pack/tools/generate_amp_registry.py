#!/usr/bin/env python3
"""Generate the Project Zomboid sound definitions and AMP song catalog."""

from __future__ import annotations

import hashlib
import math
import shutil
import sys
from pathlib import Path


MOD_ROOT = Path(__file__).resolve().parents[1]
SOUND_ROOT = MOD_ROOT / "common" / "media" / "sound"
SOUND_SCRIPT = MOD_ROOT / "common" / "media" / "scripts" / "ApocalipseMusic_Sounds.txt"
LUA_REGISTRY = MOD_ROOT / "common" / "media" / "lua" / "shared" / "ApocalipseMusic" / "AMPRegistry.lua"
SUPPORTED_AUDIO = {".ogg"}
# Reference clip distances; the framework controls attenuation for 2D playback.
MUSIC_DISTANCE_MIN = 10
MUSIC_DISTANCE_MAX = 128


def ogg_vorbis_duration(path: Path) -> float:
    """Read duration from Ogg page granules and the Vorbis identification packet."""
    sample_rate = None
    last_granule = 0
    with path.open("rb") as stream:
        while True:
            header = stream.read(27)
            if not header:
                break
            if len(header) != 27 or header[:4] != b"OggS":
                raise ValueError("invalid Ogg page header")
            granule = int.from_bytes(header[6:14], "little", signed=False)
            segment_count = header[26]
            lacing = stream.read(segment_count)
            if len(lacing) != segment_count:
                raise ValueError("truncated Ogg segment table")
            body_size = sum(lacing)
            body = stream.read(body_size)
            if len(body) != body_size:
                raise ValueError("truncated Ogg page")
            if sample_rate is None:
                marker = body.find(b"\x01vorbis")
                if marker >= 0 and len(body) >= marker + 16:
                    sample_rate = int.from_bytes(body[marker + 12:marker + 16], "little")
            # 0xffffffffffffffff marks a page without a completed packet.
            if granule != 0xFFFFFFFFFFFFFFFF:
                last_granule = max(last_granule, granule)
    if not sample_rate:
        raise ValueError("Vorbis identification header not found")
    duration = last_granule / sample_rate
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("invalid or empty audio duration")
    return duration


def lua_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'


def track_metadata(path: Path) -> tuple[str, str]:
    stem = path.stem.strip()
    if " - " in stem:
        artist, title = stem.split(" - ", 1)
        return artist.strip() or "Unknown Artist", title.strip() or stem
    return "Unknown Artist", stem or path.name


def main() -> int:
    files = sorted(
        (path for path in SOUND_ROOT.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO
            and path.relative_to(SOUND_ROOT).parts[0] != "AMPAssets"),
        key=lambda path: path.relative_to(SOUND_ROOT).as_posix().casefold(),
    )
    if not files:
        print(f"No supported audio files found under {SOUND_ROOT}", file=sys.stderr)
        return 1

    entries = []
    failures = []
    for path in files:
        relative = path.relative_to(SOUND_ROOT).as_posix()
        try:
            duration = ogg_vorbis_duration(path)
        except (OSError, ValueError) as exc:
            failures.append(f"{relative}: {exc}")
            continue
        # IDs depend on the relative path, not enumeration order or basename.
        path_hash = hashlib.sha1(relative.encode("utf-8")).hexdigest().upper()
        sound_id = "AMP_" + path_hash[:16]
        song_id = "amp_song_" + path_hash[:12].lower()
        artist, title = track_metadata(path)
        media_path = "media/sound/" + relative
        # PZ's script parser splits at commas and preserves quotes literally.
        # Keep catalog IDs/metadata based on the original filename, but give
        # paths containing script delimiters an unquoted, parser-safe alias.
        if any(char in relative for char in ',={}'):
            alias = SOUND_ROOT / "AMPAssets" / (path_hash[:16] + path.suffix.lower())
            alias.parent.mkdir(parents=True, exist_ok=True)
            if not alias.exists() or alias.stat().st_size != path.stat().st_size \
                    or alias.stat().st_mtime_ns != path.stat().st_mtime_ns:
                shutil.copy2(path, alias)
            media_path = "media/sound/AMPAssets/" + alias.name
        entries.append((sound_id, song_id, media_path, duration, artist, title, relative))

    if failures:
        print("Could not read duration for these files; outputs were not changed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    SOUND_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    LUA_REGISTRY.parent.mkdir(parents=True, exist_ok=True)

    sound_lines = ["module Base", "{"]
    for sound_id, _song_id, media_path, *_ in entries:
        sound_lines.append(
            f'    sound {sound_id} {{ category = Vehicle, loop = false, is3D = false, '
            f'clip {{ file = {media_path}, volume = 1.0f, '
            f'distanceMin = {MUSIC_DISTANCE_MIN}, distanceMax = {MUSIC_DISTANCE_MAX}, }} }}'
        )
    sound_lines.append("}")
    SOUND_SCRIPT.write_text("\n".join(sound_lines) + "\n", encoding="utf-8")

    lua_lines = [
        '-- Generated by tools/generate_amp_registry.py; edit source filenames, then regenerate.',
        'require "ApocalipseMusic/AMPStation"',
        '',
        'local station = "amp_music"',
        '',
    ]
    for sound_id, song_id, _media_path, duration, artist, title, _relative in entries:
        lua_lines.extend([
            "ABRRadio.registerSong({",
            f'    id = {lua_string(song_id)},',
            "    station = station,",
            f"    sound = {lua_string(sound_id)},",
            f"    duration = {math.ceil(duration)},",
            f"    artist = {lua_string(artist)},",
            f"    title = {lua_string(title)},",
            "})",
            "",
        ])
    lua_lines.extend([
        'local registeredStation = ABRRadio.music.stations[station]',
        'print("[Apocalipse Music Pack] Catalog registration complete: "',
        '    .. ABRRadio.resolveText(registeredStation.name) .. " [" .. station .. "] @ "',
        '    .. registeredStation.frequency .. "; songs=" .. #registeredStation.songs',
        '    .. "; talks=" .. #registeredStation.talks)',
        '',
    ])
    LUA_REGISTRY.write_text("\n".join(lua_lines), encoding="utf-8")
    print(f"Generated {len(entries)} sound definitions: {SOUND_SCRIPT}")
    print(f"Generated {len(entries)} AMP song registrations: {LUA_REGISTRY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
