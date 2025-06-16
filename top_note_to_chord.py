import fretboardgtr as fr
from fretboardgtr.fretboard import FretBoard, FretBoardConfig
from fretboardgtr.notes_creators import ScaleFromName
import os
import numpy as np
from chord_difficulty_scorer import ChordDifficultyScorer
from collections import Counter

def count_nones(t):
    return sum(i is None for i in t)

def fingering_to_relroot(fingering, root):
    notes = []
    for istring, idx in enumerate(fingering):
        if idx is not None:
            notes.append(fr.utils.note_to_interval(fr.utils.get_note_from_index(idx, TUNING[istring]), root))
        else:
            notes.append(None)
    return notes

def is_optional_bad_fingering(chord_name, fingering, optional_notes, root):
    trivial_all_optional = {None} | set(optional_notes[chord_name])
    fingering_relroot = set(fingering_to_relroot(fingering, root)[:-1])
    is_bad_fingering = fingering_relroot <= trivial_all_optional
    #if fingering == [None, 4, 4, 6, 7, None]:
    #    print("BADBAD???", is_bad_fingering, fingering_relroot, trivial_all_optional)
    return is_bad_fingering

os.makedirs('svgs',exist_ok=True)

TUNING = ["E", "A", "D", "G", "B", "E"]
config = {
    "general": {
        "first_fret": 2,
        "last_fret": 10,
        "show_tuning": False,
        "show_frets": True,
        "show_note_name": False,
        "show_degree_name": True,
        "open_color_scale": True,
        "fretted_color_scale": True,
        "fretted_colors": {
            "root": "rgb(255,255,255)",
            "diminished_fifth": "rgb(100,100,100)",
        },
        "open_colors": {
            "root": "rgb(255,255,255)",
        },
        "enharmonic": True,

    },
    #"background": {"color": "rgb(0,0,50)", "opacity": 0.4},
    #"frets": {"color": "rgb(150,150,150)"},
    #"fret_numbers": {"color": "rgb(150,150,150)", "fontsize": 20, "fontweight": "bold"},
    #"strings": {"color": "rgb(200,200,200)", "width": 2},
}

# base chords
base_chords = {
"major":[0,4,7],
"minor":[0,3,7],
"dim":[0,3,6],
"aug":[0,4,8],
"major7":[0,4,7,11],
"minor7":[0,3,7,10],
"minor7flat5":[0,3,6,10],
"minormajor7":[0,3,7,11],
"major7aug":[0,4,8,11],
"dim7":[0,3,6,9],
"dom7":[0,4,7,10],
"dom7sus":[0,5,7,10],
"dom7aug":[0,4,8,10],
}

optional_notes = {
"major":[0,7],
"minor":[0,7],
"dim":[0],
"aug":[0],
"major7":[0,7],
"minor7":[0,7],
"minor7flat5":[0],
"minormajor7":[0],
"major7aug":[0],
"dim7":[0],
"dom7":[0,7],
"dom7sus":[0,7],
"dom7aug":[0],
}

tension_notes = {
"major":[1,2,3,5,6,8,9,10,11],
"minor":[2,5,6,8,9,10],
"dim":[2,5,8,9,11],
"aug":[1,2,3,6,9,10,11],
"major7":[2,6,9],
"minor7":[2,5,9],
"minor7flat5":[2,5,8],
"minormajor7":[2,5,9],
"major7aug":[2,6],
"dim7":[2,5,8,11],
"dom7":[1,2,3,6,8,9],
"dom7sus":[1,2,3,4,8,9],
"dom7aug":[1,2,3,6,9],
}

# top note pos relative to the base chord root
# key is base chord, value is the set of top notes
top_notes = {}
for k in base_chords.keys():
    top_notes[k] = sorted(list(set(base_chords[k] + tension_notes[k])))

NOTE_NAME = fr.constants.CHROMATICS_NOTES


for chord_name, chord_notes_relroot in base_chords.items():
    for i, top_note_pos in enumerate(top_notes[chord_name]):
        top_to_root_interval = fr.constants.CHROMATICS_INTERVALS[top_note_pos]
        fretboard_config = FretBoardConfig.from_dict(config)
        fretboard = FretBoard(config=fretboard_config)
        top = NOTE_NAME[0]
        root = NOTE_NAME[(-top_note_pos) % 12]
        chord_relroot = [chord_note for chord_note in base_chords[chord_name]]

        chord = [NOTE_NAME[(chord_note-top_note_pos) % 12] for chord_note in chord_relroot]

        print(f'{chord_name} chord: ', chord, base_chords[chord_name])
        container = fr.notes_creators.NotesContainer(root,chord)
        fingerings = container.get_chord_fingerings(tuning=TUNING, max_spacing=4, min_notes_in_chord=2, number_of_fingers=4)
        cand_fgs_loss = dict()
        for fg in fingerings:
            fg_with_top_complete = fg[:-1] + [5]
            fg_none_cands = set()
            for first_none in range(5):
                for second_none in range(first_none+1,6):
                    fg_with_top = fg_with_top_complete[:]
                    if not is_optional_bad_fingering(chord_name, fg_with_top, optional_notes, root):
                        fg_none_cands.add(tuple(fg_with_top))

                    if count_nones(fg_with_top) < 2:
                        fg_with_top[first_none] = None
                        if not is_optional_bad_fingering(chord_name, fg_with_top, optional_notes, root):
                            fg_none_cands.add(tuple(fg_with_top))
                    else:
                        continue

                    if count_nones(fg_with_top) < 2:
                        fg_with_top[second_none] = None
                        if not is_optional_bad_fingering(chord_name, fg_with_top, optional_notes, root):
                            fg_none_cands.add(tuple(fg_with_top))
                    else:
                        continue
            #if chord_name == 'minor' and top_to_root_interval == '1':
            #    print('NONENONE', fg_none_cands)

            for fg_with_top in fg_none_cands:
                numbers = np.array([n for n in fg_with_top if n is not None])
                if np.all(numbers>=3) and np.all(numbers<=8) and count_nones(fg_with_top) <= 3:
                    scorer = ChordDifficultyScorer(fg_with_top)
                    difficulty, _ = scorer.analyze()
                    if difficulty < 9999:
                        cand_fgs_loss[tuple(fg_with_top)] = difficulty
                    #if chord_name == 'major' and top_note_pos == 7:
                    #    print('major fingering', fg)
                    #    print('major chord', chord, chord_relroot, flag_optional)
                    #if numbers[-4:].tolist() == [7,5,6,5]:
                    #    print("################################", difficulty, numbers)
        if not cand_fgs_loss:
            print(f'{chord_name} top note {top_to_root_interval} search failed!')
            pass
        else:
            best_fingering = min(cand_fgs_loss, key=lambda x:cand_fgs_loss[x])
            print(chord_name, best_fingering)

            fretboard.add_note(0, top)
            #fretboard.add_notes(scale=container)
            fretboard.add_fingering(list(best_fingering), root=root)
            fretboard.export(f"svgs/{chord_name}_{top_to_root_interval}.png", format="png")
