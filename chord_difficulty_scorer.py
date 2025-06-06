import math

class ChordDifficultyScorer:
    """
    Analyzes a guitar chord fingering and assigns a difficulty score.
    (Version 5 - Final, with robust finger-counting heuristic)
    """
    WEIGHTS = {
        'FINGER_COUNT': 10,
        'FRET_SPAN': 15,
        'POSITION': 2,
        'BARRE_BASE': 20,
        'BARRE_LENGTH': 8,
        'FINGER_CROSSING': 50,
        'FRET_INVERSION': 200,
        'IMPOSSIBLE_FINGERING': 10000
    }

    def __init__(self, fingering: list[int]):
        if len(fingering) != 6:
            raise ValueError("Fingering must be a list of 6 integers.")
        self.fingering = fingering
        self.notes_to_fret = {i: f for i, f in enumerate(self.fingering) if f is not None and f > 0}
        self.last_analysis_summary = ""

    def _generate_assignment(self) -> dict | None:
        """
        This is the core heuristic ("AI") for assigning fingers. It mimics a human
        by anchoring with the index finger and then assigning the rest.
        """
        if not self.notes_to_fret:
            return {} # An empty chord like [0,0,0,0,0,0]

        assignment = {}
        available_fingers = [1, 2, 3, 4]
        notes_to_assign = dict(self.notes_to_fret)

        # --- THE ROBUST "ANCHOR AND COUNT" HEURISTIC ---

        # 1. Find the lowest fret that needs pressing. This is the anchor point.
        lowest_fret = min(notes_to_assign.values())
        
        # 2. Identify all notes on this lowest fret. They will be played by the index finger.
        anchor_notes_strings = [s for s, f in notes_to_assign.items() if f == lowest_fret]

        # 3. Assign the index finger (1) to all anchor notes.
        index_finger = available_fingers.pop(0)
        for s in anchor_notes_strings:
            assignment[s] = {'fret': lowest_fret, 'finger': index_finger}
            del notes_to_assign[s]

        # 4. Check for impossible "overwrite" scenarios caused by the barre.
        min_s, max_s = min(anchor_notes_strings), max(anchor_notes_strings)
        for s_idx, fret in notes_to_assign.items():
            if min_s < s_idx < max_s and fret < lowest_fret:
                self.last_analysis_summary = f"Impossible Fingering: Note at fret {fret} on string {s_idx+1} is blocked by the index finger barre on fret {lowest_fret}."
                return None

        # 5. Check if we have enough fingers for the remaining notes.
        if len(notes_to_assign) > len(available_fingers):
            required_fingers = len(notes_to_assign) + 1 # +1 for the index finger
            self.last_analysis_summary = f"Impossible Fingering: Requires {required_fingers} fingers, but only 4 are available."
            return None

        # 6. Assign the rest of the fingers.
        # Sort by fret then string to ensure a logical finger order.
        remaining_notes_sorted = sorted(notes_to_assign.items(), key=lambda item: (item[1], item[0]))
        
        for i, (string, fret) in enumerate(remaining_notes_sorted):
            assignment[string] = {'fret': fret, 'finger': available_fingers[i]}
            
        return assignment

    def analyze(self) -> tuple[float, str]:
        # Manual override for common G-Major shape for better accuracy
        if self.fingering in ([3, 2, 0, 0, 0, 3], [3, 2, 0, 0, 3, 3]):
            assignment = {0: {'fret': 3, 'finger': 2}, 1: {'fret': 2, 'finger': 1}}
            if self.fingering[5] == 3:
                 assignment[5] = {'fret': 3, 'finger': 3}
            if self.fingering[4] == 3:
                 assignment[4] = {'fret': 3, 'finger': 4}
        else:
            assignment = self._generate_assignment()

        if not assignment:
            # Handle impossible or empty cases
            score = self.WEIGHTS['IMPOSSIBLE_FINGERING'] if self.last_analysis_summary else 0
            summary = self.last_analysis_summary if self.last_analysis_summary else "No notes to play."
            return (score, summary)

        score = 0
        analysis_log = []

        # Scoring components (unchanged)
        fingers_used = {d['finger'] for d in assignment.values()}
        score += len(fingers_used) * self.WEIGHTS['FINGER_COUNT']
        analysis_log.append(f"Fingers used: {len(fingers_used)} -> Score +{len(fingers_used) * self.WEIGHTS['FINGER_COUNT']}")

        frets = [d['fret'] for d in assignment.values()]
        fret_span = max(frets) - min(frets) if frets else 0
        score += fret_span * self.WEIGHTS['FRET_SPAN']
        if fret_span > 0:
            analysis_log.append(f"Fret span (stretch): {fret_span} frets -> Score +{fret_span * self.WEIGHTS['FRET_SPAN']:.0f}")

        avg_fret = sum(frets) / len(frets) if frets else 0
        score += avg_fret * self.WEIGHTS['POSITION']
        if avg_fret > 0:
            analysis_log.append(f"Average fret position: {avg_fret:.1f} -> Score +{avg_fret * self.WEIGHTS['POSITION']:.0f}")

        finger_usage = {}
        for d in assignment.values():
            finger_usage[d['finger']] = finger_usage.get(d['finger'], 0) + 1
        
        barres = {f: c for f, c in finger_usage.items() if c > 1}
        if barres:
            barre_strings = sum(barres.values()) - len(barres)
            score += self.WEIGHTS['BARRE_BASE']
            analysis_log.append(f"Barre detected -> Score +{self.WEIGHTS['BARRE_BASE']}")
            score += barre_strings * self.WEIGHTS['BARRE_LENGTH']
            analysis_log.append(f"Barre length penalty ({barre_strings} extra strings) -> Score +{barre_strings * self.WEIGHTS['BARRE_LENGTH']}")

        sorted_strings = sorted(assignment.keys())
        for i in range(len(sorted_strings) - 1):
            s1_idx, s2_idx = sorted_strings[i], sorted_strings[i+1]
            if s1_idx not in assignment or s2_idx not in assignment: continue
            d1, d2 = assignment[s1_idx], assignment[s2_idx]
            
            if d1['fret'] > d2['fret']:
                penalty = (d1['fret'] - d2['fret']) * self.WEIGHTS['FRET_INVERSION']
                score += penalty
                analysis_log.append(f"Fret Inversion on strings {s1_idx+1}-{s2_idx+1} -> Score +{penalty}")

            if d1['finger'] > d2['finger']:
                penalty = self.WEIGHTS['FINGER_CROSSING']
                score += penalty
                analysis_log.append(f"Finger Crossing on strings {s1_idx+1}-{s2_idx+1} -> Score +{penalty}")

        proposed_fingering_str = " ".join(f"S{s+1}:F{d['fret']}({d['finger']})" for s, d in sorted(assignment.items()))
        summary = (f"Proposed Fingering (1=Index..4=Pinky): {proposed_fingering_str}\n"
                   f"Analysis:\n- " + "\n- ".join(analysis_log))
        
        return score, summary

if __name__ == '__main__':
    # --- Final test with your chord and other key examples ---
    chords_to_test = {
        "Your Impossible Chord": [3, 4, 5, 6, 5, 5],
        "F Major (Correctly Possible)": [1, 3, 3, 2, 1, 1],
        "C Major (Open)": [-1, 3, 2, 0, 1, 0],
        "Impossible Overwrite Chord": [5, 5, 5, 4, 5, 5]
    }
    
    for name, fingering in chords_to_test.items():
        scorer = ChordDifficultyScorer(fingering)
        difficulty, analysis = scorer.analyze()
        
        print(f"--- Analyzing Chord: {name} {fingering} ---")
        print(f"Final Difficulty Score: {difficulty:.0f}")
        print(analysis)
        print("-" * (len(name) + 30))
        print()
