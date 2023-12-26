#pragma once
#include <vector>

// calculate spherical harmonic coefficients for order = 2 (9 coefficients)
// return one vector with 9 coeffcicients for each channel rgb
// group per coefficient (first three value for the first coefficient, next three values for the second and so on)
std::vector<float> image_to_sh(const std::vector<float>& image_pixels, size_t width, size_t height, size_t channels, bool apply_srgb);

// render input coefficients of the sphecrical haromonics to image pixels
// length of the sh_coefficients should be 27 = 9 coefficients (order 0, 1, 2) x 3 channels (r, g, b)
std::vector<float> sh_to_image(const std::vector<float>& sh_coefficients, int width, int height);