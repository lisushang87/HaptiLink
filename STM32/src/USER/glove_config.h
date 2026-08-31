#ifndef GLOVE_CONFIG_H
#define GLOVE_CONFIG_H
/* Default: experimental 22 channels at 100Hz.
 * Units are microseconds unless stated otherwise. Validate analog settling on hardware.
 * Linux: build_linux.bash PROFILE=100; Keil: change default or define in project. */
#ifndef GLOVE_PROFILE_HZ
#define GLOVE_PROFILE_HZ      100
#endif
#ifndef GLOVE_CHANNELS
#define GLOVE_CHANNELS 22
#endif
/* Shorter ADC sampling is experimental: verify source impedance/settling. */
#ifndef GLOVE_ADC_FAST
#define GLOVE_ADC_FAST 0
#endif
#if GLOVE_ADC_FAST == 1
#if GLOVE_CHANNELS != 22
#error Fast ADC experiment supports 22 channels only
#endif
#define GLOVE_ADC_SAMPLE_TIME ADC_SampleTime_71Cycles5
#elif GLOVE_ADC_FAST == 0
#define GLOVE_ADC_SAMPLE_TIME ADC_SampleTime_239Cycles5
#else
#error GLOVE_ADC_FAST must be 0 or 1
#endif
#define GLOVE_SAMPLE_HZ       GLOVE_PROFILE_HZ
#if GLOVE_CHANNELS == 22
#define GLOVE_FRAME_BYTES 128u
#if GLOVE_PROFILE_HZ == 1000
#if !GLOVE_ADC_FAST
#error 22ch 1000Hz requires GLOVE_ADC_FAST=1
#endif
#define GLOVE_UART_BAUD 1500000u
#else
#define GLOVE_UART_BAUD 921600u
#endif
#define GLOVE_ADC_AVERAGES 2u
#define GLOVE_ADC_TIMEOUT_US 100u
#if GLOVE_PROFILE_HZ == 20
#define GLOVE_MUX_SETTLE_US 5000u
#elif GLOVE_PROFILE_HZ == 100
#define GLOVE_MUX_SETTLE_US 1000u
#elif GLOVE_PROFILE_HZ == 200
#define GLOVE_MUX_SETTLE_US 400u
#elif GLOVE_PROFILE_HZ == 400
#define GLOVE_MUX_SETTLE_US 100u
#elif GLOVE_PROFILE_HZ == 500 || GLOVE_PROFILE_HZ == 1000
#define GLOVE_MUX_SETTLE_US 20u
#else
#error 22 channels support experimental profiles 20, 100, 200, 400, 500, 1000
#endif
#elif GLOVE_CHANNELS == 6
#define GLOVE_FRAME_BYTES 64u
#if GLOVE_PROFILE_HZ == 1000
#define GLOVE_UART_BAUD       921600u
#define GLOVE_MUX_SETTLE_US   20u
#define GLOVE_ADC_AVERAGES    2u
#define GLOVE_ADC_TIMEOUT_US  100u
#elif GLOVE_PROFILE_HZ == 100
#define GLOVE_UART_BAUD       115200u
#define GLOVE_MUX_SETTLE_US   1000u
#define GLOVE_ADC_AVERAGES    8u
#define GLOVE_ADC_TIMEOUT_US  1000u
#else
#error Unsupported glove profile: choose 100 or 1000
#endif
#else
#error GLOVE_CHANNELS must be 6 or 22
#endif
#define GLOVE_PROTOCOL       1u
/* 8N1: ten wire bits per byte. Include default two sync replies per second. */
#if (GLOVE_SAMPLE_HZ + 2u) * GLOVE_FRAME_BYTES * 10u >= GLOVE_UART_BAUD
#error UART bandwidth insufficient for sample and sync frames
#endif
#endif
