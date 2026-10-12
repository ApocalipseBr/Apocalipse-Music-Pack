# Apocalipse Music Pack (Build 42)

This is a content pack: station registration, independent song modules, audio
assets, timed lyrics, and generic between-song radio talk. Playback, synchronization,
and channel scheduling belong to ApocalipseBRRadio v2.1.0 or newer. This pack
depends on `apocalipsebrradio`. No music files are included yet; the
station stays silent until you register at least one song.

## Audio storage and pull requests

All `*.ogg` files are stored with Git LFS. Install Git LFS before cloning or
adding audio, then run these commands from the repository root:

```powershell
git lfs install
git lfs pull
```

To contribute audio, create a branch in a local clone, copy the OGG files into
the appropriate mod asset folder, and use normal `git add`, `git commit`, and
`git push` commands. The committed `.gitattributes` automatically applies LFS
to new OGG files at any depth. Open a pull request from that branch or a fork.
Use a Git LFS-enabled local client for audio contributions; GitHub's browser
upload does not perform the local LFS conversion.

Before committing, check `git lfs status`. After committing, check
`git lfs fsck` and `git lfs ls-files` to verify the audio is stored correctly.
Keep `.gitattributes` in place. LFS storage and download quotas apply to the
repository owner's account, including contributions through forks.

Build and Workshop publication require the actual audio files, so run
`git lfs pull` first. GitHub Actions jobs that package audio must use
`actions/checkout` with `lfs: true`. A source download containing only LFS
pointers is not a complete playable pack.

The repository history was reset to one current-state commit when LFS was
introduced. Existing contributors should make a fresh clone and create new
branches from the replacement `master` before submitting further changes.

## Files

- `Apocalipse-Music-Pack/42/mod.info`: B42 metadata and radio dependency.
- `Apocalipse-Music-Pack/common/media/lua/shared/ApocalipseMusic/AMPStation.lua`:
  station name/frequency (94.2 FM), color, talk probability, and talk variants.
- `.../AMPRegistry.lua`: generated song catalog; requires `AMPStation` before
  registering songs. `AMPStation` must not require the registry back, because the
  game can scan the registry first. The generator preserves this dependency.
- `.../Songs/<song-id>.lua`: one registration module per imported song, including
  title, artist, real duration, audio chunks, and timestamped lyrics.
- `common/media/scripts/AMP_<song-id>.txt` and
  `common/media/sound/ApocalipseMusic/<song-id>/`: generated audio definitions/assets.

The radio framework owns `ABRRadioMusic.lua` (catalog/protocol),
`ABRRadioMusicServer.lua` (real-time authority), and `ABRRadioMusicClient.lua`
(listener playback/captions), under its own `common/media/lua` folders.

Run `node tests/startup_spec.js` with Fengari available to verify registry-first
and station-first startup against the generated catalog and station/talk labels.
Music labels use `Translate/{EN,PTBR}/IG_UI.json`; the engine maps `IGUI_` keys
to `IG_UI.json`. Both dictionaries contain EN and PTBR broadcast variants.
Set `AMP_MUSIC_MOD` to an alternate mod root to check a Workshop staging copy.

After the final song registration, `[Apocalipse Music Pack] Catalog registration
complete` logs the station name, ID, frequency, and total song/talk counts. The
generator preserves this log. Playback diagnostics use `[ABRRadio Music Server]`
in the framework, with startup readiness, phase changes, and a 60-second runtime
heartbeat per station.
The music pack contains no playback controller.

Sound clip `file` paths must be unquoted: PZ's sound parser preserves quote
characters and splits values at commas. The generator creates parser-safe copies
under `common/media/sound/AMPAssets` for filenames containing script delimiters,
while retaining the original song IDs and metadata. Include these assets when
deploying the pack. Generated aliases are excluded from song discovery.

Generated music clips use `is3D = false`, `distanceMin = 10`, and
`distanceMax = 128`. The framework renders non-spatial audio and applies a shared
Lua distance curve with squared falloff. At full radio volume, propagation
reaches 100 yards (91.44 tiles); at half volume it reaches 50 yards. Playback
activates and stays eligible within 200 yards (182.88 tiles), so changing audible
range or approaching from the silent outer region does not restart
the track. Existing files retain their stereo channels.
Music control heartbeats reach all connected clients; playback discovery depends
on the radio being loaded on the client, rather than vanilla text reception.

Use `ABRRadio.registerMusicStation`, `ABRRadio.registerSong`, and
`ABRRadio.registerMusicTalk` to supply content. Framework transmissions may share
this channel: `ABRRadio.triggerImmediate` waits until music/timed talk ends, then
deferred messages drain in order. Ordinary scheduled text also waits for the
segment to finish. Music waits for an active text transmission, queued messages,
and due eligible scheduled text before acquiring the channel again. Other
frequencies continue independently. Arbitration covers framework APIs; native
radio scripts or third-party calls directly to `SendTransmission` bypass it.

## Standalone audio conversion and asset import

`tools/convert_to_ogg.py` requires Python 3.9+ and runs independently of this
project. It uses FFmpeg from PATH if available; otherwise it automatically
downloads the bundled executable through `imageio-ffmpeg` into a private user
cache. First setup requires internet and pip (the script attempts `ensurepip`
if pip is missing). No manual Python package installation is needed.

```powershell
python tools/convert_to_ogg.py
python tools/convert_to_ogg.py "Z:\Music\song.mp3"
python tools/convert_to_ogg.py "Z:\Music\song.wav" -o "Z:\Music\small.ogg" --quality 2 --mono
python tools/convert_to_ogg.py "Z:\Music" --recursive --output-dir "Z:\Music-OGG"
python tools/convert_to_ogg.py "Z:\Music" --mod-assets
```

With no arguments, the script prompts for a file or folder. Pasted quoted paths
are accepted. Folder scans always recurse through every level and recognize
common audio extensions including MP3, WAV, FLAC, OGG, M4A, AAC, Opus, AIFF,
and WMA. Unreadable or unsupported encodings are reported during conversion;
the rest of the batch continues. Non-audio files are ignored.

Interactive mode previews the files and destination, asks for quality and mono
settings, and requires a yes before conversion or automatic dependency setup.
The default destination is
`Apocalipse-Music-Pack/common/media/sound/ApocalipseMusic/Assets`, resolved from
the script location rather than the terminal's working directory. Source
subfolders are preserved. Asset names include the source extension to keep
`song.mp3` and `song.wav` distinct (`song_mp3.ogg`, `song_wav.ogg`). The output
subtree is excluded from recursive scans, and existing assets are skipped on
repeat runs unless `--overwrite` is specified. A blank input path or declining
the confirmation cancels without converting files. `--mod-assets` also selects
this destination and naming convention for noninteractive command-line use.

Outputs are Ogg Vorbis, quality 2 and 44.1 kHz by default. Lower `--quality`
reduces size; `--mono` trades stereo for additional savings. When input paths
are supplied as command-line arguments without an output option, files are
written beside their sources with an `.ogg` extension.
Sources are preserved. Existing outputs require `--overwrite` in ordinary
command-line mode. Folder mode always scans recursively and preserves subfolder
layout when using `--output-dir`; `--recursive` remains as a compatibility option.
`--ffmpeg <path>` selects an existing executable explicitly.
Run `--help` for all options. Conversion reports output size and percentage
change; already compressed MP3 inputs may produce larger outputs depending on
quality. This converter creates audio files only; it does not generate sound
scripts, song registrations, or lyric entries. Music-pack registration still
uses the separate importer below, whose own encoding settings determine the
size of its generated chunks.

Dependency reference: [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg/blob/main/README.md).
Real codec/CLI checks: `python tests/test_convert_to_ogg.py -v`.

## Flatten the whole-file audio catalog

The current whole-file catalog stores its OGG files directly in
`Apocalipse-Music-Pack/common/media/sound`. From the repository root:

```powershell
python Apocalipse-Music-Pack/tools/flatten_sound_files.py
python Apocalipse-Music-Pack/tools/flatten_sound_files.py --apply
python Apocalipse-Music-Pack/tools/generate_amp_registry.py
```

The first command previews the move. `--apply` moves all nested files to the
sound folder, adds a deterministic suffix to duplicate filenames instead of
overwriting them, and removes empty subfolders. The move plan (original path,
destination, and byte count) is saved to `tools/flatten_sound_manifest.json`
inside the mod folder before moving files. A repeat run on an already flat
folder does nothing and preserves that manifest. For a later batch, archive the
existing manifest before applying another move.

Regeneration reads the audio durations and updates `ApocalipseMusic_Sounds.txt`
and `AMPRegistry.lua` with the flat paths. Moving or renaming tracks changes
their generated sound and song IDs because IDs are derived from relative paths.

## Import a song

Install Node.js and make `ffmpeg` and `ffprobe` available on PATH. From this folder:

```powershell
npm run import:music -- --input "Z:\Music\song.ogg" --id mypack_song01 --title "Song title" --artist "Artist" --lyrics examples/lyrics.json
npm run build
```

`--lyrics` is optional. `--chunk-seconds 5` is the default (allowed: 1–30).
The importer reads the audio duration with ffprobe, splits/re-encodes audio into
Vorbis chunks, and generates a Lua song module and B42 sound script. It refuses
to overwrite an existing ID. IDs must be unique across installed packs, with
1–24 ASCII letters, digits, underscores, or hyphens; use a pack prefix.

Lyrics JSON is an ordered array of cues, measured in seconds from song start:

```json
[
  { "at": 12.5, "untilTime": 17.0, "text": { "EN": "A lyric line", "PTBR": "Uma linha da letra" } },
  { "at": 18.0, "untilTime": 22.5, "text": "Another line" }
]
```

`untilTime` is optional for song lyrics: without it, a cue is eligible for four
seconds, capped at the next cue or song end. A song module can override this
default with `lyricDuration`. Set `untilTime` for an exact lyric window.
Only add cues where lyrics actually occur; no blank entries are needed for
instrumental sections. Omit `lyrics` or use an empty array for instrumental songs.
Playback commands continue every two seconds for the entire song, independently
of whether any lyric is available. A late listener receives only a currently
eligible cue, without replaying earlier lyrics. Expiry prevents old lyrics from
appearing on late tuning; it does not erase an already displayed vanilla chat
bubble. Talk lines default to lasting until the next talk line or segment end.
Radio language
uses the existing ABR server language setting (EN/PTBR). This is radio content,
so every listener resolves the same language.

For manual whole-file registration, see `examples/song.lua.example`. Supply a
non-looping sound script and audio asset before enabling that module. Whole-file
songs play for listeners present at song start; a late listener gets captions
but waits until the next song for audio. Use generated chunks for mid-song audio.

## Listening and scheduling

The authority picks a weighted song, avoids consecutive repeats when possible,
and waits its entire declared real duration before choosing the next segment.
It may choose one weighted talk variant between songs (35% by default), then
returns to music. Talk consists of locally resolved timed text. You can add
variants with `ABRRadio.registerMusicTalk` in separate shared files.

Only radios receiving this frequency start listener playback. Inventory radios
must be equipped; world/vehicle radios must be within local listening range.
Volume follows the radio slider and distance, with headphone ownership and deaf
players checked. Turning off, muting, retuning, leaving range, or losing
heartbeats for eight seconds stops audio and releases its dedicated emitter.
Music does not replace the radio's own static/VOIP emitter. Native radio signal
handling remains responsible for zombie attraction; custom music is local audio.

With chunks, a listener tuning in midway waits for the next chunk boundary
(normally less than five seconds after receiving the first heartbeat). Heartbeats
arrive every two seconds, so total tune-in delay can approach seven seconds.
No one restarts the song from the beginning. Missing a boundary by more than
250 ms skips that chunk rather than starting it at the wrong position. This is
approximate synchronization, not sample-accurate streaming: chunk transitions,
audio buffering, and network latency require an in-game listening check.

## Compact radio protocol

The native transmission text is empty. The `codes` field carries:

```text
AMP1|mypack_song01|1790000000001|123
```

Fields: protocol version, stable content ID, monotonically increasing broadcast
sequence, elapsed deciseconds (123 = 12.3 seconds). The station comes from the
receiving radio's frequency and the catalog. Song position determines the audio
chunk and lyric index; no lyrics, labels, paths, or per-line commands go on wire.
The same format handles talk IDs. Repeated heartbeats never restart an active
chunk or repeat a displayed cue. A sequence change replaces the current segment.
Unknown IDs/versions and older positions/sequences are ignored.

Each heartbeat is a complete current-state command, allowing late tuning and
recovery from packet loss without listener reports or server/client round trips.
The native packet is still distributed by PZ before its radio reception checks;
this does not reduce vanilla delivery to only tuned network connections.
Weather interference may strip effect codes in native `SendTransmission`;
listeners then time out and resume at a later valid chunk boundary when signal
returns. The catalog and audio assets must match on server and clients.

## More packs and stations

Extra catalog mods can depend on `Apocalipse-Music-Pack` and place song modules,
sound scripts, and assets in their own B42 `common/media` folders. Require
`ApocalipseMusic/AMPStation` before registering songs on `amp_music`. Use
`--mod <extra-mod-root>` to generate files in that pack, then supply its own
`42/mod.info` with `require=Apocalipse-Music-Pack`.

For a separate station, depend directly on `apocalipsebrradio`, require
`ApocalipseBRRadio/ABRRadioMusic` in a uniquely named shared registration file,
and call `ABRRadio.registerMusicStation` with a new ID and unused
frequency. Require that registration file explicitly from its song modules
before calling `ABRRadio.registerSong`. The importer accepts `--station <id>`; adjust
the generated module's require for that custom station. The generic server and
client controllers support all stations in the registry.

## Build and verify

```powershell
npm test
npm run build
```

Build output: `build/Contents/mods/Apocalipse-Music-Pack`. Copy that mod folder
into your B42 mods directory alongside ApocalipseBRRadio, enable both, and tune
an equipped/world/vehicle radio to 94.2 FM. The build script preserves the B42
layout instead of using the template's former B41 PZ Studio packager.

The Lua tests load the actual ApocalipseBRRadio source through Fengari and
simulate registry/protocol behavior, channel ownership, deferred message order,
scheduled transmission fairness, independent frequencies,
lyrics and gaps, duplicate/stale packets, late joining, retuning, muting, range,
deafness, lost signal, and song/talk scheduling. They do not exercise Kahlua,
Java interop, FMOD playback, split-screen audio isolation, or multiplayer latency.
Before publishing, verify those in-game, including a second client tuning in
mid-song, battery/power loss, moving away from a world radio, and song transitions.
They locate the framework at the Workshop path used for this development;
set `ABR_RADIO_MOD` to a different framework mod root when needed. Install the
updated framework together with the rebuilt music pack; an older framework does
not provide the new registration/playback contract.

## Engine evidence and limits

Verified against the local decompiled B42 source:

- `zombie/radio/ZomboidRadio.java`, `SendTransmission` / `DistributeTransmission`:
  wave packets carry text, GUID and effect codes, not music files or sample data.
- `zombie/network/packets/WaveSignalPacket.java`: non-null empty text and codes
  are serialized independently; native receive handling delivers effect codes.
- `zombie/radio/devices/WaveSignalDevice.java`, `inventory/types/Radio.java`,
  `iso/objects/IsoWaveSignal.java`, `vehicles/VehiclePart.java`: reception triggers
  `OnDeviceText(guid, codes, x, y, z, text, device)`.
- `zombie/audio/BaseSoundEmitter.java`: exposed playback, local stop, volume,
  position and emitter tick; `setTimelinePosition(long, String)` takes a named
  marker, not a numeric position for ordinary audio files. No exposed numeric
  file seek was found. Therefore the implementation uses chunks.
- `zombie/iso/IsoWorld.java`: free emitters, explicit ownership and recycling.
- `zombie/GameTime.java`: `getRealworldSecondsSinceLastUpdate()` is independent
  of the game-time speed multiplier, so faster game time does not skip songs.

There is no engine audio broadcast/finished callback here. The server uses the
duration measured from the source audio; it does not wait on individual clients'
FMOD handles. Restarting the server starts a new song rather than restoring a
partly played broadcast. In local split-screen, headphone/private audio uses a
shared process mixer and cannot provide independent physical audio outputs.
