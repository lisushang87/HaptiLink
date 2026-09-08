[中文](README.md) | [English](README.en.md)

# Binary glove data and clock mapping

protocol.py validates frames/CRC/sequence/UID/ADC/timestamps;clock.py fits board-to-host time;record.py logs and optionally publishes ROS;report.py summarizes rate/loss/timing;align.py aligns channels;compare.py compares ADC runs.

```bash
/usr/bin/python3 -B -m glove.record --port /dev/ttyUSB0 --hand left --baud 921600 --duration 60 --output /tmp/glove_new.jsonl
/usr/bin/python3 -B -m glove.report /tmp/glove_new.jsonl
```

Run from the root. Each hand uses a separate port,label,new file. For ROS,source Humble and add --ros;topics are /glove/left/sample and timing,or right equivalents. The episode recorder does not open serial ports itself.

Wait for valid synchronization before episodes. Check gaps,missed_ticks,tx_drops,rx_errors,CRC and clock age. ADC is not joint angle;RTT/2/residuals are not absolute error measurements. See[capture and alignment](../collection/README.en.md) and[capture](../collection/CAPTURE.en.md).
