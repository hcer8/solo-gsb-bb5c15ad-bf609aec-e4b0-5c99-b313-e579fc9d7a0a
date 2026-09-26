import random
import unittest
from itertools import product

from app.decoder import MORSE_ALPHABET, decode_record, encode_words


def levenshtein(left: str, right: str) -> int:
    row = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        next_row = [i]
        for j, b in enumerate(right, start=1):
            next_row.append(
                min(
                    row[j] + 1,
                    next_row[j - 1] + 1,
                    row[j - 1] + (a != b),
                )
            )
        row = next_row
    return row[-1]


def brute_force(record: str, candidates: list[str], max_words: int):
    expected_cost = len(record) + 60
    expected_words = None

    for word_count in range(1, max_words + 1):
        for words in product(candidates, repeat=word_count):
            morse = encode_words(list(words))
            cost = levenshtein(record, morse)
            if (
                expected_words is None
                or cost < expected_cost
                or (
                    cost == expected_cost
                    and (
                        len(words) < len(expected_words)
                        or (len(words) == len(expected_words) and words < expected_words)
                    )
                )
            ):
                expected_cost = cost
                expected_words = tuple(words)

    return list(expected_words), encode_words(list(expected_words)), expected_cost


class DecoderTests(unittest.TestCase):
    def test_exact_single_word(self):
        words, morse, edits = decode_record("...---...", ["SOS", "ET", "A"])
        self.assertEqual(words, ["SOS"])
        self.assertEqual(morse, "...---...")
        self.assertEqual(edits, 0)

    def test_repeated_words_are_allowed_and_boundaries_are_global(self):
        # "..." can be one S or three E words; equal edits prefer fewer words.
        words, morse, edits = decode_record("...", ["E", "S"])
        self.assertEqual(words, ["S"])
        self.assertEqual(morse, "...")
        self.assertEqual(edits, 0)

        # ".." can be one I or two E words; one word wins on word count.
        words, _, edits = decode_record("..", ["E", "I"])
        self.assertEqual((words, edits), (["I"], 0))

    def test_fewer_words_tie_break(self):
        # Both ET and A encode to ".-", and zero edits are possible.
        words, morse, edits = decode_record(".-", ["ET", "A"])
        self.assertEqual(words, ["A"])
        self.assertEqual(morse, ".-")
        self.assertEqual(edits, 0)

    def test_lexicographic_sequence_tie_break(self):
        # "EI" and "IE" both encode the 3-dot string; equal edits and word
        # count select the lexicographically smaller word.
        words, _, edits = decode_record("...", ["IE", "EI"])
        self.assertEqual(words, ["EI"])
        self.assertEqual(edits, 0)

    def test_duplicate_candidates(self):
        words, _, _ = decode_record("...", ["S", "S", "E"])
        self.assertEqual(words, ["S"])

    def test_insertion_deletion_substitution(self):
        # E="." versus "-" needs one substitution.
        words, morse, edits = decode_record("-", ["E"])
        self.assertEqual((words, morse, edits), (["E"], ".", 1))

        # N="-." versus "." needs one deletion from the record.
        words, morse, edits = decode_record(".", ["N"])
        self.assertEqual((words, morse, edits), (["N"], "-.", 1))

        # A=".-" versus ".--" needs one insertion in the standard sequence.
        words, morse, edits = decode_record(".--", ["A"])
        self.assertEqual((words, morse, edits), (["A"], ".-", 1))

    def test_randomized_against_brute_force(self):
        random.seed(42)
        alphabet = list(MORSE_ALPHABET)
        for case in range(100):
            candidate_count = random.randint(1, 4)
            candidates = [
                "".join(random.choice(alphabet) for _ in range(random.randint(1, 3)))
                for _ in range(candidate_count)
            ]
            candidates = list(dict.fromkeys(candidates))
            record = "".join(random.choice(".-") for _ in range(random.randint(1, 8)))
            max_words = 3 if case < 50 else 4

            with self.subTest(record=record, candidates=candidates):
                self.assertEqual(
                    decode_record(record, candidates, max_words=max_words),
                    brute_force(record, candidates, max_words),
                )


if __name__ == "__main__":
    unittest.main()
