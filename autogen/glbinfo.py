"""Reads triangle count, size and mesh name straight from a GLB file (no Blender needed), names its mesh, and turns a
finished file from the pipeline's centimetres into metres.

Units (Mukul, 2026-11-04). The pipeline works in centimetres: Tripo's output is scaled to the listed W x D x H with
1 unit = 1 cm (blender_scripts/postprocess.py), and every work file, rug and wall-art slab stays that way. The FINAL GLB
- final_glb/<name>.glb and its copies in the vendor folder and the session folder - is written in metres, the glTF
standard, so Blender, 3ds Max, Connecter, Unreal and the web app all show it at its real size without the app's
"anything under 10 units is metres" guess. `to_metres` bakes the change into the file (positions and node translations
x 0.01, accessor bounds updated; the binary chunk is rewritten in place, textures untouched) and stamps
`asset.extras.units = "m"`. `info` reads that stamp, so `dims_cm` is centimetres for old (cm) and new (m) files alike:
rows, the sheet CSV, the Models sheet and the review page keep showing cm. Older finals are converted the next time
they go through vendor_export.export (`python -m autogen export-vendor --asset NAME`)."""
import json, os, struct

GLB_MAGIC, JSON_CHUNK, BIN_CHUNK = b"glTF", b"JSON", b"BIN\0"
CM_PER_M = 100.0
_NORM = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}   # normalized integer -> float, per glTF component type


def _chunks(data: bytes):
    """(version, [[type, bytearray], ...]) of a GLB's chunks, in file order."""
    if len(data) < 20 or data[:4] != GLB_MAGIC: raise ValueError("not a GLB")
    _magic, ver, length = struct.unpack_from("<4sII", data, 0)
    off, out = 12, []
    while off + 8 <= min(length, len(data)):
        clen, ctype = struct.unpack_from("<I4s", data, off); off += 8
        out.append([ctype, bytearray(data[off:off + clen])]); off += clen
    return ver, out


def _json(chunks) -> dict:
    return json.loads(bytes(next(raw for t, raw in chunks if t == JSON_CHUNK)))


def _write(path, ver, g: dict, chunks):
    """The JSON chunk from `g`, every other chunk as it is (padded to 4 bytes), through a temp file next to `path`."""
    js = json.dumps(g, separators=(",", ":")).encode(); js += b" " * (-len(js) % 4)
    body = struct.pack("<I4s", len(js), JSON_CHUNK) + js
    for ctype, raw in chunks:
        if ctype == JSON_CHUNK: continue
        raw = bytes(raw) + b"\0" * (-len(raw) % 4)
        body += struct.pack("<I4s", len(raw), ctype) + raw
    tmp = str(path) + ".units.tmp"
    with open(tmp, "wb") as f: f.write(struct.pack("<4sII", GLB_MAGIC, ver, 12 + len(body)) + body)
    os.replace(tmp, path)


def units(g: dict) -> str:
    """"m" when the file carries the metres stamp (`asset.extras.units`, this module's or glb_to_metres.py's
    "metres (converted ...)"), else "cm": everything the pipeline wrote before 2026-11-04 and every work file."""
    u = str(((g.get("asset") or {}).get("extras") or {}).get("units") or "").strip().lower()
    return "m" if u and u.split()[0] in ("m", "metre", "metres", "meter", "meters") else "cm"


# ---------- node transforms (glTF: column-major matrix, or translation * rotation * scale) ----------
def _local(n: dict):
    if "matrix" in n:
        m = n["matrix"]; return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    t = n.get("translation", [0, 0, 0]); x, y, z, w = n.get("rotation", [0, 0, 0, 1]); s = n.get("scale", [1, 1, 1])
    R = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[R[r][c] * s[c] for c in range(3)] + [t[r]] for r in range(3)] + [[0, 0, 0, 1]]


def _mul(a, b): return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def _world_of(nodes):
    """node index -> its world matrix (parents composed, so a root scaled by 0.01 is measured right)."""
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}; memo = {}
    def world(i):
        if i not in memo:
            L = _local(nodes[i]); memo[i] = _mul(world(parent[i]), L) if i in parent and parent[i] != i else L
        return memo[i]
    return world


def info(path) -> dict:
    """Triangles, [W, D, H] in cm (whatever the file's own unit), mesh names and the single mesh's name (= its UUID)."""
    with open(path, "rb") as f:
        magic, _ver, _len = struct.unpack("<4sII", f.read(12))
        if magic != GLB_MAGIC: raise ValueError("not a GLB")
        clen, ctype = struct.unpack("<I4s", f.read(8)); g = json.loads(f.read(clen))
    nodes = g.get("nodes", []); world = _world_of(nodes)
    tris = 0; lo = [1e18] * 3; hi = [-1e18] * 3; names = []
    for i, node in enumerate(nodes):
        if "mesh" not in node: continue
        mesh = g["meshes"][node["mesh"]]; names.append(mesh.get("name") or node.get("name", "")); M = world(i)
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4: continue
            acc = g["accessors"][prim["indices"]] if "indices" in prim else g["accessors"][prim["attributes"]["POSITION"]]
            tris += acc["count"] // 3
            pos = g["accessors"][prim["attributes"]["POSITION"]]
            if "min" in pos and "max" in pos:
                q = _NORM.get(pos["componentType"], 1.0) if pos.get("normalized") else 1.0   # KHR_mesh_quantization bounds are raw integers
                for k in range(8):                                   # the 8 corners of the local bounds, into world space
                    c = [(pos["max"] if k >> a & 1 else pos["min"])[a] / q for a in range(3)]
                    for r in range(3):
                        v = M[r][0] * c[0] + M[r][1] * c[1] + M[r][2] * c[2] + M[r][3]
                        lo[r] = min(lo[r], v); hi[r] = max(hi[r], v)
    # glTF is Y-up: width = X, height = Y, depth = Z. Reported in cm whatever the file's unit (the stamp decides).
    u = units(g); k = CM_PER_M if u == "m" else 1.0
    size = [round((hi[0] - lo[0]) * k, 1), round((hi[2] - lo[2]) * k, 1), round((hi[1] - lo[1]) * k, 1)] if tris else None
    return {"tris": tris, "dims_cm": size, "mesh_names": names, "mesh_count": len(names),
            "mesh_uuid": names[0] if len(names) == 1 else None, "units": u}


def _bake(g: dict, binc, k: float) -> bool:
    """Every POSITION accessor (and morph-target positions) x k, written back into the binary chunk, bounds and node
    translations x k. False when the geometry cannot be rewritten (Draco, quantized, sparse or external data)."""
    accs = set()
    for mesh in g.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if "KHR_draco_mesh_compression" in (prim.get("extensions") or {}): return False
            if "POSITION" in prim.get("attributes", {}): accs.add(prim["attributes"]["POSITION"])
            for tg in prim.get("targets", []):
                if "POSITION" in tg: accs.add(tg["POSITION"])
    if accs and binc is None: return False
    for ai in accs:
        a = g["accessors"][ai]
        if a.get("componentType") != 5126 or a.get("type") != "VEC3" or "sparse" in a or "bufferView" not in a: return False
        bv = g["bufferViews"][a["bufferView"]]
        if bv.get("buffer", 0) != 0 or "uri" in g["buffers"][0]: return False
    for ai in accs:
        a = g["accessors"][ai]; bv = g["bufferViews"][a["bufferView"]]
        base = bv.get("byteOffset", 0) + a.get("byteOffset", 0); stride = bv.get("byteStride", 12)
        for i in range(a["count"]):
            o = base + i * stride; x, y, z = struct.unpack_from("<fff", binc, o)
            struct.pack_into("<fff", binc, o, x * k, y * k, z * k)
        for key in ("min", "max"):
            if key in a: a[key] = [v * k for v in a[key]]
    for n in g.get("nodes", []):
        if "translation" in n: n["translation"] = [v * k for v in n["translation"]]
        if "matrix" in n: m = n["matrix"]; n["matrix"] = m[:12] + [v * k for v in m[12:15]] + [m[15]]
    return True


def _roots(g: dict):
    scenes = g.get("scenes") or []
    if scenes: return list(scenes[g.get("scene", 0)].get("nodes", []))
    kids = {c for n in g.get("nodes", []) for c in n.get("children", [])}
    return [i for i in range(len(g.get("nodes", []))) if i not in kids]


def to_metres(path) -> bool:
    """Turn a centimetre GLB into metres, in place. False when the file already carries the metres stamp, so a file
    may pass through any number of times. Baked into the geometry; a file whose geometry cannot be rewritten gets its
    scene roots scaled by 0.01 instead (what glb_to_metres.py did for the 2026-11-04 batch), which reads the same."""
    with open(path, "rb") as f: data = f.read()
    ver, chunks = _chunks(data); g = _json(chunks)
    if units(g) == "m": return False
    k = 1.0 / CM_PER_M
    binc = next((raw for t, raw in chunks if t == BIN_CHUNK), None)
    if not _bake(g, binc, k):
        for r in _roots(g):
            n = g["nodes"][r]
            if "matrix" in n: n["matrix"] = [v * (k if i % 4 != 3 else 1.0) for i, v in enumerate(n["matrix"])]
            else:
                n["scale"] = [v * k for v in n.get("scale", [1, 1, 1])]
                if "translation" in n: n["translation"] = [v * k for v in n["translation"]]
    ext = g.setdefault("asset", {}).setdefault("extras", {})
    ext["units"] = "m"; ext["units_note"] = "metres; converted from the pipeline's centimetres by AssetAutoGenerator (glbinfo.to_metres)"
    _write(path, ver, g, chunks); return True


def set_uuid(path, uid: str, asset_name: str | None = None) -> bool:
    """Name the GLB's single mesh (node + mesh) `uid`, in place, without Blender: only the JSON chunk is rewritten.
    The UUID stays the same for good per product and per size (decided by Mukul 2026-10-06), so every rebuild
    (steps, Fix size, re-sizing, the final GLB) is renamed to it. Returns False for a file with several meshes."""
    with open(path, "rb") as f: data = f.read()
    magic, ver, _len = struct.unpack("<4sII", data[:12])
    if magic != GLB_MAGIC: raise ValueError("not a GLB")
    clen, ctype = struct.unpack("<I4s", data[12:20]); g = json.loads(data[20:20 + clen]); rest = data[20 + clen:]
    mesh_nodes = [n for n in g.get("nodes", []) if "mesh" in n]
    if len(mesh_nodes) != 1: return False
    n = mesh_nodes[0]; m = g["meshes"][n["mesh"]]
    if n.get("name") == uid and m.get("name") == uid: return True
    n["name"] = uid; m["name"] = uid
    if asset_name: n.setdefault("extras", {})["asset_name"] = asset_name
    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    body = struct.pack("<I4s", len(js), JSON_CHUNK) + js + rest
    tmp = str(path) + ".uuid.tmp"
    with open(tmp, "wb") as f: f.write(struct.pack("<4sII", magic, ver, 12 + len(body)) + body)
    os.replace(tmp, path); return True
