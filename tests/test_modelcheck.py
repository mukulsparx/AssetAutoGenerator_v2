"""modelcheck: the doc parsers on text in the exact shapes the Tripo / Meshy pages use (copied 2026-10-21), and check()
on fake pages: a current configuration is quiet, an outdated one warns, offline is reported, nothing raises. No network."""
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen import modelcheck as MC, clients

# Tripo models page, as rendered (table cells run together) followed by the markdown form the page also embeds.
TRIPO_MODELS = ("Use these model ids with POST /v3/generation/text-to-model and POST /v3/generation/image-to-model . "
                "Model ID Description Recommended Use Case v3.1-20260211 H3.1, latest high-precision model (default) AAA production pipelines "
                "v3.0-20250812 H3.0, previous generation Legacy projects v2.5-20250123 H2.5 Older pipelines "
                "P2-20260801 P2, production model for PBR assets Game-ready furniture P1-20260311 P1, first production model Legacy. "
                "| `v3.1-20260211` | H3.1, latest high-precision model (default) | AAA production pipelines |")
TRIPO_TEXTURE = ("model string default: v3.0-20250812 Texture model version. Choose based on the generation model used for the source 3D model: "
                 "v3.5-20260815 — newest texture model. Required for texture_quality=fast and delight . "
                 "v3.0-20250812 — default. Recommended for models generated with v3.0-20250812 or v3.1-20260211 . "
                 "v2.5-20250123 — recommended for models generated with v2.5-20250123 .")
MESHY_CHANGELOG = ("2026-09 meshy-7.1 released: same parameters and credit cost as meshy-7 , higher geometry detail. latest now resolves to meshy-7.1 ; "
                   "meshy-7 is deprecated but keeps working unchanged. 2025-06 Meshy 6 released; latest resolves to Meshy 6. "
                   "Oct 10 meshy-5 has been retired. Multi-Image to 3D now returns 400 with the message ai_model meshy-5 has been retired.")
MESHY_OPENAPI = json.dumps({"servers": [{"url": "https://api.meshy.ai/openapi"}],
                            "paths": {"/v1/multi-image-to-3d": {"post": {"requestBody": {"content": {"application/json": {"schema": {"properties": {
                                "ai_model": {"type": "string", "enum": ["meshy-6", "meshy-6-lite", "meshy-7", "meshy-7.1", "latest", "meshy-t2", "meshy-t2.5"],
                                             "description": "`latest` resolves server-side to `meshy-7.1`. `meshy-7` is deprecated, superseded by `meshy-7.1`."}}}}}}}}}})
PAGES = {"tripo_models": TRIPO_MODELS, "tripo_texture": TRIPO_TEXTURE, "tripo_changelog": "2026-08 P2-20260801 released.",
         "meshy_openapi": MESHY_OPENAPI, "meshy_changelog": MESHY_CHANGELOG}
BY_URL = {MC.DOCS[k]: v for k, v in PAGES.items()}


class FakeCfg:
    def __init__(s, model="P2-20260801", tex="v3.5-20260815", meshy="meshy-7.1"):
        s.data = {"tripo": {"model": model, "texture_model": tex}}
        s.rules = {"modes": {"p2": {"model_version": model}, "hd": {"model_version": model}, "meshy": {"model": meshy}}}
    def get(s, sec, k, d=None): return s.data.get(sec, {}).get(k, d)
    def key(s, n): return None


class Parsers(unittest.TestCase):
    def test_version_ids_and_order(self):
        self.assertEqual(MC.versions(TRIPO_MODELS), {"H": ["v3.1-20260211", "v3.0-20250812", "v2.5-20250123"], "P": ["P2-20260801", "P1-20260311"]})
        self.assertEqual(MC.newest(TRIPO_MODELS, "P"), "P2-20260801")
        self.assertEqual(MC.versions("meshy-6 meshy-6-lite meshy-7.1 meshy-7 meshy-t2.5 meshy-t2"), {"meshy": ["meshy-7.1", "meshy-7", "meshy-6", "meshy-6-lite"], "meshy-t": ["meshy-t2.5", "meshy-t2"]})

    def test_id_at_sentence_end_and_not_inside_another(self):
        self.assertEqual(MC.VER_RE.findall("latest now resolves to meshy-7.1."), ["meshy-7.1"])
        self.assertEqual(MC.VER_RE.findall("use meshy-7.1 or v3.1-20260211."), ["meshy-7.1", "v3.1-20260211"])
        self.assertEqual(MC.VER_RE.findall("meshy-7.1"), ["meshy-7.1"])          # not "meshy-7" out of "meshy-7.1"

    def test_default_marker_both_page_forms(self):
        self.assertEqual(MC.default_marked(TRIPO_MODELS, "H"), "v3.1-20260211")
        self.assertIsNone(MC.default_marked(TRIPO_MODELS, "P"))
        self.assertEqual(MC.default_marked("| `v3.1-20260211` | H3.1, latest high-precision model (default) |", "H"), "v3.1-20260211")

    def test_texture_versions_from_texture_page_only(self):
        self.assertEqual(MC.texture_versions(TRIPO_TEXTURE)[0], "v3.5-20260815")
        self.assertNotIn("v3.1-20260211", MC.texture_versions(TRIPO_TEXTURE))     # named as a geometry model in the advice, not a texture model

    def test_meshy_latest_from_changelog_not_old_entries(self):
        self.assertEqual(MC.LATEST_RE.search(MESHY_CHANGELOG).group(1), "meshy-7.1")
        self.assertIsNone(MC.LATEST_RE.search("Meshy 6 released; latest resolves to Meshy 6."))

    def test_meshy_openapi(self):
        mo = MC.meshy_from_openapi(MESHY_OPENAPI)
        self.assertEqual(mo["latest"], "meshy-7.1"); self.assertEqual(mo["multi_image_api_versions"], [1])
        self.assertEqual(mo["models"][:2], ["meshy-7.1", "meshy-7"]); self.assertNotIn("latest", mo["models"])
        self.assertEqual(MC.meshy_from_openapi("not json")["models"], [])

    def test_retirement_notes_are_clause_level(self):
        notes = MC.retirement_notes(MC.text_of(MESHY_CHANGELOG), ["meshy-7"])
        self.assertTrue(notes and "meshy-7 is deprecated" in notes[0], notes)
        self.assertEqual(MC.retirement_notes(MESHY_CHANGELOG, ["meshy-7.1"]), [])             # superseded-by is not retired
        self.assertEqual(len(MC.retirement_notes(MESHY_CHANGELOG, ["meshy-5"])), 2)
        self.assertEqual(MC.retirement_notes("v3.1-20260211 is deprecated. v3.0-20250812 stays.", ["v3.0-20250812"]), [])   # the dot in v3.1 is not a clause end
        # the same sentence twice (rendered text + embedded markdown with backticks) is one note
        self.assertEqual(len(MC.retirement_notes("meshy-7 is deprecated but keeps working. `meshy-7` is deprecated but keeps working.", ["meshy-7"])), 1)

    def test_text_of(self):
        self.assertEqual(MC.text_of("<p>a &amp; <b>b</b></p><script>x=1</script> c").strip(), "a & b c")

    def test_api_probe(self):
        class Gone:
            def __init__(s, key, api): pass
            def balance(s): raise clients.ApiError("tripo", "HTTP 404 not found")
        class Fine(Gone):
            def balance(s): return {"balance": 5}
        self.assertEqual(MC.api_probe(None, Fine, "x"), "no key")
        self.assertEqual(MC.api_probe("k", Fine, "x"), "ok")
        self.assertTrue(MC.api_probe("k", Gone, "https://openapi.tripo3d.ai/v3").startswith("endpoint not found"))


class Check(unittest.TestCase):
    def setUp(self):
        self._fetch = MC.fetch; MC.fetch = lambda url, timeout=25: BY_URL[url]
    def tearDown(self): MC.fetch = self._fetch

    def test_current_configuration_is_quiet(self):
        res = MC.check(FakeCfg(), None)
        self.assertEqual(res["warnings"], []); self.assertTrue(res["ok"]); self.assertFalse(res["offline"])
        t = res["tripo"]
        self.assertEqual((t["latest_p"], t["latest_h"], t["default_h"], t["latest_texture"], t["docs_api_version"]), ("P2-20260801", "v3.1-20260211", "v3.1-20260211", "v3.5-20260815", 3))
        self.assertEqual(res["meshy"]["latest"], "meshy-7.1"); self.assertEqual(t["api"], "no key")
        self.assertTrue(MC.summary(res).startswith("Models current:"))
        self.assertEqual(MC.cached(None)["checked_at"], res["checked_at"])

    def test_outdated_configuration_warns(self):
        res = MC.check(FakeCfg("P1-20260311", "v3.0-20250812", "meshy-7"), None)
        W = " | ".join(res["warnings"])
        self.assertIn("newer P-series model: P2-20260801", W); self.assertIn("newer texture model: v3.5-20260815", W)
        self.assertIn("Meshy's latest model is now meshy-7.1", W); self.assertIn("meshy-7 is deprecated", W)
        self.assertFalse(res["ok"]); self.assertTrue(MC.summary(res).startswith("MODEL CHECK:"))

    def test_unlisted_model_warns(self):
        res = MC.check(FakeCfg("P0-20250101", "v1.0-20240101", "meshy-5"), None)
        W = " | ".join(res["warnings"])
        self.assertIn("no longer lists P0-20250101", W); self.assertIn("no longer lists v1.0-20240101", W); self.assertIn("no longer lists meshy-5", W)

    def test_offline_is_reported_not_raised(self):
        def down(url, timeout=25): raise OSError("network is unreachable")
        MC.fetch = down
        res = MC.check(FakeCfg(), None)
        self.assertTrue(res["offline"]); self.assertEqual(res["warnings"], []); self.assertTrue(res["ok"])
        self.assertTrue(MC.summary(res).startswith("Model check: offline"))

    def test_api_version_moved_warns(self):
        BY_URL2 = dict(BY_URL); BY_URL2[MC.DOCS["tripo_models"]] = TRIPO_MODELS.replace("/v3/", "/v4/")
        MC.fetch = lambda url, timeout=25: BY_URL2[url]
        res = MC.check(FakeCfg(), None)
        self.assertTrue(any("API v4" in w for w in res["warnings"]), res["warnings"])


if __name__ == "__main__": unittest.main()
