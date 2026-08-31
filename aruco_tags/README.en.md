[中文](README.md) | [English](README.en.md)

# Prism tags

Use the two A4 SVG sheets in[printable](printable/README.en.md); top-level PNGs are historical and include inactive IDs. Hand1 uses0–5,hand2 uses6–11,DICT_4X4_250. Black square48mm,cut guide60mm. Print at actual size, measure and cut along the guide while retaining white margins.

Center one tag on each outer side. All top edges point to the same rim. Looking from that rim, IDs advance clockwise for face_direction=1; see[diagram](../doc/diagrams/marker_placement.svg). Do not duplicate IDs, independently rotate or mirror tags. Test a stationary prism one visible face at a time for consistent pose.

```bash
/usr/bin/python3 -B -m tools.generate_aruco_tags --output /tmp/prism_tags_new
```

Run from the root. Changes to config.yaml dictionary/groups/physical size require regenerating and measuring prints. Use a new output directory. Camera calibration uses a different board in calibration.
