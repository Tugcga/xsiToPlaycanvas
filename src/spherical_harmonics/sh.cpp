#include <cmath>
#include <vector>

float x_to_phi(int x, int width)
{
    return 2.0 * M_PI * (x + 0.5) / width;
}

float y_to_theta(int y, int height) {
    return M_PI * (y + 0.5) / height;
}

size_t get_index(int l, int m)
{
    return l * (l + 1) + m;
}

void to_vector(float phi, float theta, float& x, float& y, float& z)
{
    float r = sin(theta);
    x = r * cos(phi);
    y = r * sin(phi);
    z = cos(theta);
}

float clamp(float val, float min, float max)
{
    if (val < min) { val = min; }
    if (val > max) { val = max; }
    return val;
}

void to_spherical(float x, float y, float z, float& phi, float& theta) {
    theta = acos(clamp(z, -1.0, 1.0));
    phi = atan2(y, x);
}

float hardcoded_sh_00(float x, float y, float z) {
    return 0.282095;
}

float hardcoded_sh_1n1(float x, float y, float z) {
    return -0.488603 * y;
}

float hardcoded_sh_10(float x, float, float z) {
    return 0.488603 * z;
}

float hardcoded_sh_1p1(float x, float y, float z) {
    return -0.488603 * x;
}

float hardcoded_sh_2n2(float x, float y, float z) {
    return 1.092548 * x * y;
}

float hardcoded_sh_2n1(float x, float y, float z) {
    return -1.092548 * y * z;
}

float hardcoded_sh_20(float x, float y, float z) {
    return 0.315392 * (-x * x - y * y + 2.0 * z * z);
}

float hardcoded_sh_2p1(float x, float y, float z) {
    return -1.092548 * x * z;
}

float hardcoded_sh_2p2(float x, float y, float z) {
    return 0.546274 * (x * x - y * y);
}

float eval_sh(int l, int m, float x, float y, float z)
{
    switch (l) {
    case 0:
        return hardcoded_sh_00(x, y, z);
    case 1:
        switch (m) {
        case -1:
            return hardcoded_sh_1n1(x, y, z);
        case 0:
            return hardcoded_sh_10(x, y, z);
        case 1:
            return hardcoded_sh_1p1(x, y, z);
        }
    case 2:
        switch (m) {
        case -2:
            return hardcoded_sh_2n2(x, y, z);
        case -1:
            return hardcoded_sh_2n1(x, y, z);
        case 0:
            return hardcoded_sh_20(x, y, z);
        case 1:
            return hardcoded_sh_2p1(x, y, z);
        case 2:
            return hardcoded_sh_2p2(x, y, z);
        }
    }
    return 0.0;
}

float eval_sh(int l, int m, float phi, float theta)
{
    float x, y, z;
    to_vector(phi, theta, x, y, z);
    return eval_sh(l, m, x, y, z);
}

std::vector<float> image_to_sh(const std::vector<float>& image_pixels, size_t width, size_t height, size_t channels, float gamma)
{
    std::vector<float> to_return(3 * 9);

    float pixel_area = (2.0 * M_PI / width) * (M_PI / height);
    float gamma_inv = 1.0f / gamma;

    // iterate throw pixels
    for (size_t y = 0; y < height; y++)
    {
        float theta = y_to_theta(y, height);
        float weight = pixel_area * sin(theta);

        for (size_t x = 0; x < width; x++)
        {
            float phi = x_to_phi(x, width);

            // get pixels
            float r = pow(image_pixels[channels * (y * width + x)], gamma_inv);
            float g = pow(image_pixels[channels * (y * width + x) + 1], gamma_inv);
            float b = pow(image_pixels[channels * (y * width + x) + 2], gamma_inv);

            for (int l = 0; l <= 2; l++)
            {
                for (int m = -l; m <= l; m++)
                {
                    size_t i = get_index(l, m);
                    float sh = eval_sh(l, m, phi, theta);

                    // update the i-th coefficient
                    to_return[3 * i] += sh * weight * r;
                    to_return[3 * i + 1] += sh * weight * g;
                    to_return[3 * i + 2] += sh * weight * b;
                }
            }
        }
    }

    return to_return;
}

float eval_sh_sum(const std::vector<float>& sh_coefficients, int channel, float x, float y, float z) {
    float sum = 0.0f;
    for (int l = 0; l <= 2; l++)
    {
        for (int m = -l; m <= l; m++)
        {
            sum += eval_sh(l, m, x, y, z) * sh_coefficients[get_index(l, m) * 3 + channel];
        }
    }
    return sum;
}

std::vector<float> sh_to_image(const std::vector<float>& sh_coefficients, int width, int height)
{
    std::vector<float> to_return(width * height * 3);  // return 3-channel image

    for (size_t y = 0; y < height; y++)
    {
        float theta = y_to_theta(y, height);
        for (size_t x = 0; x < width; x++)
        {
            float phi = x_to_phi(x, width);
            float dir_x, dir_y, dir_z;
            to_vector(phi, theta, dir_x, dir_y, dir_z);

            to_return[3 * (width * y + x)] = eval_sh_sum(sh_coefficients, 0, dir_x, dir_y, dir_z);
            to_return[3 * (width * y + x) + 1] = eval_sh_sum(sh_coefficients, 1, dir_x, dir_y, dir_z);
            to_return[3 * (width * y + x) + 2] = eval_sh_sum(sh_coefficients, 2, dir_x, dir_y, dir_z);
        }
    }

    return to_return;
}