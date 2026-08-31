"""Check output memory bounds and required interrupt vector bindings."""
import argparse
from pathlib import Path
import struct
import subprocess


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--prefix',default='arm-none-eabi-')
    p.add_argument('elf',type=Path)
    p.add_argument('binary',type=Path)
    args=p.parse_args()
    header=args.elf.read_bytes()[:24]
    if header[:6]!=b'\x7fELF\x01\x01' or struct.unpack_from('<H',header,18)[0]!=40:
        raise SystemExit('Not a 32-bit little-endian ARM ELF')
    raw=args.binary.read_bytes()
    if not 256<=len(raw)<=64*1024:raise SystemExit('Invalid flash image size')
    symbols={}
    result=subprocess.check_output([args.prefix+'nm','--defined-only',str(args.elf)],text=True)
    for line in result.splitlines():
        fields=line.split()
        if len(fields)==3:
            symbols[fields[2]]=(int(fields[0],16),fields[1])
    if struct.unpack_from('<I',raw,0)[0]!=0x20005000:
        raise SystemExit('Initial stack pointer does not match STM32F103C8 SRAM')
    for name,index in [('Reset_Handler',1),('TIM2_IRQHandler',44),('TIM3_IRQHandler',45),
                       ('USART1_IRQHandler',53),('DMA1_Channel4_IRQHandler',30)]:
        address,kind=symbols[name]
        actual=struct.unpack_from('<I',raw,4*index)[0]
        if actual!=(address|1):raise SystemExit(f'Wrong vector for {name}')
        if name!='Reset_Handler' and kind.upper()!='T':raise SystemExit(f'{name} resolved to weak/default handler')
    if symbols['_ebss'][0]>0x20004000:raise SystemExit('Less than 4KiB stack headroom')
    print('Firmware check passed: ARM ELF, 64KiB/20KiB layout, stack and four acquisition IRQ vectors.')


if __name__=='__main__':main()
