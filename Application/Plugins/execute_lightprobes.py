from win32com.client import constants
import json
import random
import math
from mesh_process import get_mesh_area
from bake import bake_diffuse_indirect
from delaunay import triangulate
import OIIO_Py2Processor as processor


math_pi = 3.1415926535


def bake_probes(app, obj, probes_bake_size, probes_bake_gamma, probes_bake_padding, probes_bake_directory, probes_bake_extension, probes_bake_json):
    # set invisible
    app.AddCyclesMesh()
    app.SetValue(obj.Name + ".CyclesMesh.ray_visibility_camera", False, "")
    app.SetValue(obj.Name + ".CyclesMesh.ray_visibility_diffuse", False, "")
    app.SetValue(obj.Name + ".CyclesMesh.ray_visibility_glossy", False, "")
    app.SetValue(obj.Name + ".CyclesMesh.ray_visibility_transmission", False, "")
    app.SetValue(obj.Name + ".CyclesMesh.ray_visibility_volume_scatter", False, "")
    app.SetValue(obj.Name + ".CyclesMesh.ray_visibility_shadow", False, "")

    bake_diffuse_indirect(app,
                          obj,
                          probes_bake_size,
                          probes_bake_directory,
                          probes_bake_extension,
                          probes_bake_padding,
                          probes_bake_gamma,
                          0,
                          "probes_",
                          probes_bake_json,
                          False,
                          False)
    result_path = probes_bake_directory + "\\" + probes_bake_json + "." + probes_bake_extension
    # after bake images we should convert islands to SH-coefficients
    # read file with probes data
    total_width = 2**(probes_bake_size + 5)
    total_height = total_width
    export_data = None
    export_path = probes_bake_directory + "\\" + probes_bake_json + ".json"
    with open(export_path, "r") as file:
        export_data = json.load(file)
        probes = export_data["probes"]
        for probe in probes:
            # each probe is a dict, contains scale, coordinates and offset
            # scale and offset we should use to read the image from rendered texture
            offset = probe["offset"]
            scale = probe["scale"]
            island_width = int(total_width * scale[0])
            island_height = int(total_height * scale[1])
            probe_coefficients = processor.extract_spherical_harmonics(
                result_path,
                int(total_width * offset[0]),
                total_height - int(total_height * offset[1]) - island_height,
                island_width,
                island_height,
                1.0)
            # add coefficients
            probe["sh"] = probe_coefficients
    # rewrite the file
    with open(export_path, "w") as file:
        file.write(json.dumps(export_data, indent=4))


def create_probes(app,
                  base_object,
                  probes_density,
                  probe_generate_iterations,
                  probe_shape_radius,
                  probe_shape_subdivs,
                  probe_shape_v_delta,
                  probes_bake_size,
                  probes_bake_padding,
                  probes_bake_directory,
                  probes_bake_json):
    pointcloud = app.GetPrim("PointCloud")
    app.ApplyOp("ICETree", pointcloud, "siNode", "", "", 0)
    app.AddICENode("GetDataNode", pointcloud.Name + ".pointcloud.ICETree")
    app.SetValue(pointcloud.Name + ".pointcloud.ICETree.SceneReferenceNode.reference", base_object.Name, "")
    app.AddICECompoundNode("Regularize Points", pointcloud.Name + ".pointcloud.ICETree")
    app.SetValue(pointcloud.Name + ".pointcloud.ICETree.Regularize_Points.Iterations", 1, "")
    app.ConnectICENodes(pointcloud.Name + ".pointcloud.ICETree.Regularize_Points.Geometry", pointcloud.Name + ".pointcloud.ICETree.SceneReferenceNode.value")
    app.ConnectICENodes(pointcloud.Name + ".pointcloud.ICETree.port1", pointcloud.Name + ".pointcloud.ICETree.Regularize_Points.Execute")
    app.SetValue(pointcloud.Name + ".pointcloud.ICETree.Regularize_Points.Iterations", probe_generate_iterations, "")
    obj_area = get_mesh_area(base_object)
    app.SetValue(pointcloud.Name + ".pointcloud.ICETree.Regularize_Points.Points_Count", int(obj_area * probes_density), "")
    app.SetValue("pointcloud.pointcloud.ICETree.Regularize_Points.Seed", random.randint(1, 1024), "")

    # read point positions
    pointcloud_geo = pointcloud.ActivePrimitive.Geometry
    pointcloud_pos_attr = pointcloud_geo.GetICEAttributeFromName("PointPosition")
    pointcloud_coords = pointcloud_pos_attr.DataArray
    points = []
    for p in pointcloud_coords:
        points.append((p.X, p.Y, p.Z))

    # delete pointcloud
    app.DeleteObj(pointcloud)

    # create spheres arond points
    r = probe_shape_radius
    u_steps = probe_shape_subdivs * 2
    v_steps = probe_shape_subdivs
    v_delta = probe_shape_v_delta

    u_step_size = 2.0 * math_pi / (u_steps - 1)
    v_step_size = (math_pi - v_delta) / (v_steps - 1)

    points_count = len(points)
    points_u_count = 0
    points_v_count = 0
    find_step = 0
    while points_u_count * points_v_count < points_count:
        if find_step == 0:
            points_u_count += 1
        else:
            points_v_count += 1
        find_step += 1
        if find_step == 3:
            find_step = 0

    uv_island_size_u = 1.0 / points_u_count
    uv_island_size_v = 1.0 / points_v_count

    # calculate padding by using texture size and input padding in pixels
    bake_size_pixels = 2 ** (probes_bake_size + 5)
    uv_padding = float(probes_bake_padding * 2) / float(bake_size_pixels)

    uv_u_step = (uv_island_size_u - uv_padding) / (u_steps - 1)
    uv_v_step = (uv_island_size_v - uv_padding) / (v_steps - 1)

    vertices = []
    polygons = []
    uvs = []
    point_index = 0
    island_u = 0
    island_v = 0

    export_data = {"probes": []}
    positions_2d = []

    for point in points:
        offset_u = island_u * uv_island_size_u + uv_padding / 2.0
        offset_v = island_v * uv_island_size_v + uv_padding / 2.0
        for v in range(v_steps):
            v_value = v_delta / 2.0 + v * v_step_size
            for u in range(u_steps):
                u_value = u * u_step_size
                if v > 0 and u > 0:
                    if u < u_steps - 1:
                        polygons += [4,
                                     point_index,
                                     point_index - (u_steps - 1),
                                     point_index - (u_steps - 1) - 1,
                                     point_index - 1]
                    else:
                        polygons += [4,
                                     point_index - (u_steps - 2) - 1,
                                     point_index - (u_steps - 2) - (u_steps - 1) - 1,
                                     point_index - (u_steps - 2) - 1 - 1,
                                     point_index - 1]
                    uvs += [(offset_u + u * uv_u_step, offset_v + v * uv_v_step),
                            (offset_u + u * uv_u_step, offset_v + (v - 1) * uv_v_step),
                            (offset_u + (u - 1) * uv_u_step, offset_v + (v - 1) * uv_v_step),
                            (offset_u + (u - 1) * uv_u_step, offset_v + v * uv_v_step)]
                if u < u_steps - 1:
                    vertices.append((r * math.cos(v_value - math_pi / 2.0) * math.cos(u_value) + point[0],
                                     r * math.sin(v_value - math_pi / 2.0) + 2.0 * r + point[1],
                                     r * math.cos(v_value - math_pi / 2.0) * math.sin(u_value) + point[2]))
                    point_index += 1
        island_u += 1
        if island_u >= points_u_count:
            island_u = 0
            island_v += 1
        export_data["probes"].append({
            "scale": [uv_island_size_u - uv_padding, uv_island_size_v - uv_padding],
            "offset": [offset_u, offset_v],
            "coordinates": [point[0], 2.0 * r + point[1], point[2]]})
        positions_2d.append((point[0], point[2]))

    # build triangulation
    triangles = triangulate(positions_2d)
    # add to the json data
    export_data["triangulation"] = triangles

    root = app.ActiveSceneRoot
    mesh_obj = root.AddGeometry("EmptyPolygonMesh")
    app.SetValue(mesh_obj.Name + ".Name", "probes_mesh", "")
    mesh_geo = mesh_obj.ActivePrimitive.Geometry
    vertices_x = [v[0] for v in vertices]
    vertices_y = [v[1] for v in vertices]
    vertices_z = [v[2] for v in vertices]
    mesh_geo.Set([vertices_x, vertices_y, vertices_z], polygons)

    uvs_cls = mesh_geo.AddCluster(constants.siSampledPointCluster, "UVCoordinates")
    new_uv_prop = app.AddProp("Texture Projection", uvs_cls.FullName, constants.siDefaultPropagation, "Texture_Projection")
    uv_prop = new_uv_prop[1][0]
    uv_u = [v[0] for v in uvs]
    uv_v = [v[1] for v in uvs]
    uv_w = [0.0] * len(uv_u)
    uv_prop.Elements.Array = [uv_u, uv_v, uv_w]
    app.SelectObj(mesh_obj)

    # try to find material for probes
    probes_mat_name = "probes_material"
    probes_mat = None
    scene = app.ActiveProject2.ActiveScene
    for library in scene.MaterialLibraries:
        for mat in library.Items:
            mat_name = mat.Name
            if mat_name == probes_mat_name:
                probes_mat = mat
    if probes_mat is None:
        # no material
        # create one and assign it to the probes mesh
        new_mat = mesh_obj.AddMaterial("Phong")
        app.SetValue(str(new_mat.Library) + "." + str(new_mat.Name) + ".Name", probes_mat_name, "")
        mat_str = str(new_mat.Library) + "." + str(new_mat.Name)
        app.CreateShaderFromProgID("CyclesShadersPlugin." + "CyclesDiffuseBSDF" + ".1.0", mat_str, "cycDiffuseBSDF")
        app.SIConnectShaderToCnxPoint(mat_str + ".cycDiffuseBSDF.outBSDF", mat_str + ".surface", False)
        app.DisconnectAndDeleteOrUnnestShaders(mat_str + ".Phong", mat_str)
        app.SetValue(mat_str + ".cycDiffuseBSDF.Color.red", 1, "")
        app.SetValue(mat_str + ".cycDiffuseBSDF.Color.green", 1, "")
        app.SetValue(mat_str + ".cycDiffuseBSDF.Color.blue", 1, "")
    else:
        app.AssignMaterial(str(probes_mat.Library) + "." + probes_mat.Name + "," + mesh_obj.Name, "siLetLocalMaterialsOverlap")

    # save export data to json
    export_path = probes_bake_directory + "\\" + probes_bake_json + ".json"
    with open(export_path, "w") as file:
        file.write(json.dumps(export_data, indent=4))
