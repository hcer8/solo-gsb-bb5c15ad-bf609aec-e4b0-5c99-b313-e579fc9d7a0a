"""Global decoder for Morse records without inter-word separators."""

from dataclasses import dataclass

MORSE_ALPHABET: dict[str, str] = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
}

MAX_WORDS = 6


@dataclass(frozen=True, slots=True)
class State:
    """One best way to reach an edit-distance grid position."""

    cost: int
    words: tuple[str, ...]


def is_better(candidate: State, current: State | None) -> bool:
    """Compare by edits, then word count, then lexicographic word sequence."""
    if current is None:
        return True
    if candidate.cost != current.cost:
        return candidate.cost < current.cost
    if len(candidate.words) != len(current.words):
        return len(candidate.words) < len(current.words)
    return candidate.words < current.words


def better_state(left: State | None, right: State | None) -> State | None:
    if left is None:
        return right
    if right is None:
        return left
    return left if is_better(left, right) else right


def encode_words(words: tuple[str, ...] | list[str]) -> str:
    return "".join("".join(MORSE_ALPHABET[char] for char in word) for word in words)


def decode_record(
    record: str,
    candidates: list[str],
    max_words: int = MAX_WORDS,
) -> tuple[list[str], str, int]:
    """
    Find the best sequence of one to ``max_words`` candidate words.

    A dynamic-programming edit grid is extended one whole word at a time.
    This considers all word boundaries and all edit alignments globally rather
    than choosing a boundary greedily or correcting words independently.
    """
    # Repeated candidates do not add a distinct transition; preserving order is
    # irrelevant because the final tie-break is lexicographic.
    unique_words = tuple(dict.fromkeys(candidates))
    word_codes = tuple((word, encode_words((word,))) for word in unique_words)

    record_length = len(record)

    # Boundary before any chosen word. Initial cost i means consuming and
    # deleting the first i dots/dashes of the record before generated Morse.
    previous_boundary = [State(i, ()) for i in range(record_length + 1)]
    best: State | None = None

    for _ in range(1, max_words + 1):
        next_boundary: list[State | None] = [None] * (record_length + 1)

        for word, code in word_codes:
            previous_column = previous_boundary

            for output_position, output_symbol in enumerate(code, start=1):
                current_column: list[State | None] = [None] * (record_length + 1)
                first_symbol = output_position == 1

                # Insert an output symbol before consuming any record symbol.
                starting_state = previous_column[0]
                if first_symbol:
                    starting_state = State(
                        starting_state.cost + 1,
                        starting_state.words + (word,),
                    )
                else:
                    starting_state = State(
                        starting_state.cost + 1,
                        starting_state.words,
                    )
                current_column[0] = starting_state

                for record_position in range(1, record_length + 1):
                    # Insertion: produce a dot/dash without consuming a record symbol.
                    insertion_source = previous_column[record_position]
                    insertion_words = (
                        insertion_source.words + (word,)
                        if first_symbol
                        else insertion_source.words
                    )
                    insertion = State(
                        insertion_source.cost + 1,
                        insertion_words,
                    )

                    # Deletion: consume a record symbol without producing one.
                    deletion_source = current_column[record_position - 1]
                    deletion = State(
                        deletion_source.cost + 1,
                        deletion_source.words,
                    )

                    # Match or substitution: consume one symbol from each side.
                    diagonal_source = previous_column[record_position - 1]
                    diagonal_words = (
                        diagonal_source.words + (word,)
                        if first_symbol
                        else diagonal_source.words
                    )
                    substitution_cost = (
                        0
                        if record[record_position - 1] == output_symbol
                        else 1
                    )
                    substitution = State(
                        diagonal_source.cost + substitution_cost,
                        diagonal_words,
                    )

                    current_column[record_position] = better_state(
                        better_state(insertion, deletion), substitution
                    )

                previous_column = current_column

            for i, state in enumerate(current_column):
                next_boundary[i] = better_state(next_boundary[i], state)

        previous_boundary = next_boundary  # type: ignore[assignment]
        finished = next_boundary[record_length]
        if is_better(finished, best):
            best = finished

    assert best is not None
    words = list(best.words)
    return words, encode_words(words), best.cost
