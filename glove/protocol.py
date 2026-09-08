"""Version 1 typed UART frames (64-byte legacy/control, 128-byte 22ch samples); fields match USER/glove_protocol.h."""
import binascii
import struct

SIZE = 64
SAMPLE, REQUEST, RESPONSE, SAMPLE22 = 1, 2, 3, 4


def pack(kind, payload):
    capacity=122 if kind==SAMPLE22 else 58
    if len(payload) > capacity:
        raise ValueError('Payload exceeds frame capacity')
    body = bytes([1, kind]) + payload.ljust(capacity, b'\0')
    return b'\xaa\x55' + body + struct.pack('<H', binascii.crc_hqx(body, 0xffff))


def request(session, number):
    return pack(REQUEST, struct.pack('<II', session, number))


def decode(frame):
    kind = frame[3]
    uid = frame[4:16].hex()
    if kind in (SAMPLE,SAMPLE22):
        channels=22 if kind==SAMPLE22 else 6
        session, seq, start, end = struct.unpack_from('<4I', frame, 16)
        offsets = struct.unpack_from('<%dH'%channels, frame, 32)
        values = struct.unpack_from('<%dH'%channels, frame, 32+2*channels)
        missed, dropped, rx_errors = struct.unpack_from('<3H', frame, 32+4*channels)
        return dict(kind='sample', uid=uid, session=session, sequence=seq,
                    start_us=start, end_us=end, channel_offsets_us=offsets, values=values,
                    channels=channels, channel_names=[f'HZ{i}' for i in range(6)]+([f'H{i}' for i in range(16)] if channels==22 else []),
                    missed_ticks=missed, tx_drops=dropped, rx_errors=rx_errors)
    if kind == RESPONSE:
        session, number, t2, t3 = struct.unpack_from('<4I', frame, 16)
        return dict(kind='sync', uid=uid, session=session, request=number, t2_us=t2, t3_us=t3)
    raise ValueError('Not a device-to-host packet')


class Parser:
    def __init__(self):
        self.buffer = bytearray()
        self.bad_frames = 0
        self.discarded_bytes = 0

    def feed(self, chunk):
        self.buffer.extend(chunk)
        output = []
        while len(self.buffer) >= 2:
            pos = self.buffer.find(b'\xaa\x55')
            if pos < 0:
                keep = 1 if self.buffer[-1] == 0xaa else 0
                self.discarded_bytes += len(self.buffer)-keep
                self.buffer[:] = self.buffer[-1:] if keep else b''
                break
            if pos:
                self.discarded_bytes += pos; del self.buffer[:pos]
            if len(self.buffer)<4: break
            if self.buffer[2]!=1 or self.buffer[3] not in (SAMPLE,RESPONSE,SAMPLE22):
                self.bad_frames+=1; self.discarded_bytes+=1; del self.buffer[0]; continue
            size=128 if self.buffer[3]==SAMPLE22 else 64
            if len(self.buffer) < size:
                break
            frame = bytes(self.buffer[:size])
            if (frame[2] != 1 or frame[3] not in (SAMPLE, RESPONSE, SAMPLE22)
                    or binascii.crc_hqx(frame[2:size-2], 0xffff) != struct.unpack_from('<H', frame, size-2)[0]):
                self.bad_frames += 1; self.discarded_bytes += 1; del self.buffer[0]
                continue
            output.append(decode(frame)); del self.buffer[:size]
        return output


class Unwrap:
    """Extend 32-bit microseconds; permits slightly reordered timestamps."""
    def __init__(self):
        self.latest = None

    def extend(self, value):
        if self.latest is None:
            self.latest = value
            return value
        delta = (value - (self.latest & 0xffffffff) + (1 << 31)) % (1 << 32) - (1 << 31)
        result = self.latest + delta
        self.latest = max(self.latest, result)
        return result
