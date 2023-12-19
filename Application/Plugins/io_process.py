import struct


def write_polygons_to_file(verts, polys, sizes, triangles, dim_mode, gen_triangulation, y_shift, file):
    write_verts = []
    if dim_mode == 0:
        # 3d-mode
        for i in range(len(verts) // 3):
            write_verts.append(verts[3 * i])
            write_verts.append(verts[3 * i + 1] + y_shift)
            write_verts.append(verts[3 * i + 2])
    else:
        # 2d-mode, only x and z, so, ignore y shift
        for i in range(len(verts) // 3):
            write_verts.append(verts[3 * i])
            write_verts.append(verts[3 * i + 2])
    file.write(" ".join([str(v) for v in write_verts]))
    file.write("\n")
    if gen_triangulation:
        file.write(" ".join([str(v) for v in triangles]))
    else:
        file.write(" ".join([str(v) for v in polys]))
        file.write("\n")
        file.write(" ".join([str(v) for v in sizes]))


def write_polygons_to_bin_file(verts, polys, sizes, y_shift, file):
    out_bytes = bytearray()
    inf_float_bytes = struct.pack(">f", float("inf"))
    for v in range(len(verts) // 3):
        out_bytes.extend(struct.pack(">f", verts[3 * v]))
        out_bytes.extend(struct.pack(">f", verts[3 * v + 1] + y_shift))
        out_bytes.extend(struct.pack(">f", verts[3 * v + 2]))
    out_bytes.extend(inf_float_bytes)

    for p in polys:
        out_bytes.extend(struct.pack(">i", p))
    out_bytes.extend(inf_float_bytes)

    for s in sizes:
        out_bytes.extend(struct.pack(">i", s))
    out_bytes.extend(inf_float_bytes)

    file.write(out_bytes)
