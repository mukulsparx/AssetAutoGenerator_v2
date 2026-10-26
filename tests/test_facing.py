"""Facing convention (2026-10-23, SPEC section 33): every GLB the tool makes faces glTF -Z, the app's front for floor items
and wall hangings alike. The Blender scripts can't run here (no bpy), so this reads them as text and checks that each one
states the convention the same way; tests/facing_check.py runs the real thing in Blender on synthetic Tripo/Meshy models."""
import math, re, sys, unittest
from pathlib import Path
PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
B = PKG / "blender_scripts"


def src(name): return (PKG / name).read_text(encoding="utf-8")


def rot_z(deg, v):
    a = math.radians(deg); x, y, z = v
    return (round(x * math.cos(a) - y * math.sin(a), 9), round(x * math.sin(a) + y * math.cos(a), 9), z)


def to_gltf(v):            # Blender (x, y, z up) -> glTF (x, y up, z): the exporter's Y-up conversion
    return (v[0], v[2], -v[1])


class Convention(unittest.TestCase):
    def test_the_maths(self):
        # Tripo faces +X: a +90 turn about Z puts it on Blender +Y, which the exporter writes as glTF -Z
        self.assertEqual(to_gltf(rot_z(90, (1, 0, 0))), (0, 0, -1))
        # Meshy faces glTF +Z = Blender -Y: a half turn puts it on glTF -Z
        self.assertEqual(to_gltf(rot_z(180, (0, -1, 0))), (0, 0, -1))

    def test_postprocess_turns_tripo_and_meshy_to_minus_z(self):
        s = src("blender_scripts/postprocess.py")
        m = re.search(r'elif cfg\.get\("source", "tripo"\) == "tripo":\n\s+me\.transform\(mathutils\.Matrix\.Rotation\(math\.radians\((-?\d+)\), 4, \'Z\'\)\)', s)
        self.assertIsNotNone(m, "Tripo orientation branch missing"); self.assertEqual(int(m.group(1)), 90)
        m = re.search(r'else:\n\s+me\.transform\(mathutils\.Matrix\.Rotation\(math\.radians\((-?\d+)\), 4, \'Z\'\)\)\s+# Meshy', s)
        self.assertIsNotNone(m, "Meshy orientation branch missing"); self.assertEqual(int(m.group(1)), 180)
        self.assertIn("front lands on glTF -Z", s)

    def test_scripts_that_know_where_the_front_is_agree(self):
        self.assertIn("f.normal.y < -0.9 and f.calc_center_median().y < y0 + 0.08 * D", src("blender_scripts/close_back.py"))   # back panel at -Y
        self.assertIn("py0 = y0 - 0.001 * D; py1 = py0 + t", src("blender_scripts/close_back.py"))
        q = src("blender_scripts/qa_render.py")
        self.assertIn("d = mathutils.Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))", q)      # azimuth 0 looks from +Y
        self.assertIn("front (glTF -Z", q)
        self.assertIn('("front",(0,1,0.15))', src("blender_scripts/render_views.py"))
        self.assertIn("if ax_n @ np.array([0, 1, 0.0]) < 0: ax_n = -ax_n", src("blender_scripts/net_panel.py"))
        self.assertIn("u, w = (x1 - x) / W, (y1 - y) / D", src("blender_scripts/make_rug.py"))                              # photo bottom edge at +Y
        self.assertIn('"a": (x0, y1, z0), "b": (x1, y1, z0), "c": (x1, y1, z1), "d": (x0, y1, z1),   # front', src("blender_scripts/make_art.py"))
        self.assertIn("new THREE.Vector3(-1.1, .7, -1.5)", src("web/index.html"))                                            # preview looks at the front
        for f in B.glob("*.py"):                                                   # no script still calls +Z the front (history lines say "until")
            for i, line in enumerate(src(f"blender_scripts/{f.name}").splitlines(), 1):
                if "until" in line.lower() or "Meshy output faces" in line: continue
                self.assertFalse(re.search(r"front[^\n]{0,30}glTF \+Z|glTF \+Z[^\n]{0,12}front", line), f"{f.name}:{i}: {line.strip()}")


if __name__ == "__main__": unittest.main()
