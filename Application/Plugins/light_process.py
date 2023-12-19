def deactivate_lights(app, light_settings):
    for l_id, l_data in light_settings.items():
        app.SetValue(l_data[0].FullName + l_data[1], 0.0, "")


def activate_lights(app, light_settings):
    for l_id, l_data in light_settings.items():
        app.SetValue(l_data[0].FullName + l_data[1], l_data[2], "")


def walk_lights(app, root, output):
    t = root.Type
    if t == "cyclesSun" or t == "cyclesPoint" or t == "cyclesSpot" or t == "cyclesArea":
        if t == "cyclesArea":
            is_portal = app.GetValue(root.Name + ".cyclesArea.is_portal")
            if is_portal is False:
                output.append(root)
        else:
            output.append(root)
    elif t == "light":
        # find built-in light source
        output.append(root)

    for child in root.Children:
        walk_lights(app, child, output)


def geather_lights(app):
    # return all Cycles lights, which we should deactivate when bake indirect lighting
    project = app.ActiveProject2
    scene = project.ActiveScene
    root = scene.Root
    lights = []
    walk_lights(app, root, lights)
    return lights


def walk_direct_lights(app, root, output_array):
    t = root.Type
    if t == "cyclesSun" or t == "cyclesPoint" or t == "cyclesSpot":
        is_rendered = app.GetValue(root.FullName + ".visibility.rendvis")
        if is_rendered:
            output_array.append(root)
    elif t == "light":
        is_rendered = app.GetValue(root.FullName + ".visibility.rendvis")
        if is_rendered:
            output_array.append(root)

    for child in root.Children:
        walk_direct_lights(app, child, output_array)


def get_all_direct_lights(app):
    root = app.ActiveSceneRoot
    lights = []
    walk_direct_lights(app, root, lights)
    return lights
