[中文](README.md) | [English](README.en.md)

# 3D-printed parts

This directory contains STL meshes, not printer-specific G-code.

|File|Raw STL bounding-box values|Role|
|---|---|---|
|hex-hand.stl|103.923×120×60.453|Hand prism|
|handBand.stl|18.216×23.9×60|Wrist mounting component|
|hex-hand-camera.stl|128×147.089×88.024|Camera mounting variant|
|hex-robot-arm.stl|12×10.392×6|Robot-side variant; check scale carefully|

STL has no units. Import into a slicer, verify units/orientation/supports, test-fit, print, measure outside faces, then generate/attach tags and verify poses. Do not normalize all models to the same size. Check actual hole/part fit and strength. Default geometry is60mm prism side/height and48mm black marker; update config.yaml when physical dimensions change. Editing an STL does not update tracking. See[root instructions](../README.en.md).
