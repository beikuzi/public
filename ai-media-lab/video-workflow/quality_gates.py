"""Conservative heuristic triage, not calibrated ASR accuracy estimation."""
import unicodedata

def assess(text,segments=None):
 normalized=''.join(c for c in unicodedata.normalize('NFKC',text) if c.isalnum())
 flags=[]
 if not normalized: flags.append('empty_transcript')
 trigrams=[normalized[i:i+3] for i in range(max(0,len(normalized)-2))]
 diversity=len(set(trigrams))/len(trigrams) if trigrams else None
 if len(normalized)>=24 and diversity is not None and diversity<0.35: flags.append('high_repetition_possible_hallucination')
 return {'status':'blocked' if flags else 'unverified_requires_review','blocking_flags':flags,'normalized_characters':len(normalized),'trigram_diversity':diversity,'eligible_as_analysis_input':not bool(flags),'independent_verification_required':True,'warning':'Passing heuristics does not establish correctness; never treat hypothesis as verified fact. Repetition may occasionally be real speech.'}
