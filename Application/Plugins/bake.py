import hashlib
import time
from light_process import get_all_direct_lights
import OIIO_Py2Processor as processor


def bake_diffuse_indirect(app, obj, size, directory, extension, padding, gamma, uv_index, suffix, final_name, bake_combined, denoise_output, apply_srgb):
    # add bake property
    app.SelectObj(obj)
    app.AddCyclesBake()
    # create hash from given time
    m = hashlib.md5()
    m.update(str(time.time()))
    hash_str = "_" + m.hexdigest()
    output_pathes = []
    names_dir = {0: "_only_indirect",
                 1: "_only_direct",
                 2: "_combined"}
    render_samples = app.GetValue("Passes.Cycles_Renderer_Options.sampling_render_samples")
    direct_lights = get_all_direct_lights(app)
    for step in range(3 if bake_combined else 2):
        name_postfix = names_dir[step]
        app.SetValue(obj.FullName + ".CyclesBake.texture_size", size, "")
        app.SetValue(obj.FullName + ".CyclesBake.output_folder", directory + "\\temp_images", "")
        # app.SetValue(obj.FullName + ".CyclesBake.output_extension", extension, "")
        app.SetValue(obj.FullName + ".CyclesBake.output_extension", "exr", "")
        app.SetValue(obj.FullName + ".CyclesBake.output_name", suffix + obj.Name + name_postfix + hash_str, "")
        app.SetValue(obj.FullName + ".CyclesBake.uv_index", uv_index, "")
        output_path = directory + "\\temp_images\\" + suffix + obj.Name + name_postfix + hash_str + "." + "exr"
        output_pathes.append(output_path)
        if step == 0:
            # indirect mode
            app.SetValue(obj.FullName + ".CyclesBake.baking_shader", "Cycles Diffuse", "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_direct", False, "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_indirect", True, "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_color", False, "")
        elif step == 1:
            # direct mode without lights
            # we need it to catch sky and emissive lights
            # hide all direct lights
            for light in direct_lights:
                app.SetValue(light.FullName + ".visibility.rendvis", False, "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_shader", "Cycles Diffuse", "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_direct", True, "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_indirect", False, "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_color", False, "")
        else:
            # combined mode
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_direct", True, "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_indirect", True, "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_filter_color", True, "")
            app.SetValue(obj.FullName + ".CyclesBake.baking_shader", "Cycles Combined", "")
            # set low samples
            app.SetValue("Passes.Cycles_Renderer_Options.sampling_render_samples", 4, "")

        rendermap = obj.Properties("RenderMap")
        if rendermap is None:
            rendermap = obj.AddProperty("RenderMap")
        app.RegenerateMaps(obj.FullName + ".RenderMap", "")

        if step == 1:
            for light in direct_lights:
                app.SetValue(light.FullName + ".visibility.rendvis", True, "")
        if step == 2:
            app.SetValue("Passes.Cycles_Renderer_Options.sampling_render_samples", render_samples, "")
    # we should combine rendered passes
    combined_temp_path = directory + "\\temp_images\\" + suffix + obj.Name + "_combined_direct_indirect" + hash_str + "." + "exr"
    noised_path = directory + "\\temp_images\\" + suffix + obj.Name + "_noise" + hash_str + "." + "exr"
    denoised_path = directory + "\\temp_images\\" + suffix + obj.Name + "_denoise" + hash_str + "." + "exr"
    gamma_path = directory + "\\temp_images\\" + suffix + obj.Name + "_gamma" + hash_str + "." + "exr"
    result_path = directory + "\\" + final_name + "." + extension

    processor.combine_add(output_pathes[0], output_pathes[1], combined_temp_path)
    if bake_combined:
        # replace alpha from combined pass
        processor.replace_alpha(combined_temp_path, output_pathes[2], noised_path)
    if denoise_output:
        # denoise
        processor.denoise(noised_path if bake_combined else combined_temp_path, denoised_path)
    # apply gamma
    gamma_in_path = ""
    if bake_combined and denoise_output:
        gamma_in_path = denoised_path
    elif bake_combined and not denoise_output:
        gamma_in_path = noised_path
    elif not bake_combined and denoise_output:
        gamma_in_path = denoised_path
    else:
        gamma_in_path = combined_temp_path
    processor.apply_gamma(gamma_in_path, gamma_path if bake_combined else result_path, gamma)
    # apply padding
    if bake_combined:
        processor.add_padding(gamma_path, result_path, padding)
    if apply_srgb:
        processor.apply_srgb(result_path, result_path)
    # remove unnecesery files
    # os.remove(output_pathes[0])
    # os.remove(output_pathes[1])
    # if bake_combined:
        # os.remove(output_pathes[2])
    # os.remove(combined_temp_path)  // also locked
    # if bake_combined:
        # os.remove(noised_path)
    # os.remove(denoised_path)  # the file is locked by Softimage
    # if bake_combined:
        # os.remove(gamma_path)
    print("FINISH baking " + obj.Name)
