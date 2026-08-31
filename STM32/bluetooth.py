"""Configure two serial Bluetooth modules from Ubuntu; no I/O on import."""
import argparse
from contextlib import ExitStack
from pathlib import Path
import re
import time
import serial
from serial.tools import list_ports


def send_at_command(ser, command, timeout=2):
    """Require an explicit OK; stop on ERROR/FAIL or missing response."""
    ser.reset_input_buffer()
    ser.write((command + '\r\n').encode('ascii'))
    deadline = time.monotonic() + timeout
    lines = []
    while time.monotonic() < deadline:
        line = ser.readline().decode('ascii', errors='replace').strip()
        if not line:
            continue
        lines.append(line)
        if line == 'OK':
            print(f'[{ser.port}] {command.split("=")[0]}: OK')
            return '\n'.join(lines)
        if line.startswith(('ERROR', 'FAIL')):
            raise RuntimeError(f'{ser.port}: {command.split("=")[0]} 返回错误，请检查模块型号和AT模式')
    raise TimeoutError(f'{ser.port}: {command.split("=")[0]} 未收到OK；检查接线、AT模式和AT波特率')


def configure(master, slave, password, factory_reset=False, data_baud=None):
    send_at_command(master, 'AT')
    send_at_command(slave, 'AT')
    if factory_reset:
        send_at_command(master, 'AT+ORGL')
        send_at_command(slave, 'AT+ORGL')
    if data_baud is not None:
        send_at_command(master, f'AT+UART={data_baud},0,0')
        send_at_command(slave, f'AT+UART={data_baud},0,0')
    send_at_command(slave, 'AT+ROLE=0')
    send_at_command(slave, f'AT+PSWD="{password}"')
    response = send_at_command(slave, 'AT+ADDR?')
    match = re.search(r'\+ADDR:\s*([0-9a-fA-F]{1,4}):([0-9a-fA-F]{1,2}):([0-9a-fA-F]{1,6})(?:\s|$)', response)
    if match is None:
        raise RuntimeError('无法解析从机地址，停止配置主机')
    address = ','.join(match.groups())
    send_at_command(master, 'AT+ROLE=1')
    send_at_command(master, f'AT+PSWD="{password}"')
    send_at_command(master, 'AT+CMODE=0')
    send_at_command(master, f'AT+BIND={address}')
    print('配置指令已确认。断电、退出EN/KEY AT模式后重新上电，再验证两模块实际连接。')
    print('数据模式UART='+str(data_baud)+'，8N1；请验证实际收发。' if data_baud else '未修改数据UART速率；请与固件匹配：六通道100Hz为115200，22通道或六通道1000Hz为921600；高速无线吞吐需单独验证。')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Ubuntu串口蓝牙主从配置（不是系统内置蓝牙配对）')
    parser.add_argument('--list', action='store_true', help='只列出串口，不打开设备或发送指令')
    parser.add_argument('--master', default='/dev/ttyUSB0', help='主机模块串口，可使用/dev/serial/by-id路径')
    parser.add_argument('--slave', default='/dev/ttyUSB1', help='从机模块串口')
    parser.add_argument('--baud', type=int, default=38400, help='AT模式波特率，默认38400；不是手套数据波特率')
    parser.add_argument('--data-baud', type=int, choices=[9600,19200,38400,57600,115200,230400,460800,921600], help='可选：设置两个模块的数据模式波特率，六通道100Hz使用115200，22通道使用921600（不保证无线吞吐）；AT波特率仍由--baud指定')
    parser.add_argument('--password', default='1234', help='模块配对密码，默认1234')
    parser.add_argument('--factory-reset', action='store_true', help='显式对两个模块执行AT+ORGL（清除原配置）')
    args = parser.parse_args(argv)
    if args.list:
        ports = sorted(list_ports.comports(), key=lambda p: p.device)
        for port in ports:
            print(f'{port.device}  {port.description}  serial={port.serial_number or "unknown"}')
        for path in sorted(Path('/dev/serial/by-id').glob('*')):
            print(f'{path} -> {path.resolve()}')
        if not ports:
            print('未发现串口；请连接USB转串口设备。')
        return 0
    if args.baud <= 0 or not re.fullmatch(r'[A-Za-z0-9]{1,16}', args.password):
        parser.error('波特率必须为正数；密码须为1～16位ASCII字母/数字（长度支持取决于模块）')
    if Path(args.master).resolve() == Path(args.slave).resolve():
        parser.error('主从模块不能使用同一个串口')
    for path in (args.master, args.slave):
        if not Path(path).exists():
            parser.error(f'串口不存在：{path}，请先执行 --list 并指定正确的主从端口')
    print(f'主机={args.master}，从机={args.slave}，AT波特率={args.baud}；USB编号不代表模块角色。')
    try:
        with ExitStack() as stack:
            master = stack.enter_context(serial.Serial(args.master, args.baud, timeout=.1, write_timeout=2, exclusive=True))
            slave = stack.enter_context(serial.Serial(args.slave, args.baud, timeout=.1, write_timeout=2, exclusive=True))
            configure(master, slave, args.password, args.factory_reset, args.data_baud)
    except (serial.SerialException, OSError, RuntimeError, TimeoutError) as error:
        print(f'配置未完成：{error}')
        print('如提示Permission denied，检查Ubuntu串口设备权限及dialout组；不要盲目使用sudo。')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
