#ifndef GLOVE_PROTOCOL_H
#define GLOVE_PROTOCOL_H
#include <stdint.h>
/* Little-endian: AA55, version, type, payload, CRC16.
 * Types 1/2/3: 64 bytes; type 4 (22ch): 128 bytes.
 * CRC-CCITT-FALSE: init FFFF, poly 1021, covers bytes 2..size-3. */
static uint16_t glove_crc(const uint8_t *p, unsigned n) {
    uint16_t crc = 0xffffu;
    /* Nibble lookup: identical wire CRC, less work in UART/DMA IRQs. */
    static const uint16_t table[16] = {
        0x0000,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,
        0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef
    };
    while (n--) {
        crc ^= (uint16_t)(*p++) << 8;
        crc = (uint16_t)((crc << 4) ^ table[crc >> 12]);
        crc = (uint16_t)((crc << 4) ^ table[crc >> 12]);
    }
    return crc;
}
static void put16(uint8_t *p, uint16_t n) { p[0]=(uint8_t)n; p[1]=(uint8_t)(n>>8); }
static void put32(uint8_t *p, uint32_t n) { put16(p,(uint16_t)n); put16(p+2,(uint16_t)(n>>16)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1]<<8) | ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24); }
static void seal_frame_size(uint8_t *p, uint8_t type, unsigned size) {
    p[0]=0xaa; p[1]=0x55; p[2]=1; p[3]=type; put16(p+size-2,glove_crc(p+2,size-4));
}
static void seal_frame(uint8_t *p, uint8_t type) { seal_frame_size(p,type,64); }
#endif
