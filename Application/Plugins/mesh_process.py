def read_polygon_structure(xsi_obj):
    verts = []
    polys = []
    sizes = []
    xsi_polydata = xsi_obj.GetActivePrimitive3().Geometry.Get2()
    xsi_vertices = xsi_polydata[0]
    xsi_polygons = xsi_polydata[1]
    for i in range(len(xsi_vertices[0])):
        verts.append(xsi_vertices[0][i])
        verts.append(xsi_vertices[1][i])
        verts.append(xsi_vertices[2][i])
    is_size = True
    size_counter = 0
    size_value = 0
    for v in xsi_polygons:
        if is_size:
            sizes.append(v)
            is_size = False
            size_counter = 0
            size_value = v
        else:
            polys.append(v)
            size_counter += 1
            if size_counter == size_value:
                is_size = True
    # reverse polygons and sizes array
    # to output in clockwise direction
    # polys = polys[::-1]
    # sizes = sizes[::-1]
    return (verts, polys, sizes)


def heron(a, b, c):
    s = (a + b + c) / 2
    area = (s * (s - a) * (s - b) * (s - c)) ** 0.5
    return area


def distance3d(x1, y1, z1, x2, y2, z2):
    a = (x1 - x2)**2 + (y1 - y2)**2 + (z1 - z2)**2
    d = a ** 0.5
    return d


def get_triangle_area(vertices, v0, v1, v2):
    x1 = vertices[0][v0]
    x2 = vertices[0][v1]
    x3 = vertices[0][v2]
    y1 = vertices[1][v0]
    y2 = vertices[1][v1]
    y3 = vertices[1][v2]
    z1 = vertices[2][v0]
    z2 = vertices[2][v1]
    z3 = vertices[2][v2]
    a = distance3d(x1, y1, z1, x2, y2, z2)
    b = distance3d(x2, y2, z2, x3, y3, z3)
    c = distance3d(x3, y3, z3, x1, y1, z1)
    area = heron(a, b, c)
    return abs(area)


def get_mesh_area(obj):
    polymesh = obj.GetActivePrimitive3().GetGeometry3()
    vertices, polygons = polymesh.Get2()
    # vertices has the form ((x1, x2, ...), (y1, y2, ...), (z1, z2, ...))
    is_size = True
    current_size = 0
    size_step = 0
    triangle_start = 0
    area = 0.0
    for i in range(len(polygons)):
        v = polygons[i]
        if is_size:
            current_size = v
            size_step = 0
            is_size = False
        else:
            if size_step == 0:
                triangle_start = polygons[i]
            elif size_step > 1:
                area += get_triangle_area(vertices, triangle_start, polygons[i - 1], polygons[i])
            size_step += 1
        if size_step == current_size:
            is_size = True
    return area


def add_to_array(obj, array):
    obj_id = obj.ObjectID
    for v in array:
        v_id = v.ObjectID
        if obj_id == v_id:
            return None
    array.append(obj)


def hierarch_walk(app, root_object, output):
    t = root_object.Type
    if t == "polymsh":
        # may this object is hidden
        vis_val = app.GetValue(root_object.Name + ".visibility.viewvis")
        if vis_val:
            add_to_array(root_object, output)

    children = root_object.Children
    for obj in children:
        hierarch_walk(app, obj, output)
