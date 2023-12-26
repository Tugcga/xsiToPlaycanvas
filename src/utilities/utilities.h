#pragma once
#include <string>

bool is_image_hdr(const std::string& path);
float linear_to_srgb(float v);