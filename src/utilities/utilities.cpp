#include <string>
#include <algorithm>

bool is_image_hdr(const std::string& path) {
    size_t point_pos = path.rfind('.');
    if (point_pos == std::string::npos) {
        return false;
    }

    std::string ext = path.substr(point_pos + 1);
    std::transform(ext.begin(), ext.end(), ext.begin(),
        [](unsigned char c) { return std::tolower(c); });

    if (ext == "exr" || ext == "hdr") {
        return true;
    }

    return false;
}

float linear_to_srgb(float v) {
	if (v <= 0.0f) {
		return 0.0;
	}
	if (v >= 1.0f) {
		return v;
	}
	if (v <= 0.0031308f) {
		return  12.92f * v;
	}

	return (1.055f * pow(v, 1.0f / 2.4f)) - 0.055f;
}