import math
import numpy as np
from itertools import combinations
from collections import Counter

class ChordDifficultyScorer:
    """
    Analyzes a guitar chord fingering and assigns a difficulty score.
    (Version 12 - With Internal Stretch Variance analysis)
    """
    WEIGHTS = {
        'FINGER_COUNT': 10, 'FRET_SPAN': 25, 'POSITION': 2, 'BARRE_BASE': 20,
        'BARRE_LENGTH': 10, 'FRET_INVERSION': 400,
        'INTERNAL_STRETCH_VARIANCE': 300, # New, powerful penalty for hand contortion
        'IMPOSSIBLE_FINGERING': 10000
    }
    MAX_FRET_SPAN = 4

    def __init__(self, fingering: list[int]):
        if len(fingering) != 6:
            raise ValueError("Fingering must be a list of 6 integers.")
        self.fingering = [f if f is not None else -1 for f in fingering]
        self.notes_to_fret = {i: f for i, f in enumerate(self.fingering) if f > 0}

    def _find_best_fingering(self):
        """Finds the most plausible fingering based on a barre-centric heuristic."""
        if not self.notes_to_fret:
            return None, "No notes to play."

        assignment = {}
        available_fingers = [1, 2, 3, 4]
        notes_to_assign = dict(self.notes_to_fret)
        lowest_fret = min(notes_to_assign.values())
        counts_repeat = Counter(notes_to_assign.values())
        barred_fret = max(counts_repeat, key=counts_repeat.get)

        # Hard Rule: No notes can be below the barre fret
        if counts_repeat[barred_fret] >= 4 and any(f < barred_fret for f in notes_to_assign.values()):
            return None, f"Impossible: Note on fret {min(notes_to_assign.values())} is blocked by barre on fret {barred_fret}."

        index_finger = available_fingers.pop(0)
        anchor_strings = [s for s, f in notes_to_assign.items() if f == lowest_fret]
        for s in anchor_strings:
            assignment[s] = {'fret': lowest_fret, 'finger': index_finger}
            del notes_to_assign[s]
        
        # Hard Rule: Must have enough fingers for the rest
        if len(notes_to_assign) > len(available_fingers):
            return None, f"Impossible: Requires {len(notes_to_assign) + 1} fingers."

        remaining_sorted = sorted(notes_to_assign.items(), key=lambda item: (item[1], item[0]))
        for i, (s, f) in enumerate(remaining_sorted):
            assignment[s] = {'fret': f, 'finger': available_fingers[i]}
        
        return assignment, ""

    def analyze(self):
        """The main analysis function."""
        assignment, reason = self._find_best_fingering()

        if not assignment:
            return self.WEIGHTS['IMPOSSIBLE_FINGERING'], reason

        score, analysis = self._calculate_score(assignment)
        
        # Final check for hard limits
        frets = [d['fret'] for d in assignment.values()]
        if max(frets) - min(frets) > self.MAX_FRET_SPAN:
             return self.WEIGHTS['IMPOSSIBLE_FINGERING'], f"Impossible Stretch: Fret span of {max(frets) - min(frets)}."

        return score, analysis

    def _calculate_score(self, assignment):
        """Calculates the score for a given fingering."""
        score = 0
        analysis_log = []

        # --- Ergonomic Penalties ---
        fingers_used = len({d['finger'] for d in assignment.values()})
        score += fingers_used * self.WEIGHTS['FINGER_COUNT']
        analysis_log.append(f"Fingers used: {fingers_used}")

        frets = [d['fret'] for d in assignment.values()]
        fret_span = max(frets) - min(frets)
        score += fret_span * self.WEIGHTS['FRET_SPAN']
        if fret_span > 0: analysis_log.append(f"Fret span (stretch): {fret_span} frets")
        
        avg_fret = sum(frets) / len(frets)
        score += avg_fret * self.WEIGHTS['POSITION']
        analysis_log.append(f"Average fret position: {avg_fret:.1f}")

        # --- NEW: Internal Stretch Variance Penalty ---
        non_barre_frets = [d['fret'] for d in assignment.values() if d['finger'] != 1]
        if len(non_barre_frets) > 1:
            internal_variance = np.std(non_barre_frets)
            if internal_variance > 0:
                variance_penalty = internal_variance * self.WEIGHTS['INTERNAL_STRETCH_VARIANCE']
                score += variance_penalty
                analysis_log.append(f"Internal Stretch Variance: {internal_variance:.2f} -> Penalty +{variance_penalty:.0f}")

        # Barre penalties
        finger_usage = {}
        for d in assignment.values():
            finger = d['finger']
            if finger not in finger_usage:
                finger_usage[finger] = []
            finger_usage[finger].append(d['fret'])
        
        barre_fingers = [f for f, frets_list in finger_usage.items() if len(frets_list) > 1]
        if barre_fingers:
            barre_strings = sum(len(finger_usage[f]) - 1 for f in barre_fingers)
            score += self.WEIGHTS['BARRE_BASE'] * len(barre_fingers)
            analysis_log.append(f"Barre detected")
            score += barre_strings * self.WEIGHTS['BARRE_LENGTH']
            analysis_log.append(f"Barre length penalty ({barre_strings} extra strings)")

        # Fret Inversion Penalty
        sorted_notes = sorted(assignment.items(), key=lambda item: item[0])
        for (s1, d1), (s2, d2) in combinations(sorted_notes, 2):
            if d1['fret'] > d2['fret']:
                inversion_penalty = (d1['fret'] - d2['fret']) * self.WEIGHTS['FRET_INVERSION']
                score += inversion_penalty
                analysis_log.append(f"Hand Contortion: S{s1+1}:F{d1['fret']} over S{s2+1}:F{d2['fret']} -> Penalty +{inversion_penalty:.0f}")

        proposed_fingering_str = " ".join(f"S{s+1}:F{d['fret']}({d['finger']})" for s, d in sorted(assignment.items()))
        summary_text = (f"Proposed Fingering (1=Index..4=Pinky): {proposed_fingering_str}\n"
                   f"Analysis:\n- " + "\n- ".join(analysis_log))
        
        return score, summary_text

if __name__ == '__main__':
    # --- Testing your two chords ---
    chords_to_test = {
        "Your 'Easier' Chord": (6, None, 5, 6, 5, 5),
        "Your 'Harder' Chord": (6, None, 5, 6, 8, 5),
    }
    
    for name, fingering in chords_to_test.items():
        scorer = ChordDifficultyScorer(fingering)
        difficulty, analysis = scorer.analyze()
        
        print(f"--- Analyzing Chord: {name} {fingering} ---")
        print(f"Final Difficulty Score: {difficulty if isinstance(difficulty, int) else difficulty:.0f}")
        print(analysis)
        print("-" * (len(name) + 30))
        print()
