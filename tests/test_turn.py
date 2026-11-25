"""Turn to the listing (2026-11-25, SPEC section 43): the card line for postprocess.py step 2b and where the step sits.
The geometry needs Blender: tests/facing_check.py runs it on boxes laid out the way Tripo delivers them (a bed lying
sideways like Kory, one facing the right way, one with its headboard in front, a sofa, a dresser across the width)."""
import re, sys, unittest
from pathlib import Path
PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from autogen import jobs


class TurnNote(unittest.TestCase):
    def test_no_turn_no_line(self):
        self.assertEqual(jobs.turn_note({}), [])
        self.assertEqual(jobs.turn_note({"turned_to_listing": {"deg": 0, "why": "none"}}), [])

    def test_headboard(self):
        (line,) = jobs.turn_note({"turned_to_listing": {"deg": 90, "why": "headboard"}})
        self.assertTrue(line.startswith(jobs.TURN_NOTE + " 90° before sizing"), line)
        self.assertIn("headboard", line)

    def test_footprint_asks_for_a_look(self):
        (line,) = jobs.turn_note({"turned_to_listing": {"deg": -90, "why": "footprint"}})
        self.assertTrue(line.startswith(jobs.TURN_NOTE + " 90° "), line)
        self.assertIn("Check which way it faces", line)

    def test_generate_and_fix_size_add_it_once(self):
        src = (PKG / "autogen" / "jobs.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"\+ turn_note\(rep\)", src)), 2)            # generate + Fix size
        self.assertIn('TURN_NOTE + " "))', src)                                       # Fix size drops the old line first


class Step(unittest.TestCase):
    src = (PKG / "blender_scripts" / "postprocess.py").read_text(encoding="utf-8")

    def test_after_the_pivot_before_sizing(self):
        s = self.src
        self.assertLess(s.index("# 2) pivot"), s.index("# 2b) turn to the listing"))
        self.assertLess(s.index("# 2b) turn to the listing"), s.index("# 3) scale to listed dims"))

    def test_left_out_where_it_does_not_apply(self):
        self.assertIn('not ({"scale", "turn"} & SKIP) and not cfg.get("uniform_scale")', self.src)
        self.assertIn('cfg.get("category") not in ("rug", "bedding", "lamp")', self.src)

    def test_headboard_goes_to_the_back(self):
        # -Y is the back (front = Blender +Y = glTF -Z): a +90 turn takes -X to -Y, -90 takes +X, 180 takes +Y
        self.assertIn('{"-Y": 0, "-X": 90, "+X": -90, "+Y": 180}[top]', self.src)

    def test_always_logged(self):
        self.assertIn('log("turned_to_listing"', self.src)


if __name__ == "__main__":
    unittest.main()
