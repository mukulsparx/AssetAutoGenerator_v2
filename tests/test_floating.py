"""Floating parts (2026-10-29, SPEC section 40): the card line for postprocess.py step 1c, and the wiring that keeps it
to one line per version. The geometry itself needs Blender; it was checked on every card version's raw download."""
import re, sys, unittest
from pathlib import Path
PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from autogen import jobs


class FloatingNote(unittest.TestCase):
    def test_nothing_removed_no_line(self):
        self.assertEqual(jobs.floating_note({}), [])
        self.assertEqual(jobs.floating_note({"floating_removed": {"pieces": 0, "faces": 0, "where": []}}), [])

    def test_one_piece(self):
        rep = {"floating_removed": {"pieces": 1, "faces": 1049, "where": ["back"], "area_pct": 0.162}}
        self.assertEqual(jobs.floating_note(rep), ["Removed floating part (back): a small piece that touched nothing else in the model."])

    def test_several_pieces(self):
        (line,) = jobs.floating_note({"floating_removed": {"pieces": 2, "where": ["back", "top"]}})
        self.assertTrue(line.startswith(jobs.FLOATING_NOTE + "s (back, top): 2 small pieces"), line)

    def test_generate_and_fix_size_add_it_once(self):
        src = (PKG / "autogen" / "jobs.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"\+ floating_note\(rep\)", src)), 2)        # generate + Fix size
        self.assertIn('startswith(("Resized to ", FLOATING_NOTE, TURN_NOTE + " "))', src)   # Fix size drops the old lines first

    def test_step_skips_lamps_and_rugs(self):
        src = (PKG / "blender_scripts" / "postprocess.py").read_text(encoding="utf-8")
        self.assertIn("""if cfg.get("category") not in ("lamp", "rug") and 'floating' not in SKIP:""", src)
        self.assertLess(src.index("# 1c) floating pieces"), src.index("# 3) scale to listed dims"))   # before sizing


if __name__ == "__main__":
    unittest.main()
