# Boundary-aware speaker consistency audit

## Result

The Shaman provides a small, machine-supported positive control; Sintel remains a documented challenging case. This is a pipeline demonstration, not a verified training dataset or a measured speaker-identification accuracy benchmark.

Four Shaman utterances meet the exploratory boundary, duration, and acoustic gates in both anchor configurations:

- srt_003: 2.936 seconds of VAD-positive speech, non-enrolled candidate.
- srt_007: 2.360 seconds, enrollment anchor, scored leave-one-out.
- srt_009: 2.128 seconds, enrollment anchor, scored leave-one-out.
- srt_011: 2.168 seconds, non-enrolled candidate.

Total: 9.592 seconds of model-detected speech. Enrollment accounts for 4.488 seconds. The two non-enrolled candidates account for 5.104 seconds. They are withheld from reference centroids, but are not human-labeled independent test data; both still come from the same film. All retain unknown overlap and training_ready=false.

The original experiment's 10 Shaman passing caption windows included two enrollment anchors and eight non-enrolled candidates. Do not report those as 10 independent positive results or compare raw caption seconds with VAD seconds without labeling the difference.

## Boundary correction changed the explanation

Independent Whisper tiny.en decoding found “Thank you” for srt_005 in stereo, center, and neural vocals. Silero found contextual center speech at 124.978–125.482 seconds; only 0.276 seconds falls within the original caption window. The earlier low-energy finding applied to that caption crop. It did not establish absent speech, a false subtitle, or an incorrect Sintel role label.

Several utterances begin before their caption starts. The earlier constant video/master offset correction alone could not fix those utterance-specific caption delays. Full-context VAD and phrase evidence are therefore necessary to avoid truncating speech. The boundary proposals remain machine estimates, not audited word alignment.

## V2 protocol

protocol-v2.json was written before computing V2 embeddings. The original protocol, verification.json, and REPORT.md remain unchanged.

1. Use accepted boundary-audit/boundary-proposals.json regions, matched from independently decoded ASR and contextual VAD. Concatenate accepted regions without added silence. Store their source sample coordinates.
2. For rejected boundary proposals, compute available diagnostic embeddings only from contextual VAD clipped to the old caption window. These can still truncate early speech and are never automatically admitted.
3. Compare center-channel and stereo-mono embeddings separately. Keep cosine >= 0.35 and role-margin >= 0.10 unchanged. Both views must favor the scene-attributed role.
4. Require an accepted boundary proposal and at least 2.0 seconds of VAD-positive speech for full admission. This is stricter than the original caption-duration gate; short consistent utterances remain quarantined.
5. Run two disclosed anchor configurations. The fixed-original configuration keeps Sintel 013/014 and Shaman 007/009. The ASR-supported alternative uses Sintel 008/012/020, selected before V2 scores by exact multiword ASR matches and scene context, while retaining Shaman 007/009.
6. Sintel 012 contributes 2.008 VAD-positive seconds; 008 plus 020 form a composite 2.640-second reference spanning two utterances. This does not establish two individually >= 2-second Sintel anchors. Reference prototypes average utterance embeddings. Any enrolled utterance is left out when scoring itself and excluded from non-enrolled counts.
7. Where neural stems exist, compute extra scores against center prototypes as explicitly cross-condition diagnostics. These do not replace failed primary gates.

Changing Sintel enrollment after inspecting the first experiment makes this follow-up exploratory. It is not an untouched benchmark and must not be used to claim an unbiased error rate. Thresholds remain uncalibrated engineering gates, not identity probabilities.

## Detailed contrast

Shaman's result is stable across both enrollment configurations:

- srt_003 cosine to Shaman: 0.656 center / 0.625 stereo.
- srt_011: 0.551 / 0.498.
- Shaman anchors 007 and 009 mutually score 0.438 / 0.404 under leave-one-out.
- 001, 002, and 004 are quarantined because automatic boundary repair lacks sufficiently good ASR phrase agreement, not because their speaker similarity proves incorrect attribution.
- 006 is short and lacks an admitted boundary proposal. 021, 022, and 023 remain below the 2-second speech-duration gate despite useful transcript and acoustic evidence.

Sintel has no full-gate V2 pass:

- Alternative anchors improve 008 to 0.452 / 0.423 under leave-one-out, but its detected speech is only 1.464 seconds.
- 012 has 2.008 detected seconds but is channel-sensitive: 0.352 center / 0.287 stereo under alternative-anchor leave-one-out.
- 014 is consistent with the fixed treatment-scene reference, at 0.379 / 0.367, but only 1.528 detected seconds. Against the alternative reference, it is 0.352 / 0.285.
- 016 has a 2.104-second neural-supported boundary proposal, but similarities remain low in center, stereo, and the supplementary neural-vocal condition. Separation does not establish speaker identity.
- Short calls and other rejected proposals remain visible in verification-v2.json rather than being silently removed from evaluation coverage.

## What is and is not established

This run actually processed waveform-derived pretrained speaker embeddings, contextual neural VAD, and independent ASR. It supports a finite four-utterance Shaman control and a transparent Sintel failure case under these gates. It does not establish absence of overlapping speech, clean source separation, human-confirmed spoken duration, transcript accuracy, label accuracy, or training readiness. A VAD-positive interval may include noise or missed/extra speech. Center/stereo are related views, not independent recordings.

No identities were inferred beyond published fictional role credits. No model training, voice cloning, private voice database, or external upload of embeddings was performed. Keep embeddings-v2-local-only.npz, model weights, and dependency directories out of public deliverables.

## Reproduction and handoff

- Full results: verification-v2.json (all 26 IDs in both configurations).
- Frozen rules: protocol-v2.json.
- Code: verify_v2.py, reusing the previously downloaded official ECAPA checkpoint with weights_only=True.
- Upstream evidence: boundary-audit/audit.json and boundary-audit/boundary-proposals.json; the latter's SHA256 is recorded in the result.
- Original data and first experiment were not overwritten.

The downstream dataset should retain source sample coordinates, the two enrollment IDs, the two non-enrolled candidate IDs, exact machine-detected duration, and all unknown-overlap/training flags. These findings warrant a modest demo, not a claim of a clean large character-voice dataset.
