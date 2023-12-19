from win32com.client import constants
from mesh_process import hierarch_walk
from math_process import xsi_matrix_to_matrix, apply_matrix


def join_by_materials(app, objects, join_pack):
    if objects is None:
        objects = [v for v in app.Selection]
    else:
        objects = [v for v in objects]

    polymesh_objects = []
    for obj in objects:
        hierarch_walk(app, obj, polymesh_objects)

    # next find all materials of the selected objects
    materials = {}  # key - material id, value - array of objects with this material
    materials_map = {}
    for obj in polymesh_objects:
        obj_mat = obj.Material
        obj_mat_id = obj_mat.ObjectID
        if obj_mat_id in materials:
            materials[obj_mat_id].append(obj)
        else:
            materials[obj_mat_id] = [obj]
            materials_map[obj_mat_id] = obj_mat

    # next union all objects in each array
    for mat_id, mat_objects in materials.items():
        material_name = mat_objects[0].Material.Name
        join_vertices = [[], [], []]  # arrays for x, y and z components
        join_polygons = []
        uv_first = [[], [], []]
        uv_second = [[], [], []]
        for obj in mat_objects:
            app.SetValue(obj.Name + ".visibility.rendvis")  # deactivate object

            polymesh = obj.GetActivePrimitive3().GetGeometry3()
            sample_clusters = polymesh.Clusters.Filter("sample")
            uv_clusters = []
            for s_cls in sample_clusters:
                if s_cls.IsAlwaysComplete():
                    for prop in s_cls.Properties:
                        if prop.Type == "uvspace":
                            uv_data = prop.Elements.Array  # has the form ((u-coordinates), (v-coordinates), (w-coordinates = 0.0))
                            uv_clusters.append(uv_data)
            if len(uv_clusters) > 0:
                obj_tfm = obj.Kinematics.Global.Transform.Matrix4
                obj_matrix = xsi_matrix_to_matrix(obj_tfm)
                polymesh_vertices, polymesh_polygons = polymesh.Get2()
                # apply global transform to vertices
                points = [(polymesh_vertices[0][i], polymesh_vertices[1][i], polymesh_vertices[2][i], 1) for i in range(len(polymesh_vertices[0]))]
                tfm_points = [apply_matrix(obj_matrix, v)[0:3] for v in points]
                polygon_shift = len(join_vertices[0])
                for p in tfm_points:
                    join_vertices[0].append(p[0])
                    join_vertices[1].append(p[1])
                    join_vertices[2].append(p[2])
                # copy values form first uv_cluster
                if len(uv_clusters) > 0:
                    uv_first[0].extend(uv_clusters[0][0])
                    uv_first[1].extend(uv_clusters[0][1])
                    uv_first[2].extend(uv_clusters[0][2])
                    second_index = 1 if len(uv_clusters) > 1 else 0
                    uv_second[0].extend(uv_clusters[second_index][0])
                    uv_second[1].extend(uv_clusters[second_index][1])
                    uv_second[2].extend(uv_clusters[second_index][2])

                step = 0
                get_size = True
                for v in polymesh_polygons:
                    if get_size:
                        step = v
                        get_size = False
                        join_polygons.append(v)
                    else:
                        join_polygons.append(v + polygon_shift)
                        step = step - 1
                        if step == 0:
                            get_size = True
            else:
                print("object " + obj.Name + " does not contains uv-coordinates, skip it")
        # create new object
        new_obj = app.GetPrim("EmptyPolygonMesh", "combined_" + material_name, "", "")
        app.AssignMaterial([materials_map[mat_id], new_obj], "siLetLocalMaterialsOverlap")
        new_geo = new_obj.GetActivePrimitive3().GetGeometry3()
        if len(join_polygons) > 0:
            new_geo.Set(join_vertices, join_polygons)
            # add uvs
            # create new uv claster
            uvs_cls = new_geo.AddCluster(constants.siSampledPointCluster, "UV")
            # add the prop
            new_first_uv_prop = app.AddProp("Texture Projection", uvs_cls.FullName, constants.siDefaultPropagation, "Texture_Projection")
            fist_uv_prop = new_first_uv_prop[1][0]
            fist_uv_prop.Elements.Array = tuple([tuple(uv_first[0]), tuple(uv_first[1]), tuple(uv_first[2])])

            new_second_uv_prop = app.AddProp("Texture Projection", uvs_cls.FullName, constants.siDefaultPropagation, "Texture_Projection")
            second_uv_prop = new_second_uv_prop[1][0]
            second_uv_prop.Elements.Array = tuple([tuple(uv_second[0]), tuple(uv_second[1]), tuple(uv_second[2])])

            # call uv packer
            if join_pack:
                app.SelectObj(new_obj.Name)
                app.UVPacker(app.Selection, True, 1, 0, 512, 512, 4.0)
