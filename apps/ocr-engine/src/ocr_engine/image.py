"""Minimal image loading helpers for OCR experiments.

The first implementation intentionally avoids hard runtime dependencies on
external imaging packages so the OCR skeleton can be verified in a clean
environment. PNG and portable graymap images are supported.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
import zlib


@dataclass(slots=True)
class LoadedImage:
    """Decoded image payload used by preprocessing and detection."""

    grayscale: list[list[int]]
    width: int
    height: int
    mode: str
    metadata: dict[str, object]


def crop_grayscale(grayscale: list[list[int]], bbox: list[list[int]]) -> list[list[int]]:
    """Extract one grayscale crop from a page."""
    if len(bbox) != 2 or len(bbox[0]) != 2 or len(bbox[1]) != 2:
        raise ValueError("Bounding box must be [[x1, y1], [x2, y2]].")
    if not grayscale or not grayscale[0]:
        return []
    x1, y1 = bbox[0]
    x2, y2 = bbox[1]
    max_height = len(grayscale)
    max_width = len(grayscale[0])
    left = max(0, min(x1, max_width - 1))
    top = max(0, min(y1, max_height - 1))
    right = max(left, min(x2, max_width - 1))
    bottom = max(top, min(y2, max_height - 1))
    return [row[left:right + 1] for row in grayscale[top:bottom + 1]]


def write_pgm(path: Path, grayscale: list[list[int]]) -> None:
    """Write a grayscale matrix to a binary PGM file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not grayscale or not grayscale[0]:
        width = 1
        height = 1
        payload = bytes([255])
    else:
        height = len(grayscale)
        width = len(grayscale[0])
        payload = bytes(
            max(0, min(255, int(pixel)))
            for row in grayscale
            for pixel in row
        )
    header = f"P5\n{width} {height}\n255\n".encode("ascii")
    path.write_bytes(header + payload)


def write_png(path: Path, grayscale: list[list[int]]) -> None:
    """Write a grayscale matrix to an 8-bit non-interlaced PNG file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not grayscale or not grayscale[0]:
        width = 1
        height = 1
        rows = [bytes([255])]
    else:
        height = len(grayscale)
        width = len(grayscale[0])
        rows = [
            bytes(max(0, min(255, int(pixel))) for pixel in row[:width])
            for row in grayscale[:height]
        ]

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    raw_scanlines = b"".join(b"\x00" + row for row in rows)
    idat = zlib.compress(raw_scanlines)
    png_bytes = (
        signature
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(png_bytes)


def load_image(path: Path) -> LoadedImage:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return _load_png(path)
    if suffix in {".pgm", ".pnm"}:
        return _load_pgm(path)
    raise ValueError(f"Unsupported image format: {path.suffix}")


def _load_pgm(path: Path) -> LoadedImage:
    data = path.read_bytes()
    tokens: list[bytes] = []
    index = 0

    def next_token() -> bytes:
        nonlocal index
        while index < len(data):
            byte = data[index:index + 1]
            if byte == b"#":
                while index < len(data) and data[index:index + 1] not in {b"\n", b"\r"}:
                    index += 1
            elif byte.isspace():
                index += 1
            else:
                start = index
                while index < len(data) and not data[index:index + 1].isspace():
                    index += 1
                return data[start:index]
        raise ValueError("Unexpected end of PGM header.")

    magic = next_token()
    if magic != b"P5":
        raise ValueError("Only binary PGM (P5) is supported in the baseline loader.")
    width = int(next_token())
    height = int(next_token())
    max_value = int(next_token())
    if max_value > 255:
        raise ValueError("Only 8-bit PGM images are supported.")

    while index < len(data) and data[index:index + 1].isspace():
        index += 1
    raw = data[index:index + width * height]
    if len(raw) != width * height:
        raise ValueError("PGM pixel data is truncated.")
    grayscale = [list(raw[row_start:row_start + width]) for row_start in range(0, len(raw), width)]
    return LoadedImage(
        grayscale=grayscale,
        width=width,
        height=height,
        mode="L",
        metadata={
            "format": "PGM",
            "max_value": max_value,
        },
    )


def _load_png(path: Path) -> LoadedImage:
    data = path.read_bytes()
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        raise ValueError("Invalid PNG signature.")

    index = len(signature)
    width = height = None
    bit_depth = None
    color_type = None
    idat_chunks: list[bytes] = []

    while index < len(data):
        if index + 8 > len(data):
            break
        length = struct.unpack(">I", data[index:index + 4])[0]
        index += 4
        chunk_type = data[index:index + 4]
        index += 4
        chunk_data = data[index:index + length]
        index += length
        index += 4  # skip CRC

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("Only standard non-interlaced PNGs are supported.")
            if bit_depth != 8:
                raise ValueError("Only 8-bit PNG images are supported.")
        elif chunk_type == b"IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None or bit_depth is None or color_type is None:
        raise ValueError("PNG missing IHDR chunk.")

    decompressed = zlib.decompress(b"".join(idat_chunks))
    channels = {0: 1, 2: 3, 6: 4}.get(color_type)
    if channels is None:
        raise ValueError(f"Unsupported PNG color type: {color_type}")

    bytes_per_pixel = channels
    row_stride = width * bytes_per_pixel
    expected = height * (1 + row_stride)
    if len(decompressed) < expected:
        raise ValueError("PNG pixel data is truncated.")

    rows = []
    cursor = 0
    prev_row = bytes([0] * row_stride)
    for _ in range(height):
        filter_type = decompressed[cursor]
        cursor += 1
        row = bytearray(decompressed[cursor:cursor + row_stride])
        cursor += row_stride
        recon = _unfilter_png_row(filter_type, row, prev_row, bytes_per_pixel)
        rows.append(recon)
        prev_row = recon

    grayscale_rows: list[list[int]] = []
    for row in rows:
        if channels == 1:
            grayscale_rows.append(list(row))
            continue
        gray_row: list[int] = []
        for offset in range(0, len(row), channels):
            r = row[offset]
            g = row[offset + 1]
            b = row[offset + 2]
            gray_value = int(round(0.299 * r + 0.587 * g + 0.114 * b))
            gray_row.append(max(0, min(255, gray_value)))
        grayscale_rows.append(gray_row)

    grayscale = grayscale_rows
    return LoadedImage(
        grayscale=grayscale,
        width=width,
        height=height,
        mode="L",
        metadata={
            "format": "PNG",
            "bit_depth": bit_depth,
            "color_type": color_type,
        },
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def _unfilter_png_row(
    filter_type: int,
    row: bytearray,
    prev_row: bytes,
    bytes_per_pixel: int,
) -> bytes:
    if filter_type == 0:
        return bytes(row)

    result = bytearray(len(row))

    def left_value(index: int) -> int:
        return result[index - bytes_per_pixel] if index >= bytes_per_pixel else 0

    def up_value(index: int) -> int:
        return prev_row[index] if index < len(prev_row) else 0

    def up_left_value(index: int) -> int:
        return prev_row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0

    if filter_type == 1:
        for index, value in enumerate(row):
            result[index] = (value + left_value(index)) & 0xFF
    elif filter_type == 2:
        for index, value in enumerate(row):
            result[index] = (value + up_value(index)) & 0xFF
    elif filter_type == 3:
        for index, value in enumerate(row):
            result[index] = (value + ((left_value(index) + up_value(index)) // 2)) & 0xFF
    elif filter_type == 4:
        for index, value in enumerate(row):
            a = left_value(index)
            b = up_value(index)
            c = up_left_value(index)
            p = a + b - c
            pa = abs(p - a)
            pb = abs(p - b)
            pc = abs(p - c)
            if pa <= pb and pa <= pc:
                predictor = a
            elif pb <= pc:
                predictor = b
            else:
                predictor = c
            result[index] = (value + predictor) & 0xFF
    else:
        raise ValueError(f"Unsupported PNG filter type: {filter_type}")

    return bytes(result)
