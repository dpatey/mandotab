from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict


# =========================
# Data models
# =========================

@dataclass
class NoteEvent:
    """
    Represents a detected musical note from audio.
    """
    start_time: float        # seconds
    end_time: float          # seconds
    midi: int                # 0–127 MIDI pitch
    confidence: float = 1.0  # 0–1, optional


@dataclass
class TabEvent:
    """
    Represents a single note placed on mandolin tablature.
    """
    start_time: float
    end_time: float
    string: int              # 4 = G, 3 = D, 2 = A, 1 = E
    fret: int                # 0 = open
    midi: int                # keep for sanity/debug


# =========================
# Mandolin tuning helpers
# =========================

# Standard mandolin tuning in MIDI (G3, D4, A4, E5).
MANDOLIN_TUNING: Dict[int, int] = {
    4: 55,   # G3
    3: 62,   # D4
    2: 69,   # A4
    1: 76,   # E5
}

MAX_FRET = 20  # tweak as needed


def candidates_for_midi(midi: int) -> List[Tuple[int, int]]:
    """
    Given a MIDI pitch, return all (string, fret) candidates that can play it
    on a standard-tuned mandolin.
    """
    candidates: List[Tuple[int, int]] = []
    for string, open_midi in MANDOLIN_TUNING.items():
        fret = midi - open_midi
        if 0 <= fret <= MAX_FRET:
            candidates.append((string, fret))
    return candidates


def choose_position(
    midi: int,
    prev: Optional[TabEvent]
) -> Optional[Tuple[int, int]]:
    """
    Choose a (string, fret) for the given MIDI note.
    v0 heuristic:
      - If no previous note: pick lowest fret, then lowest string.
      - Otherwise score candidates by small fret moves + small string moves.
    Returns None if note is out of range for standard tuning.
    """
    candidates = candidates_for_midi(midi)
    if not candidates:
        return None

    if prev is None:
        # Lowest fret first, then lowest string
        return sorted(candidates, key=lambda sf: (sf[1], sf[0]))[0]

    def score(sf: Tuple[int, int]) -> float:
        s, f = sf
        dist_fret = abs(f - prev.fret)
        dist_string = abs(s - prev.string)
        # weights are arbitrary for v0; tweak later
        return dist_fret * 1.0 + dist_string * 0.7

    return min(candidates, key=score)


# =========================
# Notes -> Tab
# =========================

def notes_to_tab(note_events: List[NoteEvent]) -> List[TabEvent]:
    """
    Map NoteEvent sequence to TabEvent sequence using simple position heuristics.
    Assumes note_events are monophonic and mostly in time order.
    """
    if not note_events:
        return []

    # Ensure sorted by start_time
    note_events = sorted(note_events, key=lambda n: n.start_time)

    tab_events: List[TabEvent] = []
    prev_tab: Optional[TabEvent] = None

    for n in note_events:
        pos = choose_position(n.midi, prev_tab)
        if pos is None:
            # note cannot be played in standard tuning; skip for now
            continue

        string, fret = pos
        tab = TabEvent(
            start_time=n.start_time,
            end_time=n.end_time,
            string=string,
            fret=fret,
            midi=n.midi
        )
        tab_events.append(tab)
        prev_tab = tab

    return tab_events


# =========================
# Tab -> ASCII
# =========================

def render_ascii_tab(tab_events: List[TabEvent]) -> str:
    """
    Render a simple ASCII mandolin tab.
    Very naive v0: one 'column' per TabEvent in time order,
    2 characters wide for each event.

    Example output:

    E|--0-02-03-|
    A|--2-03-05-|
    D|----------|
    G|----------|
    """
    if not tab_events:
        return "E|\nA|\nD|\nG|\n"

    # Sort by time
    tab_events = sorted(tab_events, key=lambda e: e.start_time)

    # Each string will accumulate a list of 2-char chunks
    # We'll index strings by 1..4, but store as dict
    columns: Dict[int, List[str]] = {1: [], 2: [], 3: [], 4: []}

    for ev in tab_events:
        # For every event, we emit a "column" for all strings
        for s in columns.keys():
            if s == ev.string:
                fret_txt = str(ev.fret)
                # Pad to width 2; use '-' as fill char
                if len(fret_txt) == 1:
                    fret_txt = "-" + fret_txt
                elif len(fret_txt) >= 2:
                    # Truncate if crazy big, just to avoid blowing layout
                    fret_txt = fret_txt[-2:]
            else:
                fret_txt = "--"
            columns[s].append(fret_txt)

    # Turn each string's columns into a line
    # Important: E string is "top" line, G is bottom line
    line_E = "E|" + "".join(columns[1]) + "|"
    line_A = "A|" + "".join(columns[2]) + "|"
    line_D = "D|" + "".join(columns[3]) + "|"
    line_G = "G|" + "".join(columns[4]) + "|"

    return "\n".join([line_E, line_A, line_D, line_G])


# =========================
# Tiny manual test harness
# =========================

if __name__ == "__main__":
    # Example: simple ascending G major-ish thing on the A string
    # A4 (69), B4 (71), C5 (72), D5 (74)
    demo_notes = [
        NoteEvent(start_time=0.0, end_time=0.5, midi=69),
        NoteEvent(start_time=0.5, end_time=1.0, midi=71),
        NoteEvent(start_time=1.0, end_time=1.5, midi=72),
        NoteEvent(start_time=1.5, end_time=2.0, midi=74),
    ]

    demo_tabs = notes_to_tab(demo_notes)
    print(render_ascii_tab(demo_tabs))