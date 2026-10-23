"""Bound central-directory allocation before Python's eager ZipFile constructor."""
import struct


def check_directory(source, max_entries, max_metadata):
    source.seek(0, 2)
    size = source.tell()
    source.seek(max(0, size-65557))
    tail = source.read(65557)
    offset = tail.rfind(b'PK\x05\x06')
    if offset < 0 or len(tail)-offset < 22:
        raise ValueError('Missing ZIP directory')
    if offset >= 20 and tail[offset-20:offset-16] == b'PK\x06\x07':
        raise ValueError('ZIP64 workbook directory is unsupported')
    _, disk, directory_disk, disk_entries, entries, metadata, start, comment = struct.unpack_from('<4s4H2LH', tail, offset)
    if (offset+22+comment != len(tail) or disk or directory_disk or disk_entries != entries or
            entries == 65535 or metadata == 0xffffffff or start == 0xffffffff or
            entries > max_entries or metadata > max_metadata or start+metadata != size-len(tail)+offset):
        raise ValueError('Oversized, multipart or ZIP64 workbook directory is unsupported')
    source.seek(0)
