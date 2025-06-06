import fretboardgtr as fr
from fretboardgtr.fretboard import FretBoard, FretBoardConfig
from fretboardgtr.notes_creators import ScaleFromName
import os
import numpy as np
from chord_difficulty_scorer import ChordDifficultyScorer

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

chord_tension_structures = {
"major7":[0,4,7,11],
"minor7":[0,3,7,10],
"minor7flat5":[0,3,6,10],
"minormajor7":[0,3,7,11],
"major7aug":[0,4,8,11],
"dim":[0,3,6,9],
"dom7":[0,4,7,10],
"dom7sus":[0,5,7,10],
"dom7aug":[0,4,8,10],

"major7_tensions":[2,6,9],
"minor7_tensions":[2,5,9],
"minor7flat5_tensions":[2,5,8],
"minormajor7_tensions":[2,5,9],
"major7aug_tensions":[2,6],
"dim_tensions":[2,5,8,11],
"dom7_tensions":[1,2,3,6,8,9],
"dom7sus_tensions":[1,2,3,4,8,9],
"dom7aug_tensions":[1,2,3,6,9],
}

ALL = fr.constants.CHROMATICS_NOTES


for k,v in chord_tension_structures.items():
    for i, interval in enumerate(v):
        fretboard_config = FretBoardConfig.from_dict(config)
        fretboard = FretBoard(config=fretboard_config)
        top = ALL[0]
        root = ALL[(-interval) % 12]
        if 'tensions' in k:
            chord_name = k.removesuffix('_tensions')
        else:
            chord_name = k
        chord = [ALL[(i-interval) % 12] for i in chord_tension_structures[chord_name]]
        container = fr.notes_creators.NotesContainer(root,chord)
        fingerings = container.get_chord_fingerings(TUNING)
        cand_fgs_loss = dict()
        for fg in fingerings:
            fg_with_top = fg[:-1] + [5]
            numbers = np.array([n for n in fg_with_top if n is not None])
            if np.all(numbers>=3) and np.all(numbers<=9):
                scorer = ChordDifficultyScorer(fg_with_top)
                difficulty, _ = scorer.analyze()
                cand_fgs_loss[tuple(fg_with_top)] = difficulty

            #number_none = sum([n is None for n in fg_with_top])
            #if number_none == 0:
            #    numbers = np.array([n for n in fg_with_top if n is not None])
            #    if np.all(numbers>=3) and np.all(numbers<=9):
            #        min_n = np.min(numbers)
            #        max_n = np.max(numbers)
            #        range_pos = max_n - min_n
            #        number_collinear = np.sum(numbers == min_n)
            #        loss = 4*range_pos - number_collinear
            #        cand_fgs_loss[tuple(fg_with_top)] = loss
        best_fingering = min(cand_fgs_loss, key=lambda x:cand_fgs_loss[x])
        print(k, best_fingering)

        fretboard.add_note(0, top)
        #fretboard.add_notes(scale=container)
        fretboard.add_fingering(list(best_fingering), root=root)
        fretboard.export(f"svgs/{k}_{i}.svg", format="svg")
