## What it is

The repository contains scripts for preparing data from Softimage and next using inside [Playcanvas](https://playcanvas.com) game engine. These scripts can be used for:
* Baking navmesh and export it into file (text or binary)
* Combine meshes inside scene with the same material into one big mesh. Pack second uv by using [UV Packer for Softimage](https://ssoftadd.github.io/uvPackerPage.html)
* Bake lightmaps
* Create lightprobes and export data into json-file

## How to install

Scripts are written on pure Python, so, you need only clone the repository into workgroup. Also the repository contains sources for one binary module ```OIIO_Py2Processor.pyd```. This module contains the following methods:
* ```combine_three_textures``` It create the texture ```A + B - C```
* ```combine_add``` Simply create ```A + B```
* ```replace_alpha``` Assign alpha from one image to the other
* ```remove_alpha``` Simply remove alpha channel from the image
* ```apply_gamma``` apply gamma correction to the image
* ```add_padding``` Add padding to the texture. In most cases used for rendered lightmaps
* ```denoise``` Denoise the image by using [OIDN](https://www.openimagedenoise.org/)
* ```extract_spherical_harmonics``` Convert the piece of texture into 27 (```9 x 3```) coefficients, which encode the corresponding spherical harmonics
* ```render_spherical_harmonics``` Convert spherical harmonics coefficients into image

Module ```OIIO_Py2Processor.pyd``` required several external libraries (OpenImageIO, OpenImageDenoise and their dependencies). These libraries and corresponding headers can be download from release section. The folder structure should be as follows:
```
xsiToPlaycanvas/
├─ Application/
├─ Data/
├─ dst/
│  ├─ includes/
│  │  ├─ ...
│  ├─ libs/
│  │  ├─ .../
├─ src/

```