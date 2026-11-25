"""Final GLBs are metres (Mukul 2026-11-04): glbinfo.to_metres bakes the pipeline's centimetres into metres and stamps
the file; glbinfo.info reports cm for both; store.copy_final converts the copy and leaves the work file alone; a file
that is already metres (this converter's stamp or glb_to_metres.py's root-scale files) is measured right and never
converted twice. No Blender: the GLBs are built here by hand."""
import json, struct, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autogen import glbinfo
from autogen.store import Store


def glb(path, verts, nodes, scenes=None, extras=None, stride=None, tris=None):
    """A GLB with one mesh of `verts` (list of xyz, one triangle per 3) referenced by `nodes` (glTF node dicts; the
    ones with "mesh": 0 draw it); `stride` pads each vertex to that many bytes (interleaved buffers)."""
    stride = stride or 12
    raw = bytearray()
    for v in verts: raw += struct.pack("<fff", *v) + b"\0" * (stride - 12)
    lo = [min(v[i] for v in verts) for i in range(3)]; hi = [max(v[i] for v in verts) for i in range(3)]
    bv = {"buffer": 0, "byteOffset": 0, "byteLength": len(raw)}
    if stride != 12: bv["byteStride"] = stride
    g = {"asset": {"version": "2.0", **({"extras": extras} if extras else {})},
         "buffers": [{"byteLength": len(raw)}], "bufferViews": [bv],
         "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(verts), "type": "VEC3", "min": lo, "max": hi}],
         "meshes": [{"name": "m", "primitives": [{"attributes": {"POSITION": 0}}]}], "nodes": nodes,
         "scenes": [{"nodes": scenes if scenes is not None else list(range(len(nodes)))}], "scene": 0}
    js = json.dumps(g).encode(); js += b" " * (-len(js) % 4); raw += b"\0" * (-len(raw) % 4)
    body = struct.pack("<I4s", len(js), b"JSON") + js + struct.pack("<I4s", len(raw), b"BIN\0") + raw
    Path(path).write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body); return path


# a 120 wide x 40 deep x 75 high slab in cm (glTF Y-up: width X, height Y, depth Z), 4 triangles
SLAB = [(0, 0, 0), (120, 0, 0), (120, 75, 0), (0, 0, 0), (120, 75, 0), (0, 75, 0),
        (0, 0, 40), (120, 0, 40), (120, 75, 40), (0, 0, 40), (120, 75, 40), (0, 75, 40)]


class Units(unittest.TestCase):
    def setUp(self): self.d = Path(tempfile.mkdtemp())

    def test_cm_file_reads_as_cm(self):
        p = glb(self.d / "a.glb", SLAB, [{"mesh": 0, "name": "x", "translation": [10, 0, 0]}])
        i = glbinfo.info(p)
        self.assertEqual((i["units"], i["dims_cm"], i["tris"], i["mesh_uuid"]), ("cm", [120.0, 40.0, 75.0], 4, "m"))

    def test_to_metres_bakes_positions_and_keeps_the_cm_reading(self):
        p = glb(self.d / "a.glb", SLAB, [{"mesh": 0, "name": "x", "translation": [10, 0, 0]}], stride=16)
        self.assertTrue(glbinfo.to_metres(p))
        i = glbinfo.info(p); self.assertEqual((i["units"], i["dims_cm"], i["tris"]), ("m", [120.0, 40.0, 75.0], 4))
        data = p.read_bytes(); clen = struct.unpack_from("<I", data, 12)[0]; g = json.loads(data[20:20 + clen])
        self.assertEqual(g["asset"]["extras"]["units"], "m")
        self.assertEqual(g["nodes"][0]["translation"], [0.1, 0, 0]); self.assertNotIn("scale", g["nodes"][0])
        a = g["accessors"][0]; self.assertAlmostEqual(a["max"][0], 1.2); self.assertAlmostEqual(a["max"][1], 0.75)
        bo = 20 + clen + 8                                              # the first vertex's floats are metres now
        blen = struct.unpack_from("<I", data, 20 + clen)[0]; x, y, z = struct.unpack_from("<fff", data, bo + 16)
        self.assertAlmostEqual(x, 1.2, places=5); self.assertEqual(blen % 4, 0)
        self.assertFalse(glbinfo.to_metres(p), "a metres file is left alone"); self.assertEqual(glbinfo.info(p)["dims_cm"], [120.0, 40.0, 75.0])

    def test_set_uuid_after_the_conversion_keeps_both(self):
        p = glb(self.d / "a.glb", SLAB, [{"mesh": 0, "name": "x"}]); glbinfo.to_metres(p)
        self.assertTrue(glbinfo.set_uuid(p, "0123-uuid", "slab"))
        i = glbinfo.info(p); self.assertEqual((i["units"], i["mesh_uuid"], i["dims_cm"]), ("m", "0123-uuid", [120.0, 40.0, 75.0]))
        self.assertFalse(glbinfo.to_metres(p))

    def test_root_scaled_file_from_glb_to_metres_py_is_measured_through_its_parent(self):
        # the 2026-11-04 batch: cm positions under a root node scaled 0.01, stamped "metres (converted from cm ...)"
        p = glb(self.d / "a.glb", SLAB, [{"name": "root", "scale": [0.01, 0.01, 0.01], "children": [1]}, {"mesh": 0, "name": "x"}],
                scenes=[0], extras={"units": "metres (converted from cm 2026-11-04)"})
        i = glbinfo.info(p); self.assertEqual((i["units"], i["dims_cm"], i["mesh_count"]), ("m", [120.0, 40.0, 75.0], 1))
        self.assertFalse(glbinfo.to_metres(p))

    def test_rotated_node_is_measured_in_world_space(self):
        # 90 degrees about Y swaps width and depth
        p = glb(self.d / "a.glb", SLAB, [{"mesh": 0, "name": "x", "rotation": [0, 0.7071068, 0, 0.7071068]}])
        self.assertEqual(glbinfo.info(p)["dims_cm"], [40.0, 120.0, 75.0])

    def test_draco_file_falls_back_to_scaling_the_roots(self):
        p = glb(self.d / "a.glb", SLAB, [{"mesh": 0, "name": "x"}])
        data = p.read_bytes(); clen = struct.unpack_from("<I", data, 12)[0]; g = json.loads(data[20:20 + clen])
        g["meshes"][0]["primitives"][0]["extensions"] = {"KHR_draco_mesh_compression": {"bufferView": 0}}
        js = json.dumps(g).encode(); js += b" " * (-len(js) % 4)
        body = struct.pack("<I4s", len(js), b"JSON") + js + data[20 + clen:]
        p.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
        self.assertTrue(glbinfo.to_metres(p))
        data = p.read_bytes(); clen = struct.unpack_from("<I", data, 12)[0]; g = json.loads(data[20:20 + clen])
        self.assertEqual(g["nodes"][0]["scale"], [0.01, 0.01, 0.01]); self.assertEqual(g["accessors"][0]["max"][0], 120)
        self.assertEqual(glbinfo.info(p)["dims_cm"], [120.0, 40.0, 75.0])

    def test_copy_final_converts_the_copy_and_leaves_the_work_file(self):
        st = Store(self.d / "assets", "test"); st.adir("slab").mkdir(parents=True)
        src = glb(self.d / "work.glb", SLAB, [{"mesh": 0, "name": "x"}])
        dst = st.copy_final("slab", src, "slab_std")
        self.assertEqual(dst, self.d / "assets" / "slab" / "final_glb" / "slab_std.glb")
        self.assertEqual(glbinfo.info(dst)["units"], "m"); self.assertEqual(glbinfo.info(src)["units"], "cm")
        self.assertEqual(glbinfo.info(dst)["dims_cm"], glbinfo.info(src)["dims_cm"])


if __name__ == "__main__": unittest.main()
