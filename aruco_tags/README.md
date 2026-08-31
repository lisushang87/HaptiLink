[中文](README.md) | [English](README.en.md)

# 六棱柱标签

[printable](printable/) 是当前配置生成的可打印文件，优先使用其中两张A4 SVG；顶层PNG是历史单码，不能直接按文件数量分配两只手。

第一组ID0–5，第二组ID6–11，字典DICT_4X4_250。每码黑色外边48mm，裁剪框60mm。A4实际大小打印，尺量后沿灰框裁剪，保留白边。

贴在每个外侧平面中心，所有码上边朝同一开口。顺序和观察方向见[贴码图](../doc/diagrams/marker_placement.svg)与[完整装配说明](../README.md#贴在哪里按什么顺序)。两手ID不能重复；不要单独旋转某个码。

在项目根目录重新生成：

```bash
/usr/bin/python3 -B -m tools.generate_aruco_tags --output /tmp/prism_tags_new
```

修改根目录config.yaml的字典、标签组或物理尺寸后重新生成，保持打印尺寸与配置一致。生成到新目录，不覆盖原始文件。这里不是相机内参标定板，标定使用calibration目录。
