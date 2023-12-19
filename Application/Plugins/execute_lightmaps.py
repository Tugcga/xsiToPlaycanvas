import math
from mesh_process import get_mesh_area
from light_process import deactivate_lights, activate_lights, geather_lights
from bake import bake_diffuse_indirect
import OIIO_Py2Processor as processor


def bake_lightmaps(app, objects, mode, bake_size_index, bake_directory, bake_extension, bake_gamma, bake_padding, bake_denoise):
    if objects is None:
        objects = [v for v in app.Selection]
    else:
        objects = [v for v in objects]

    # find total area of each object and calculate corresponding lightmap size
    polygon_objects = []
    areas = []
    for obj in objects:
        obj_type = obj.Type
        if obj_type == "polymsh":
            vis_val = app.GetValue(obj.FullName + ".visibility.rendvis")
            if vis_val:
                polygon_objects.append(obj)
                obj_area = get_mesh_area(obj)
                areas.append(obj_area)

    objects = polygon_objects

    if len(objects) == 0:
        print("Select objects to bake lightmaps, skip the process")
        return True

    max_area = max(areas)
    downsizes = []
    for area in areas:
        # here we should find coefficient for each area of the object, and the use it in the size of the map
        ds = int(round(math.log(math.sqrt(max_area / area), 2.0)))
        downsizes.append(ds)

    lights = geather_lights(app)
    # remember the light strength
    light_settings = {}  # key - object id, value - (object, param_name, value)
    for l in lights:
        l_t = l.Type
        l_id = l.ObjectID
        if l_t == "cyclesSun":
            strength = app.GetValue(l.FullName + ".cyclesSun.power")
            light_settings[l_id] = (l, ".cyclesSun.power", strength)
        elif l_t == "cyclesPoint":
            strength = app.GetValue(l.FullName + ".cyclesPoint.power")
            light_settings[l_id] = (l, ".cyclesPoint.power", strength)
        elif l_t == "cyclesSpot":
            strength = app.GetValue(l.FullName + ".cyclesSpot.power")
            light_settings[l_id] = (l, ".cyclesSpot.power", strength)
        elif l_t == "cyclesArea":
            strength = app.GetValue(l.FullName + ".cyclesArea.power")
            light_settings[l_id] = (l, ".cyclesArea.power", strength)
        elif l_t == "light":
            strength = app.GetValue(l.FullName + ".light.soft_light.intensity")
            light_settings[l_id] = (l, ".light.soft_light.intensity", strength)

    if mode == 2:
        # separate process for mode = 2 (diffuse indirect)
        # the process is similar to probes
        for obj_index in range(len(objects)):
            obj = objects[obj_index]
            bake_diffuse_indirect(app,
                                  obj,
                                  bake_size_index - downsizes[obj_index],
                                  bake_directory,
                                  bake_extension,
                                  bake_padding,
                                  bake_gamma,
                                  1,
                                  "lightmap_",
                                  "lightmap_" + obj.FullName,
                                  True,
                                  bake_denoise)
    else:
        render_steps = 1 if mode == 0 else 3
        # if mode = 1, then we use three render steps:
        # 1. Combined
        # 2. without lights (only environment) combined
        # 3. with lights only direct (without indirect, glossy and emission)
        pathes_dict = {}  # key - object index, value - array of pathes [combined, environment, direct]
        for step in range(render_steps):
            name_postfix = ""
            if step == 0:
                activate_lights(light_settings)
                name_postfix = "_combined"
            elif step == 1:
                name_postfix = "_env"
                deactivate_lights(app, light_settings)
            elif step == 2:
                name_postfix = "_direct"
                activate_lights(app, light_settings)
            # enumerate objects
            for obj_index in range(len(objects)):
                obj = objects[obj_index]
                app.SelectObj(obj)
                app.AddCyclesBake()
                # set output directory
                if len(bake_directory) > 0:
                    app.SetValue(obj.FullName + ".CyclesBake.output_folder", bake_directory, "")
                # set texture extension
                app.SetValue(obj.FullName + ".CyclesBake.output_extension", bake_extension, "")
                # set taxture size
                app.SetValue(obj.FullName + ".CyclesBake.texture_size", bake_size_index - downsizes[obj_index], "")
                # swith to the second uv
                app.SetValue(obj.FullName + ".CyclesBake.uv_index", 1, "")
                # set output name
                app.SetValue(obj.FullName + ".CyclesBake.output_name", "lightmap_" + obj.Name + name_postfix, "")
                output_path = bake_directory + "\\" + "lightmap_" + obj.Name + name_postfix + "." + bake_extension
                if obj_index not in pathes_dict:
                    pathes_dict[obj_index] = []
                pathes_dict[obj_index].append(output_path)
                if step == 0 or step == 1:
                    app.SetValue(obj.FullName + ".CyclesBake.baking_shader", "Cycles Combined", "")
                    app.SetValue(obj.FullName + ".CyclesBake.baking_filter_indirect", True, "")
                    app.SetValue(obj.FullName + ".CyclesBake.baking_filter_glossy", True, "")
                    app.SetValue(obj.FullName + ".CyclesBake.baking_filter_emission", True, "")
                elif step == 2:
                    app.SetValue(obj.FullName + ".CyclesBake.baking_shader", "Cycles Combined", "")
                    app.SetValue(obj.FullName + ".CyclesBake.baking_filter_indirect", False, "")
                    app.SetValue(obj.FullName + ".CyclesBake.baking_filter_glossy", False, "")
                    app.SetValue(obj.FullName + ".CyclesBake.baking_filter_emission", False, "")
                # call bake
                rendermap = obj.Properties("RenderMap")
                if rendermap is None:
                    # there are no rendermap property on the object, add it
                    rendermap = obj.AddProperty("RenderMap")
                app.RegenerateMaps(obj.FullName + ".RenderMap", "")

        if mode == 1:
            # we should process rendered images for each baked object
            for obj_index in pathes_dict.keys():
                comb_path, env_path, direct_path = pathes_dict[obj_index]
                obj = objects[obj_index]
                out_path = bake_directory + "\\" + "lightmap_" + obj.Name + "_indirect" + "." + bake_extension
                processor.combine_three_textures(comb_path, direct_path, env_path, out_path)  # produce a - b + c
                processor.apply_gamma(out_path, out_path, bake_gamma)
                # and also add padding for indirect map
                processor.add_padding(out_path, out_path, bake_padding)
        for obj_index in pathes_dict.keys():
            obj = objects[obj_index]
            out_paths = pathes_dict[obj_index]
            for out_path in out_paths:
                processor.add_padding(out_path, out_path, bake_padding)
