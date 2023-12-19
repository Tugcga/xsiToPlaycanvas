#include <iostream>

#include "OpenImageIO/imagebuf.h"
#include "OpenImageIO/imagebufalgo.h"

#include "OpenImageDenoise/oidn.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "utilities/utilities.h"
#include "spherical_harmonics/sh.h"

namespace py = pybind11;

void combine_three_textures(std::string path_01, std::string path_02, std::string path_03, std::string output)
{
    OIIO::ImageBuf buffer_01(path_01);
    OIIO::ImageBuf buffer_02(path_02);
    OIIO::ImageBuf buffer_03(path_03);

    OIIO::ImageBuf subtuct = OIIO::ImageBufAlgo::sub(buffer_01, buffer_02);
    OIIO::ImageBuf combine = OIIO::ImageBufAlgo::add(subtuct, buffer_03);

    combine.write(output);
}

void combine_add(std::string background_path, std::string overground_path, std::string output_path)
{
    OIIO::ImageBuf buffer_01(background_path);
    OIIO::ImageBuf buffer_02(overground_path);

    OIIO::ImageBuf combine = OIIO::ImageBufAlgo::add(buffer_01, buffer_02);
    combine.write(output_path);
}

void replace_alpha(std::string main_path, std::string alpha_source_path, std::string output_path)
{
    OIIO::ImageBuf main_buffer(main_path);
    OIIO::ImageBuf alpha_buffer(alpha_source_path);

    OIIO::ImageBuf main_rgb = OIIO::ImageBufAlgo::channels(main_buffer, 3, {});
    OIIO::ImageBuf alpha = OIIO::ImageBufAlgo::channels(alpha_buffer, 1, 3);

    OIIO::ImageBuf combine = OIIO::ImageBufAlgo::channel_append(main_rgb, alpha);

    combine.write(output_path);
}

void remove_alpha(std::string input_path, std::string output_path)
{
    OIIO::ImageBuf main_buffer(input_path);

    OIIO::ImageBuf main_rgb = OIIO::ImageBufAlgo::channels(main_buffer, 3, {});

    main_rgb.write(output_path);
}

void apply_gamma(std::string input_path, std::string output_path, float gamma)
{
    OIIO::ImageBuf buffer(input_path);
    const float g = 1.0f / gamma;
    OIIO::ImageBufAlgo::pow(buffer, buffer, { g, g, g, 1.0f });

    buffer.write(output_path);
}

void add_padding(std::string input_path, std::string output_path, int padding)
{
    OIIO::ImageBuf input(input_path);
    OIIO::ImageBuf shifted(input.spec());
    OIIO::ImageBuf result(input.spec());

    for (int step = 0; step < padding; step++)
    {
        OIIO::ImageBufAlgo::paste(shifted, 1, 0, 0, 0, input);
        OIIO::ImageBufAlgo::over(result, shifted, result);
        shifted.reset();
        OIIO::ImageBufAlgo::paste(shifted, -1, 0, 0, 0, input);
        OIIO::ImageBufAlgo::over(result, shifted, result);
        shifted.reset();
        OIIO::ImageBufAlgo::paste(shifted, 0, 1, 0, 0, input);
        OIIO::ImageBufAlgo::over(result, shifted, result);
        shifted.reset();
        OIIO::ImageBufAlgo::paste(shifted, 0, -1, 0, 0, input);
        OIIO::ImageBufAlgo::over(result, shifted, result);

        OIIO::ImageBufAlgo::over(result, input, result);

        input.copy(result);
    }
    
    result.write(output_path);
}

void denoise(std::string noised_path, std::string output_path)
{
    oidn::DeviceRef device = oidn::newDevice();
    device.commit();

    // read image bixels
    OIIO::ImageBuf input_buf(noised_path);
    OIIO::ImageSpec input_spec(input_buf.spec());

    size_t channels = input_spec.nchannels;
    size_t width = input_spec.width;
    size_t height = input_spec.height;

    // for denoise use only 3 channels
    OIIO::ImageBuf input_rgb = OIIO::ImageBufAlgo::channels(input_buf, 3, {});
    oidn::BufferRef noised_buf = device.newBuffer(width * height * 3 * sizeof(float));
    oidn::BufferRef denoised_buf = device.newBuffer(width * height * 3 * sizeof(float));
    oidn::FilterRef filter = device.newFilter("RT");
    filter.setImage("color", noised_buf, oidn::Format::Float3, width, height);
    filter.setImage("output", denoised_buf, oidn::Format::Float3, width, height);

    filter.set("hdr", is_image_hdr(noised_path));
    float* noised_ptr = (float*)noised_buf.getData();
    
    OIIO::ROI full_roi = OIIO::ROI(0, width, 0, height);
    input_rgb.get_pixels(full_roi, OIIO::TypeDesc::FLOAT, noised_ptr);

    filter.commit();
    filter.execute();

    float* denoised_ptr = (float*)denoised_buf.getData();
    OIIO::ImageBuf output_rgb(OIIO::ImageSpec(width, height, 3));
    output_rgb.set_pixels(full_roi, OIIO::TypeDesc::FLOAT, denoised_ptr);

    // assume that input image has 3 or 4 channels
    if (channels == 3) {
        output_rgb.write(output_path);
    }
    else if (channels == 4) {
        // extract input alpha
        OIIO::ImageBuf alpha = OIIO::ImageBufAlgo::channels(input_buf, 1, 3);
        // combine with denoised rgb
        OIIO::ImageBuf combine = OIIO::ImageBufAlgo::channel_append(output_rgb, alpha);

        combine.write(output_path);
    }
}



std::vector<float> extract_spherical_harmonics(std::string image_path, size_t min_x, size_t min_y, size_t width, size_t height, float gamma)
{
    OIIO::ImageBuf input_img(image_path);
    OIIO::ImageSpec input_spec(input_img.spec());
    // extract subimage
    std::vector<float> extract_pixels(width * height * input_spec.nchannels);
    OIIO::ROI extract_roi = OIIO::ROI(min_x, min_x + width, min_y, min_y + height);
    input_img.get_pixels(extract_roi, OIIO::TypeDesc::FLOAT, extract_pixels.data());
    // read the image from top to bottom (and from left to right)

    return image_to_sh(extract_pixels, width, height, input_spec.nchannels, gamma);
}

void render_spherical_harmonics(std::vector<float> sh_coefficients, int width, int height, std::string image_path)
{
    std::vector<float> image_pixels = sh_to_image(sh_coefficients, width, height);
    OIIO::ImageBuf out_buf(OIIO::ImageSpec(width, height, 3, OIIO::TypeDesc::FLOAT));
    OIIO::ROI full_roi = OIIO::ROI(0, width, 0, height);
    out_buf.set_pixels(full_roi, OIIO::TypeDesc::FLOAT, image_pixels.data());
    out_buf.write(image_path);
}

PYBIND11_MODULE(OIIO_Py2Processor, m)
{
    m.def("combine_three_textures", &combine_three_textures);
    m.def("apply_gamma", &apply_gamma);
    m.def("add_padding", &add_padding);
    m.def("combine_add", &combine_add);
    m.def("replace_alpha", &replace_alpha);
    m.def("remove_alpha", &remove_alpha);
    m.def("denoise", &denoise);
    m.def("extract_spherical_harmonics", &extract_spherical_harmonics);
    m.def("render_spherical_harmonics", &render_spherical_harmonics);
}