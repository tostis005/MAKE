import struct

class _Image:
    def __init__(self, source):
        if hasattr(source, "read"):
            pos = source.tell() if hasattr(source, "tell") else None
            data = source.read(32)
            if pos is not None and hasattr(source, "seek"):
                source.seek(pos)
        else:
            with open(source, "rb") as fh:
                data = fh.read(32)
        if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            raise ValueError("Unsupported image; expected PNG")
        self.size = struct.unpack(">II", data[16:24])
        self.format = "PNG"
    def load(self):
        return self
    def verify(self):
        return None
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False

def open(source):
    return _Image(source)
