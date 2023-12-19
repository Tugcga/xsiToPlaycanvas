#include <string>
#include <algorithm>

bool is_image_hdr(const std::string& path)
{
    size_t point_pos = path.rfind('.');
    if (point_pos == std::string::npos)
    {
        return false;
    }

    std::string ext = path.substr(point_pos + 1);
    std::transform(ext.begin(), ext.end(), ext.begin(),
        [](unsigned char c) { return std::tolower(c); });

    if (ext == "exr" || ext == "hdr")
    {
        return true;
    }

    return false;
}