# ============================================================================
# workflows/dialog_archetypes.py - Archetype Rhetorical Profiles (Phase 4)
# ============================================================================
"""
Maps archetype IDs to rhetorical profiles that shape how characters speak.

Each profile defines:
- argument_style: How they make their case
- disagreement_pattern: How they push back
- deflection_style: How they dodge
- sentence_style: Syntactic fingerprint
- never_does: Things this archetype would never say/do
- signature_moves: Characteristic rhetorical patterns
"""

ARCHETYPE_RHETORICAL_PROFILES = {
    "engineer": {
        "argument_style": "data-first; cites specific measurements; uses conditional logic ('if X then Y')",
        "disagreement_pattern": "asks for the source; names the exact number they dispute; proposes alternative measurement",
        "deflection_style": "redirects to technical subproblem",
        "sentence_style": "short declarative sentences; technical vocabulary; avoids metaphor",
        "never_does": [
            "make emotional appeals",
            "appeal to authority without data",
            "use 'we feel'",
        ],
        "signature_moves": [
            "qualifies estimates with error margins",
            "asks clarifying questions before answering",
        ],
        "voice_anti_exemplar": "The data serves as a testament to the transformative potential of our monitoring systems, showcasing the intricate interplay between sensor readings and operational outcomes.",
    },
    "executive_director": {
        "argument_style": "schedule and budget framing; translates everything to downstream impact; uses 'we' not 'I'",
        "disagreement_pattern": "reframes concern as resource problem; offers to table for future meeting",
        "deflection_style": "elevates ('let's not get into the weeds') or redirects to process",
        "sentence_style": "longer compound sentences; management vocabulary; decisive tone",
        "never_does": [
            "admit uncertainty in front of subordinates",
            "engage with technical details directly",
        ],
        "signature_moves": [
            "ends turns with action items or deadlines",
            "references precedent from past projects",
        ],
        "voice_anti_exemplar": "This initiative serves as a powerful catalyst for innovation, inspiration, and institutional growth, nestled at the intersection of strategic vision and operational excellence.",
    },
    "military_commander": {
        "argument_style": "chain of command framing; weighs mission risk vs. crew safety; speaks in directives",
        "disagreement_pattern": "asks for options not problems; demands alternatives before accepting criticism",
        "deflection_style": "defers to protocol or asks for formal assessment",
        "sentence_style": "crisp, clipped sentences; active voice; minimal hedging",
        "never_does": ["show fear in front of crew", "undermine a subordinate publicly"],
        "signature_moves": [
            "asks 'what are our options' not 'what do we do'",
            "calls for the room before deciding",
        ],
        "voice_anti_exemplar": "In order to fully realize the transformative potential of our mission parameters, we must additionally consider the intricate interplay between crew safety and operational timelines.",
    },
    "scientist": {
        "argument_style": "hypothesis-driven; cites studies and precedent; distinguishes correlation from causation",
        "disagreement_pattern": "questions methodology; asks about sample size and controls; offers alternative explanation",
        "deflection_style": "requests more data before committing to a position",
        "sentence_style": "precise language; hedged claims ('the data suggests'); avoids absolutes",
        "never_does": [
            "claim certainty without evidence",
            "dismiss a finding without methodological critique",
        ],
        "signature_moves": [
            "prefaces claims with confidence level",
            "proposes experiments to resolve disagreement",
        ],
        "voice_anti_exemplar": "These groundbreaking findings serve as a testament to the power of scientific inquiry, showcasing how research can unlock transformative insights and reshape our understanding of complex phenomena.",
    },
    "politician": {
        "argument_style": "constituency framing; appeals to shared values; uses stories and anecdotes",
        "disagreement_pattern": "pivots to adjacent issue; acknowledges concern while redirecting",
        "deflection_style": "broadens scope ('the real question is...') or personalizes ('I hear you')",
        "sentence_style": "rhythmic phrasing; inclusive language ('we all want'); avoids specifics when possible",
        "never_does": ["give a simple yes or no", "take a position without testing the room first"],
        "signature_moves": [
            "triangulates between factions",
            "frames own position as the moderate middle",
        ],
        "voice_anti_exemplar": "This pivotal policy serves as a beacon of hope, marking a transformative moment in governance that showcases our commitment to innovation, inclusion, and institutional excellence.",
    },
    "lawyer": {
        "argument_style": "precedent-based; identifies liability and risk; speaks in if-then consequences",
        "disagreement_pattern": "distinguishes facts from interpretation; asks for documented evidence",
        "deflection_style": "raises procedural objection or requests formal review",
        "sentence_style": "precise, qualified language; defined terms; avoids ambiguity",
        "never_does": ["speculate without qualification", "make promises without conditions"],
        "signature_moves": [
            "summarizes the other side's position before rebutting",
            "identifies the unstated assumption",
        ],
        "voice_anti_exemplar": "The legal landscape continues to evolve, and this ruling serves as a testament to the intricate interplay between precedent and progress, reshaping how practitioners approach liability.",
    },
    "diplomat": {
        "argument_style": "relationship-first; acknowledges all positions before stating own; seeks face-saving solutions",
        "disagreement_pattern": "reframes as misunderstanding; proposes compromise that preserves each side's core interest",
        "deflection_style": "suggests private conversation or defers to bilateral discussion",
        "sentence_style": "measured tone; diplomatic hedging; avoids direct accusation",
        "never_does": ["publicly embarrass another party", "force a binary choice"],
        "signature_moves": [
            "offers the other side a graceful exit",
            "proposes a framework rather than a solution",
        ],
        "voice_anti_exemplar": "This agreement stands as a groundbreaking milestone in international cooperation, nestled at the intersection of diplomacy and progress, showcasing the transformative power of dialogue.",
    },
    "safety_officer": {
        "argument_style": "risk-based; cites regulations and incident history; speaks in worst-case scenarios",
        "disagreement_pattern": "escalates to documented risk; demands written sign-off for exceptions",
        "deflection_style": "defers to regulation ('my hands are tied') or asks for formal waiver",
        "sentence_style": "procedural language; references standards by number; lists consequences",
        "never_does": [
            "sign off on unknown risk without documentation",
            "let schedule pressure override safety",
        ],
        "signature_moves": [
            "asks 'what if this goes wrong?'",
            "requests that objection be entered into the record",
        ],
        "voice_anti_exemplar": "Safety protocols serve as a cornerstone of organizational excellence, and this incident underscores the vital importance of cultivating a culture of awareness, accountability, and continuous improvement.",
    },
    "doctor": {
        "argument_style": "differential diagnosis approach; weighs risks vs benefits; cites clinical experience",
        "disagreement_pattern": "asks what the counter-evidence is; distinguishes anecdote from systemic data",
        "deflection_style": "suggests monitoring before acting; recommends second opinion",
        "sentence_style": "clinical precision mixed with patient-facing warmth; uses analogies for laypeople",
        "never_does": ["guarantee outcomes", "dismiss patient-reported symptoms"],
        "signature_moves": [
            "ranks options by risk profile",
            "checks understanding ('does that make sense?')",
        ],
        "voice_anti_exemplar": "This diagnosis serves as a pivotal moment in the patient's healthcare journey, showcasing the transformative impact of evidence-based medicine on outcomes, well-being, and quality of life.",
    },
    "journalist": {
        "argument_style": "source-based; asks follow-up questions; looks for inconsistencies",
        "disagreement_pattern": "asks 'who told you that?' or 'when did you learn this?'",
        "deflection_style": "claims need for more investigation before commenting",
        "sentence_style": "direct questions; short factual sentences; avoids editorializing in questions",
        "never_does": ["accept a claim at face value", "reveal a source without permission"],
        "signature_moves": [
            "circles back to unanswered questions",
            "asks the same question different ways",
        ],
        "voice_anti_exemplar": "This story serves as a compelling testament to the power of investigative journalism, showcasing how dedicated reporters continue to play a vital role in fostering transparency, accountability, and public trust.",
    },
}


def get_rhetorical_profile(archetype_id: str) -> dict:
    """Look up rhetorical profile for an archetype. Returns empty dict if not found."""
    return ARCHETYPE_RHETORICAL_PROFILES.get(archetype_id, {})
