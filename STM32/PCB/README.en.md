[中文](README.md) | [English](README.en.md)

# Electrical design and manufacturing files

The schematic PDF defines nets/pins;PCB PDF previews layout;BOM XLSX lists parts;Gerber ZIP is for fabrication;Altium ZIP contains editable design sources. Verify revision consistency before manufacturing; photographs are not wiring instructions.

|Inputs|Mux|MCU ADC|Address lines|
|---|---|---|---|
|HZ0–5|U10|PA0|PA1/PA2/PA3|
|H0–7|U6|PB0|PA5/PA6/PA7|
|H8–15|U7|PB1|Shared withU6|

Select address→wait for settling→ADC→packet. U10 common-node capacitor is100nF;U6/U7 use10nF,with24k pulldowns on added channels. Source impedance/capacitance can bias high-speed readings. Voltage,power polarity and net details must follow the schematic. ST-Link SWD programming and USART1 data are different interfaces. Retouched[photos](../../doc/pictrue/enhanced/) are illustrative only.
