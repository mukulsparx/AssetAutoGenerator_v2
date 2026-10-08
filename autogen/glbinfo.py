"""Reads triangle count, size (cm) and mesh name straight from a GLB file (no Blender needed)."""
import json, struct


def info(path) -> dict:
    with open(path, "rb") as f:
        magic, _ver, _len = struct.unpack("<4sII", f.read(12))
        if magic != b"glTF": raise ValueError("not a GLB")
        clen, ctype = struct.unpack("<I4s", f.read(8)); g = json.loads(f.read(clen))
    tris = 0; lo = [1e18] * 3; hi = [-1e18] * 3; names = []
    for node in g.get("nodes", []):
        if "mesh" not in node: continue
        mesh = g["meshes"][node["mesh"]]; names.append(mesh.get("name") or node.get("name", ""))
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4: continue
            acc = g["accessors"][prim["indices"]] if "indices" in prim else g["accessors"][prim["attributes"]["POSITION"]]
            tris += acc["count"] // 3
            pos = g["accessors"][prim["attributes"]["POSITION"]]
            if "min" in pos and "max" in pos:
                s = node.get("scale", [1, 1, 1])
                for i in range(3):
                    a, b = pos["min"][i] * s[i], pos["max"][i] * s[i]
                    t = node.get("translation", [0, 0, 0])[i]
                    lo[i] = min(lo[i], min(a, b) + t); hi[i] = max(hi[i], max(a, b) + t)
    # glTF is Y-up: width = X, height = Y, depth = Z. The pipeline exports centimetres.
    size = [round(hi[0] - lo[0], 1), round(hi[2] - lo[2], 1), round(hi[1] - lo[1], 1)] if tris else None
    return {"tris": tris, "dims_cm": size, "mesh_names": names, "mesh_count": len(names),
            "mesh_uuid": names[0] if len(names) == 1 else None}


def set_uuid(path, uid: str, asset_name: str | None = None) -> bool:
    """Name the GLB's single mesh (node + mesh) `uid`, in place, without Blender: only the JSON chunk is rewritten.
    The UUID stays the same for good per product and per size (decided by Mukul 2026-10-06), so every rebuild
    (steps, Fix size, re-sizing, the final GLB) is renamed to it. Returns False for a file with several meshes."""
    with open(path, "rb") as f: data = f.read()
    magic, ver, _len = struct.unpack("<4sII", data[:12])
    if magic != b"glTF": raise ValueError("not a GLB")
    clen, ctype = struct.unpack("<I4s", data[12:20]); g = json.loads(data[20:20 + clen]); rest = data[20 + clen:]
    mesh_nodes = [n for n in g.get("nodes", []) if "mesh" in n]
    if len(mesh_nodes) != 1: return False
    n = mesh_nodes[0]; m = g["meshes"][n["mesh"]]
    if n.get("name") == uid and m.get("name") == uid: return True
    n["name"] = uid; m["name"] = uid
    if asset_name: n.setdefault("extras", {})["asset_name"] = asset_name
    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    body = struct.pack("<I4s", len(js), b"JSON") + js + rest
    tmp = str(path) + ".uuid.tmp"
    with open(tmp, "wb") as f: f.write(struct.pack("<4sII", magic, ver, 12 + len(body)) + body)
    import os; os.replace(tmp, path); return True
