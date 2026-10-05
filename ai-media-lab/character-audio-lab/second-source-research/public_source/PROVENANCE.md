# Elephants Dream: role-labelled production audio provenance

Research checkpoint: 2026-10-05 UTC.

## What was recovered

An openly downloadable preservation of the original 2006 PAL production DVD contains 20 mono WAV files in its soundbytes directory. The original filenames identify two fictional roles, Proog and Emo. A separate licence file in that same directory specifies Creative Commons Attribution 2.5.

The inventory contains 11 Proog-labelled files and 9 Emo-labelled files. All are PCM 16-bit, 48 kHz, mono. Their file durations total 350.213667 seconds for Proog and 296.297063 seconds for Emo. **Those figures include silence and must not be reported as usable speech duration.**

A complete original stereo film master was independently retrieved from the Xiph collection supplied by the production team. It is 658.32 seconds long, stereo, 48 kHz, 16-bit. Its SHA256 matches Xiph's published checksum.

This checkpoint publishes provenance metadata only. Audio, DVD sectors, video, transcripts, model files and account data are not included.

## Primary-source corroboration

- [Official production-team recording-session account](https://orange.blender.org/blog/talking-heads/): the director describes recording dialogue with Tygo Gernandt as Proog and Cas Jansen as Emo, then using the performances as animation reference.
- [Official film credits](https://orange.blender.org/theteam/): independently identifies those actor/role assignments and credits dialogue editing and audio post-production.
- [Official release and licence notices](https://orange.blender.org/page/2/): describe the movie and DVD production data as Creative Commons Attribution content. Additional standalone score downloads have different restrictions and must not be conflated with the DVD-data licence.
- [Official project website](https://orange.blender.org/): records the production team's delivery of original lossless audio and video to Xiph.
- [Xiph audio collection](https://media.xiph.org/ED/), [master-audio licence/readme](https://media.xiph.org/ED/ED-CM-readme.txt), and [published SHA256 checksums](https://media.xiph.org/ED/SHA256SUMS).

## Preservation source and extraction

The production WAVs were obtained from [Internet Archive's original-DVD preservation item](https://archive.org/details/elephans-dream-iso), specifically [Elephans Dream Disk 1 PAL.ISO](https://archive.org/download/elephans-dream-iso/Elephans%20Dream%20Disk%201%20PAL.ISO). This is a third-party preservation copy, not the contemporary Blender Studio subscription archive.

Small HTTP byte-range reads identified the ISO9660 directory and file records. Each selected WAV and its directory's licence file were then fetched by the recorded byte extent and exact file length. Audio files were preserved without transcoding or sample modification. The companion JSON contains those extents, sizes, sample counts and SHA256 hashes.

The evidence establishes that the filenames are entries in the preserved production DVD. It does not provide a production-team signature authenticating this particular preserved ISO. The file hashes identify the recovered bytes; they are not claims of upstream-signed checksums. Only the stereo film master has additionally been checked against an independently published Xiph SHA256.

## Licence and attribution

The recovered soundbytes-directory licence specifies CC BY 2.5 for the digital files and identifies this attribution:

(c) Copyright 2006, Blender Foundation / Netherlands Media Art Institute / www.elephantsdream.org

The licence also requires the complete credits roll when distributing, screening or broadcasting the movie or documentary itself. Xiph's accompanying readme permits modification and redistribution of its master soundtrack files under CC BY 2.5. See the [CC BY 2.5 licence](https://creativecommons.org/licenses/by/2.5/) and the original notices for applicable terms.

This evidence supports attributed reuse within the stated copyright licence. It does not certify unrelated personality, endorsement or voice-cloning permissions, and this checkpoint does not train or clone an actor's voice.

## Scope and limits of the evidence

The justified source label is **authored role-labelled production WAV**. A role name in a filename is stronger independent identity evidence than a separator's inferred speaker label, but it does not by itself establish acoustic purity.

Before using an excerpt as a clean comparison reference, separately verify:

1. That it contains the indicated role and no unwanted second speaker, music or effects.
2. That the performance actually occurs in the final film, rather than being an unused or preliminary edit.
3. Its alignment to the film master, including any offset, edit boundary, speed change or channel-processing differences.
4. That the chosen boundaries preserve speech and that total duration is not substituted for active speech duration.

Equal-length role pairs may be scene-aligned animation tracks; their local time zero is not established as film time zero. Some files contain long silent intervals. No listening assessment, noise-free certification, final-cut identity or training-readiness conclusion is made by this provenance checkpoint.

The stereo film master is a **mixture**, not a clean dialogue oracle. A centre surround channel is also not automatically a dialogue-only stem. Subtracting a music-and-effects mix cannot establish a clean reference without independent alignment and cancellation validation.
