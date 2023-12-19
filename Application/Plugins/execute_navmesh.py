from win32com.client import constants
import recastdetour as rd
from math_process import xsi_matrix_to_matrix, apply_matrix


navmesh_id = None
navmesh = None


def get_navmesh():
    global navmesh
    return navmesh


def get_navmesh_id():
    global navmesh_id
    return navmesh_id


def build_navmesh(app,
                  objects, cellSize=0.3, cellHeight=0.2, partition=0, agentHeight=2.0, agentRadius=0.6, agentMaxClimb=0.9, agentMaxSlope=45.0,
                  regionMinSize=8.0, regionMergeSize=20.0, edgeMaxLen=12.0, edgeMaxError=1.3, vertsPerPoly=6.0, detailSampleDist=6.0, detailSampleMaxError=1.0,
                  gen_triangulation=False):
    app.LogMessage("BuildNavmesh_Execute called", constants.siVerbose)
    # create navmesh object
    global navmesh
    if navmesh is None:
        navmesh = rd.Navmesh()
    # next, init it by geometry
    vertices = []
    faces = []
    index_shift = 0
    global navmesh_id
    if len(objects) > 0:
        for obj in objects:
            if obj.Properties("Visibility").Parameters("viewvis").Value:
                # filter generated navmesh
                if (navmesh_id is not None and obj.ObjectID != navmesh_id) or (navmesh_id is None):
                    glb = obj.Kinematics.Global
                    tfm = glb.Transform
                    tfm_matrix = tfm.Matrix4
                    geo = obj.GetActivePrimitive3().Geometry
                    if len(geo.Points) > 0:
                        geo_vertices, geo_faces = geo.Get2()
                        points = [(geo_vertices[0][i], geo_vertices[1][i], geo_vertices[2][i], 1) for i in range(len(geo_vertices[0]))]
                        m = xsi_matrix_to_matrix(tfm_matrix)
                        tfm_points = [apply_matrix(m, v)[0:3] for v in points]
                        # add coordinates to the global list
                        for p in tfm_points:
                            vertices.append(p[0])
                            vertices.append(p[1])
                            vertices.append(p[2])
                        # add faces to faces global list
                        steps = 0
                        for v in geo_faces:
                            if steps == 0:
                                faces.append(v)
                                steps = v
                            else:
                                faces.append(v + index_shift)
                                steps = steps - 1
                        index_shift += len(tfm_points)
        navmesh.init_by_raw(vertices, faces)
        settings = {"cellSize": cellSize,
                    "cellHeight": cellHeight,
                    "agentHeight": agentHeight,
                    "agentRadius": agentRadius,
                    "agentMaxClimb": agentMaxClimb,
                    "agentMaxSlope": agentMaxSlope,
                    "regionMinSize": regionMinSize,
                    "regionMergeSize": regionMergeSize,
                    "edgeMaxLen": edgeMaxLen,
                    "edgeMaxError": edgeMaxError,
                    "vertsPerPoly": vertsPerPoly,
                    "detailSampleDist": detailSampleDist,
                    "detailSampleMaxError": detailSampleMaxError}
        navmesh.set_settings(settings)
        navmesh.set_partition_type(partition)
        navmesh.build_navmesh()
        if gen_triangulation:  # create triangulated object
            nm_vertices, nm_triangles = navmesh.get_navmesh_trianglulation()

            # build arrays for geometry
            verts_count = len(nm_vertices) // 3
            nm_geo_verts = [[nm_vertices[3 * i] for i in range(verts_count)], [nm_vertices[3 * i + 1] for i in range(verts_count)], [nm_vertices[3 * i + 2] for i in range(verts_count)]]
            nm_geo_verts = [tuple(nm_geo_verts[0]), tuple(nm_geo_verts[1]), tuple(nm_geo_verts[2])]
            nm_geo_faces = []
            for i in range(len(nm_triangles) // 3):
                nm_geo_faces.append(3)
                nm_geo_faces.append(nm_triangles[3 * i])
                nm_geo_faces.append(nm_triangles[3 * i + 1])
                nm_geo_faces.append(nm_triangles[3 * i + 2])
        else:  # create mesh from polygons
            nm_vertices, nm_polygons, nm_sizes = navmesh.get_navmesh_poligonization()
            verts_count = len(nm_vertices) // 3
            nm_geo_verts = [[nm_vertices[3 * i] for i in range(verts_count)], [nm_vertices[3 * i + 1] for i in range(verts_count)], [nm_vertices[3 * i + 2] for i in range(verts_count)]]
            nm_geo_verts = [tuple(nm_geo_verts[0]), tuple(nm_geo_verts[1]), tuple(nm_geo_verts[2])]
            nm_geo_faces = []
            j = 0
            for i in range(len(nm_sizes)):
                nm_geo_faces.append(nm_sizes[i])
                for k in range(nm_sizes[i]):
                    nm_geo_faces.append(nm_polygons[j])
                    j += 1

        # create new object
        if navmesh_id is not None:
            nm_obj = app.GetObjectFromID2(navmesh_id)
            if nm_obj is not None:
                app.DeleteObj(nm_obj)
        nm_obj = app.GetPrim("EmptyPolygonMesh", "navmesh", "", "")
        nm_obj.Properties("Visibility").Parameters("rendvis").Value = False
        nm_obj.Properties("Visibility").Parameters("selectability").Value = False
        navmesh_id = nm_obj.ObjectID
        nm_geo = nm_obj.GetActivePrimitive3().Geometry
        if len(nm_geo_faces) > 0:
            nm_geo.Set(nm_geo_verts, nm_geo_faces)
    return navmesh
