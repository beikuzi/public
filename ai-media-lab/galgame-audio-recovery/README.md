# Original-engine audio capture reproduction

This historical experiment used an isolated Linux desktop session. It does not alter the system audio server, global default device, firewall, OS permissions, desktop security, or immutable Ren'Py SDK. Do not run these desktop capture commands in an execution context that lacks desktop/audio access, and do not bypass such restrictions.

## Root cause

The original desktop has no ALSA device (`/dev/snd` absent) and no PulseAudio/PipeWire service. Ren'Py's normal audio initialization therefore failed and fell back to its dummy driver. The historical FFmpeg scripts also specified `-an`, which omits audio entirely. Original game script plays `illurock.opus`; the game itself is not inherently silent.

## Runtime path

Ren'Py SDL PulseAudio output → private ephemeral PulseAudio `game_only` null sink → `game_only.monitor` → FFmpeg AAC, captured concurrently with the real X11 game window. No source-music file is an FFmpeg input to the delivered recording. Synthetic testing is separately labelled and excluded from deliverables.

## Dependencies

Official Debian package downloads, SHA256 compared to packages.debian.org:
- https://packages.debian.org/trixie/amd64/pulseaudio/download
- https://packages.debian.org/trixie/amd64/pulseaudio-utils/download
- https://packages.debian.org/trixie/amd64/libspeexdsp1/download

Packages were extracted to the workspace, not system-installed. Package hashes and licence manifests were checked for the original experiment; no dependencies or runtime configuration are included in this public note. Upstream source packages are available from the linked official package pages. Executables, game assets, saved games, authentication files and runtime sockets are not included in this reproduction bundle. Existing FFmpeg and the official Ren'Py SDK were used without modification.

## Final verified media

The verified MP4 is 1,672,408 bytes, with SHA256 `974ede519a88972ab56752b9eb0096fc22c555c96600107f7a4eeba8520a88ac`. Its H.264 1280×720 video contains **1,139 frames in 38.000 seconds**, with nominal 30 fps and measured average **1139/38 ≈ 29.973684 fps**. It is not represented as 1,140 frames or verified strict CFR 30. AAC-LC stereo audio is 48 kHz with a 38.000-second stream timeline.

Stereo volumedetect measured −22.1 dBFS mean and −7.3 dBFS peak. No silence events reached 0.3 seconds below −50 dBFS. Independent decode completed without errors, and visual samples showed the expected lead-in, dialogue and proposal without unrelated window overlays.

The 2-second source-comparison segments at capture offsets 9, 17, 25 and 33 seconds scored at least 0.997431. The segment at offset 1 second crosses the music loop boundary and scored 0.664673. That diagnostic limitation is retained; not all segments were near-perfect matches.

## Validation limits

Correlation to the original decoded music verifies the recorded sound source and progression. Container duration/PTS checks verify stream timelines. The 0.048327-second input-start timestamp difference is not a measured end-to-end A/V skew. Decoded AAC framing can span 38.016 seconds while its stream timeline remains 38.000 seconds. Mono 8 kHz correlation-analysis levels use a different measurement method from stereo volumedetect. This BGM-only scene does not establish speech/lip sync; no human listening test is claimed. The retained short scene test has a known tail issue; use the cleaned 7-second sample or full scene deliverable instead. An early full-length attempt also used a stale screenshot marker and was retained separately; it is not the deliverable. The final capture fails fast if the explicit checkpoint timing marker does not refresh.

## Source-only closeout · 2026-10-06

This note records a completed historical capture and its limitations. Environment-bound shell scripts, audio daemon configuration, process/window identifiers, save profiles, authentication material, screenshots and recordings are not published. No capture was rerun during closeout. This is not a portable one-command recorder or a universal visual-novel validation result.
