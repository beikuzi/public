# Sintel speaker-label acoustic audit

## Decision

Do not treat this as a verified training dataset. All segments remain training_ready=false and overlap=unknown. Frozen pretrained acoustic analysis was actually run, but no human listening, ASR, forced alignment, or overlap detector was used.

Of15 scene-attributed Sintel spans (40.87s of caption windows),13 fail conservative exploratory gates. Only srt_013 and srt_014 pass (6.00s of caption windows), and these two are the enrollment-source pair. Their mutual leave-one-out similarity establishes consistency within one scene, not an independent successful extraction test. Zero non-anchor target examples pass. Ten substantive Shaman spans pass; the brief srt_006 “So...” is quarantined for length.

## Reproducible method

- Official public pretrained SpeechBrain ECAPA-TDNN from https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb, trained on VoxCeleb; Apache2.0 model repository. Model card explicitly disclaims performance warranty on other datasets.
- SpeechBrain1.1.1 from PyPI; Torch2.8 CPU from existing separation environment, read-only. Package dependencies are isolated here. No fitting/training/voice cloning was performed.
- Explicit architecture matching the downloaded YAML, instantiated from installed package, strict state-dict loading with torch.load(weights_only=True). No remote Python model code, no unsafe pickle fallback, no gated credentials.
- Checkpoint SHA256:0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2.
- Decode corrected master-audio caption windows with ffmpeg, independently from51channel2(center) and stereo equal-channel mono downmix. Resample16kHz. 80-bin Fbank, sentence mean normalization,192-D embedding, unit normalization, cosine to enrolled role centroid.
- Sintel anchors:013(207.206–210.456) and014(210.706–213.456), injury-treatment scene. Shaman anchors:007(129.356–133.756) and009(137.956–142.156), wide-shot conversation and Shaman close-up. Static visual inspection and narrative context support labels; no audited lip-sync.
- For each anchor, omit itself from its own role centroid. Anchors were selected before scoring. Frozen protocol.json gates: caption duration>=2s, at least3 lexical words, winner cosine>=.35, margin>=.10, both views agree with scene label. Thresholds are exploratory engineering gates, NOT calibrated accept/reject probabilities or a measured error rate.

## Important falsifiable findings

-013/014 mutual cosine:.456(center),.479(stereo). The apparent6s consists of caption windows; activity above−40dBFS is only1.72s and.72s respectively. That activity statistic is NOT VAD or actual speech duration. We cannot establish>=2s of speech in each anchor.
-005(“Thank you”): center winning role differs from stereo, maximum similarities<.35, center activity only.06s above−40dBFS. Insufficient acoustic evidence; not proof the subtitle/role is wrong.
-010(“A dragon”): near tie, center Sintel.287/Shaman.292 and stereo Sintel.275/Shaman.298. Do not relabel to Shaman based on this.
-008/012 prefer Sintel in both views, but similarities remain below the preregistered exploratory gate. They are not promoted by lowering thresholds post hoc.
-015 reaches.428 to Sintel on center but.323 on stereo; channel sensitivity indicates uncertainty.
-Short calls017/019/024/025/026 remain unsuitable for reliable standalone speaker assignment from these embeddings even when caption windows exceed2s.

## Limits and coverage

Only26 published-caption intervals were analyzed, across one888s film. Uncaptioned speech, cries/grunts, overlapping voices, the singer, and all other time are outside coverage. Center/stereo share the same underlying performance and are not independent observations. The Sintel anchor pair is from one scene with similar recording conditions and may not generalize to whispers, narration, or shouting. Strong Shaman separation does not establish target recall. No label-accuracy, source-separation SDR, actor-identity certainty, absence of overlap, or clean speech duration is claimed.

Published fictional role credits are grounded by the inspected end-credit frames:Sintel/Halina Reijn at766s and Shaman/Thom Hoffman at768.5s, plus the official casting article https://durian.blender.org/news/casting-line-up-thom-hoffman-and-halina-reijn/ . This is within-film role consistency, not identifying private people from voice.

## Next verification that would change the decision

Listen to and precisely annotate several longer clean target utterances across scenes; establish actual voiced duration, boundaries, and overlap; freeze independent enroll/evaluate partitions; then evaluate on withheld manually audited positives and negative distractors. If still only very short expressive calls exist, keep them separate as manual-review clips rather than claiming a general-purpose clean target-speaker dataset. Model scores should remain review aids.

verification.json contains all26 IDs, times, per-view similarities, margins, diagnostics, prospective triage reasons, model/source hashes, and summary. Original target-annotations.json was not changed. embeddings-local-only.npz and model weights are local working files and must not be published with the deliverable.
