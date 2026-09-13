#!/usr/bin/env python3
"""
Pure-Python HWP 5.0 Compound Document Splitter with MiniFAT support and BinData pruning.
Splits large HWP documents into independent, valid HWP part files (<50MB).
Zero third-party dependencies (standard library only).
"""

from __future__ import annotations
import sys
import os
import struct
import zlib
import io
import re
import argparse
from pathlib import Path

# Static 1x1 white image byte literals (zero third-party dependencies)
DUMMY_BMP_1X1 = (
    b"BM\x3a\x00\x00\x00\x00\x00\x00\x00\x36\x00\x00\x00\x28\x00\x00\x00"
    b"\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00"
    b"\x04\x00\x00\x00\x13\x0b\x00\x00\x13\x0b\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\xff\xff\xff\x00"
)

DUMMY_JPG_1X1 = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08"
    b"\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e"
    b"\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


class CFBFParser:
    """
    Parser for Compound File Binary Format (CFBF / OLE2).
    Supports FAT, DIFAT, Directory hierarchy, regular streams, and MiniFAT/MiniStream.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.fp = open(filepath, "rb")
        hdr = self.fp.read(512)
        if len(hdr) < 512 or hdr[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise ValueError(f"{filepath} is not a valid OLE2 compound document")

        self.sec_size = 1 << struct.unpack("<H", hdr[30:32])[0]
        self.short_sec_size = 1 << struct.unpack("<H", hdr[32:34])[0]
        self.num_fat_secs = struct.unpack("<I", hdr[44:48])[0]
        self.first_dir_sec = struct.unpack("<I", hdr[48:52])[0]
        self.min_cutoff = struct.unpack("<I", hdr[56:60])[0]
        self.first_minifat_sec = struct.unpack("<I", hdr[60:64])[0]
        self.num_minifat_secs = struct.unpack("<I", hdr[64:68])[0]
        self.first_difat_sec = struct.unpack("<I", hdr[68:72])[0]
        self.num_difat_secs = struct.unpack("<I", hdr[72:76])[0]

        # Read DIFAT
        difat_sectors = [struct.unpack("<I", hdr[76 + i * 4:80 + i * 4])[0] for i in range(109)]
        cur_difat = self.first_difat_sec
        for _ in range(self.num_difat_secs):
            if cur_difat in (0xFFFFFFFE, 0xFFFFFFFF):
                break
            self.fp.seek((cur_difat + 1) * self.sec_size)
            difat_block = self.fp.read(self.sec_size)
            num_entries = (self.sec_size // 4) - 1
            difat_sectors.extend(struct.unpack(f"<{num_entries}I", difat_block[:num_entries * 4]))
            cur_difat = struct.unpack("<I", difat_block[-4:])[0]

        # Read FAT
        self.fat = []
        for sec in difat_sectors:
            if sec in (0xFFFFFFFE, 0xFFFFFFFF):
                continue
            self.fp.seek((sec + 1) * self.sec_size)
            self.fat.extend(struct.unpack(f"<{self.sec_size // 4}I", self.fp.read(self.sec_size)))

        # Read MiniFAT
        self.minifat = []
        cur_minifat = self.first_minifat_sec
        while cur_minifat not in (0xFFFFFFFE, 0xFFFFFFFF) and cur_minifat < len(self.fat):
            self.fp.seek((cur_minifat + 1) * self.sec_size)
            self.minifat.extend(struct.unpack(f"<{self.sec_size // 4}I", self.fp.read(self.sec_size)))
            cur_minifat = self.fat[cur_minifat]

        # Read Directory entries
        dir_data = bytearray()
        cur_sec = self.first_dir_sec
        while cur_sec not in (0xFFFFFFFE, 0xFFFFFFFF) and cur_sec < len(self.fat):
            self.fp.seek((cur_sec + 1) * self.sec_size)
            dir_data.extend(self.fp.read(self.sec_size))
            cur_sec = self.fat[cur_sec]

        self.entries = []
        for i in range(0, len(dir_data), 128):
            chunk = dir_data[i:i + 128]
            if len(chunk) < 128:
                break
            name_len = struct.unpack("<H", chunk[64:66])[0]
            if name_len == 0:
                continue
            name = chunk[:name_len].decode("utf-16le", errors="ignore").rstrip("\x00")
            etype = chunk[66]
            left = struct.unpack("<I", chunk[68:72])[0]
            right = struct.unpack("<I", chunk[72:76])[0]
            child = struct.unpack("<I", chunk[76:80])[0]
            start_sec = struct.unpack("<I", chunk[116:120])[0]
            size = struct.unpack("<Q", chunk[120:128])[0]
            self.entries.append({
                "id": len(self.entries),
                "name": name,
                "type": etype,
                "left": left,
                "right": right,
                "child": child,
                "start_sec": start_sec,
                "size": size
            })

        root_entry = self.entries[0] if self.entries else None
        if root_entry:
            self.ministream = self._read_regular_stream(root_entry["start_sec"], root_entry["size"])
        else:
            self.ministream = b""

        # Build parent mapping by traversing tree from root
        self.parent_map = {}
        def traverse(entry_id, parent_name):
            if entry_id in (0xFFFFFFFE, 0xFFFFFFFF) or entry_id >= len(self.entries):
                return
            entry = self.entries[entry_id]
            if parent_name is not None:
                self.parent_map[entry["name"]] = parent_name
            traverse(entry["left"], parent_name)
            traverse(entry["right"], parent_name)
            if entry["type"] in (1, 5):
                traverse(entry["child"], entry["name"])
        traverse(0, None)

    def close(self):
        if self.fp and not self.fp.closed:
            self.fp.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def _read_regular_stream(self, start_sec: int, size: int) -> bytes:
        if size == 0 or start_sec in (0xFFFFFFFE, 0xFFFFFFFF):
            return b""
        data = bytearray()
        c_sec = start_sec
        rem = size
        while c_sec not in (0xFFFFFFFE, 0xFFFFFFFF) and rem > 0 and c_sec < len(self.fat):
            self.fp.seek((c_sec + 1) * self.sec_size)
            to_r = min(rem, self.sec_size)
            data.extend(self.fp.read(to_r))
            rem -= to_r
            c_sec = self.fat[c_sec]
        return bytes(data)

    def _read_mini_stream(self, start_sec: int, size: int) -> bytes:
        if size == 0 or start_sec in (0xFFFFFFFE, 0xFFFFFFFF):
            return b""
        data = bytearray()
        c_sec = start_sec
        rem = size
        while c_sec not in (0xFFFFFFFE, 0xFFFFFFFF) and rem > 0 and c_sec < len(self.minifat):
            offset = c_sec * self.short_sec_size
            to_r = min(rem, self.short_sec_size)
            data.extend(self.ministream[offset:offset + to_r])
            rem -= to_r
            c_sec = self.minifat[c_sec]
        return bytes(data)

    def get_stream_data(self, entry: dict) -> bytes:
        if entry["type"] == 5:
            return self.ministream
        if entry["size"] < self.min_cutoff and self.first_minifat_sec not in (0xFFFFFFFE, 0xFFFFFFFF) and len(self.ministream) > 0:
            return self._read_mini_stream(entry["start_sec"], entry["size"])
        else:
            return self._read_regular_stream(entry["start_sec"], entry["size"])


def parse_hwp_paragraphs(sec0_bytes: bytes) -> list[list[tuple[int, int, bytes]]]:
    """
    Parse Section0 binary stream into list of paragraphs.
    Each paragraph is a list of record tuples: (tag_id, level, data).
    Top-level paragraphs start with tag 66 (HWPTAG_PARA_HEADER) and level 0.
    """
    pos = 0
    records = []
    while pos + 4 <= len(sec0_bytes):
        hdr = struct.unpack("<I", sec0_bytes[pos:pos + 4])[0]
        pos += 4
        tag_id = hdr & 0x3FF
        level = (hdr >> 10) & 0x3FF
        size = (hdr >> 20) & 0xFFF
        if size == 0xFFF:
            if pos + 4 > len(sec0_bytes):
                break
            size = struct.unpack("<I", sec0_bytes[pos:pos + 4])[0]
            pos += 4
        data = sec0_bytes[pos:pos + size]
        pos += size
        records.append((tag_id, level, data))

    paragraphs = []
    cur_para = []
    for tag_id, level, data in records:
        if tag_id == 66 and level == 0 and cur_para:
            paragraphs.append(cur_para)
            cur_para = [(tag_id, level, data)]
        else:
            cur_para.append((tag_id, level, data))
    if cur_para:
        paragraphs.append(cur_para)
    return paragraphs


def rebuild_section0(paragraphs: list[list[tuple[int, int, bytes]]]) -> bytes:
    """
    Serialize paragraph records back into packed HWP 5.0 Section binary format.
    """
    sec_bytes = bytearray()
    for p in paragraphs:
        for tag_id, level, data in p:
            sz = len(data)
            if sz < 0xFFF:
                hdr = (tag_id & 0x3FF) | ((level & 0x3FF) << 10) | ((sz & 0xFFF) << 20)
                sec_bytes.extend(struct.pack("<I", hdr))
            else:
                hdr = (tag_id & 0x3FF) | ((level & 0x3FF) << 10) | (0xFFF << 20)
                sec_bytes.extend(struct.pack("<II", hdr, sz))
            sec_bytes.extend(data)
    return bytes(sec_bytes)


def extract_referenced_bins(paragraphs: list[list[tuple[int, int, bytes]]]) -> set[int]:
    """
    Scan for HWPTAG_SHAPE_COMPONENT_PICTURE (tag 85) records and extract 16-bit BinData item IDs.
    """
    bin_ids = set()
    for p in paragraphs:
        for tag_id, level, data in p:
            if tag_id == 85 and len(data) >= 72:
                for offset in (70, 71):
                    if len(data) >= offset + 2:
                        b_le = struct.unpack("<H", data[offset:offset + 2])[0]
                        b_be = struct.unpack(">H", data[offset:offset + 2])[0]
                        for b in (b_le, b_be):
                            if 0 < b <= 65535:
                                bin_ids.add(b)
    return bin_ids


def ole_cmp_key(name: str):
    return (len(name), [ord(c.upper()) for c in name])


def build_bst(indices: list[int], entries: list[dict]) -> int:
    if not indices:
        return 0xFFFFFFFF
    sorted_indices = sorted(indices, key=lambda idx: ole_cmp_key(entries[idx]["name"]))

    def construct(sub: list[int]) -> int:
        if not sub:
            return 0xFFFFFFFF
        mid = len(sub) // 2
        root = sub[mid]
        entries[root]["left"] = construct(sub[:mid])
        entries[root]["right"] = construct(sub[mid + 1:])
        return root

    return construct(sorted_indices)


def rebuild_ole_directory_tree(entries: list[dict]):
    """
    Rebuild OLE directory tree pointers (left, right, child) as balanced BSTs
    according to MS-CFB specifications.
    """
    for e in entries:
        e["left"] = 0xFFFFFFFF
        e["right"] = 0xFFFFFFFF
        e["child"] = 0xFFFFFFFF

    for idx, s in enumerate(entries):
        if s["type"] in (1, 5):  # Storage or Root Entry
            s_name = s["name"]
            child_indices = [i for i, e in enumerate(entries) if e.get("parent_name") == s_name and i != idx]
            s["child"] = build_bst(child_indices, entries)


def write_hwp_ole(entries: list[dict], output_path: str):
    """
    Reconstruct a valid OLE2 compound document with proper DIFAT/FAT/MiniFAT/Directory layout.
    Stores streams <4096 bytes into MiniStream and large streams into regular sectors.
    """
    sec_size = 512
    mini_sec_size = 64
    mini_cutoff = 4096

    # 1. Process mini streams (size < 4096, excluding storages and Root Entry)
    mini_stream_bytes = bytearray()
    minifat = []

    for e in entries:
        if e["type"] in (1, 5):  # Storage or Root
            e["size"] = 0
            e["is_mini"] = False
            e["start_sec"] = 0 if e["type"] == 1 else 0xFFFFFFFE
            continue

        d = e.get("data", b"")
        sz = len(d)
        e["size"] = sz
        if 0 < sz < mini_cutoff:
            e["is_mini"] = True
            e["start_sec"] = len(minifat)
            pad = (mini_sec_size - (sz % mini_sec_size)) % mini_sec_size
            padded = d + b"\x00" * pad
            mini_stream_bytes.extend(padded)
            num_mini_secs = len(padded) // mini_sec_size
            start_m = e["start_sec"]
            for i in range(num_mini_secs - 1):
                minifat.append(start_m + i + 1)
            minifat.append(0xFFFFFFFE)  # ENDOFCHAIN
        else:
            e["is_mini"] = False
            e["start_sec"] = 0xFFFFFFFE

    # 2. Regular streams (size >= 4096)
    regular_stream_bytes = bytearray()
    new_fat = []
    cur_sec = 0

    for e in entries:
        if e["type"] in (1, 5):
            continue
        if not e["is_mini"] and e["size"] >= mini_cutoff:
            e["start_sec"] = cur_sec
            d = e["data"]
            pad = (sec_size - (len(d) % sec_size)) % sec_size
            padded = d + b"\x00" * pad
            regular_stream_bytes.extend(padded)
            num_secs = len(padded) // sec_size
            for i in range(num_secs - 1):
                new_fat.append(cur_sec + i + 1)
            new_fat.append(0xFFFFFFFE)
            cur_sec += num_secs

    # 3. Write MiniStream into regular sectors as Root Entry's data
    root_entry = entries[0]
    root_entry["size"] = len(mini_stream_bytes)
    if len(mini_stream_bytes) > 0:
        root_entry["start_sec"] = cur_sec
        pad = (sec_size - (len(mini_stream_bytes) % sec_size)) % sec_size
        padded = bytes(mini_stream_bytes) + b"\x00" * pad
        regular_stream_bytes.extend(padded)
        num_secs = len(padded) // sec_size
        for i in range(num_secs - 1):
            new_fat.append(cur_sec + i + 1)
        new_fat.append(0xFFFFFFFE)
        cur_sec += num_secs
    else:
        root_entry["start_sec"] = 0xFFFFFFFE

    # 4. Write MiniFAT sectors into regular stream
    if len(minifat) > 0:
        first_minifat_sec = cur_sec
        minifat_bytes = bytearray()
        for m_val in minifat:
            minifat_bytes.extend(struct.pack("<I", m_val))
        pad = (sec_size - (len(minifat_bytes) % sec_size)) % sec_size
        minifat_bytes.extend(b"\xFF" * pad)
        regular_stream_bytes.extend(minifat_bytes)
        num_minifat_secs = len(minifat_bytes) // sec_size
        for i in range(num_minifat_secs - 1):
            new_fat.append(cur_sec + i + 1)
        new_fat.append(0xFFFFFFFE)
        cur_sec += num_minifat_secs
    else:
        first_minifat_sec = 0xFFFFFFFE
        num_minifat_secs = 0

    # 5. Rebuild directory tree
    rebuild_ole_directory_tree(entries)

    dir_bytes = bytearray()
    for e in entries:
        entry_chunk = bytearray(128)
        encoded_name = e["name"].encode("utf-16le") + b"\x00\x00"
        name_len = len(encoded_name)
        entry_chunk[:name_len] = encoded_name
        struct.pack_into("<H", entry_chunk, 64, name_len)
        entry_chunk[66] = e["type"]
        entry_chunk[67] = 1  # Black node
        struct.pack_into("<I", entry_chunk, 68, e.get("left", 0xFFFFFFFF))
        struct.pack_into("<I", entry_chunk, 72, e.get("right", 0xFFFFFFFF))
        struct.pack_into("<I", entry_chunk, 76, e.get("child", 0xFFFFFFFF))
        struct.pack_into("<I", entry_chunk, 116, e["start_sec"])
        struct.pack_into("<Q", entry_chunk, 120, e["size"])
        dir_bytes.extend(entry_chunk)

    pad = (sec_size - (len(dir_bytes) % sec_size)) % sec_size
    dir_bytes.extend(b"\x00" * pad)
    num_dir_secs = len(dir_bytes) // sec_size
    first_dir_sec = cur_sec
    for i in range(num_dir_secs - 1):
        new_fat.append(cur_sec + i + 1)
    new_fat.append(0xFFFFFFFE)
    cur_sec += num_dir_secs

    # 6. Calculate FAT & DIFAT sector counts
    num_fat_secs = (len(new_fat) + (sec_size // 4) - 1) // (sec_size // 4)
    while True:
        difat_extra_needed = max(0, num_fat_secs - 109)
        num_difat_secs = (difat_extra_needed + (sec_size // 4 - 2)) // (sec_size // 4 - 1) if difat_extra_needed > 0 else 0
        total_meta_secs = num_fat_secs + num_difat_secs
        req_fat_len = len(new_fat) + total_meta_secs
        new_num_fat = (req_fat_len + (sec_size // 4) - 1) // (sec_size // 4)
        if new_num_fat == num_fat_secs:
            break
        num_fat_secs = new_num_fat

    first_fat_sec = cur_sec
    first_difat_sec = cur_sec + num_fat_secs if num_difat_secs > 0 else 0xFFFFFFFE

    for _ in range(num_fat_secs):
        new_fat.append(0xFFFFFFFD)  # FAT sector marker
    for _ in range(num_difat_secs):
        new_fat.append(0xFFFFFFFC)  # DIFAT sector marker

    all_difat = [first_fat_sec + i for i in range(num_fat_secs)]

    # 7. Build Header
    hdr = bytearray(512)
    hdr[:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    struct.pack_into("<H", hdr, 24, 0x003E)
    struct.pack_into("<H", hdr, 26, 0x0003)
    struct.pack_into("<H", hdr, 28, 0xFFFE)
    struct.pack_into("<H", hdr, 30, 9)  # Sector shift = 9 (512 bytes)
    struct.pack_into("<H", hdr, 32, 6)  # Mini sector shift = 6 (64 bytes)
    struct.pack_into("<I", hdr, 44, num_fat_secs)
    struct.pack_into("<I", hdr, 48, first_dir_sec)
    struct.pack_into("<I", hdr, 56, mini_cutoff)
    struct.pack_into("<I", hdr, 60, first_minifat_sec)
    struct.pack_into("<I", hdr, 64, num_minifat_secs)
    struct.pack_into("<I", hdr, 68, first_difat_sec)
    struct.pack_into("<I", hdr, 72, num_difat_secs)

    for i in range(109):
        val = all_difat[i] if i < len(all_difat) else 0xFFFFFFFF
        struct.pack_into("<I", hdr, 76 + i * 4, val)

    difat_bytes = bytearray()
    if num_difat_secs > 0:
        difat_idx = 109
        for s_idx in range(num_difat_secs):
            sec_buf = bytearray(sec_size)
            for e_idx in range((sec_size // 4) - 1):
                val = all_difat[difat_idx] if difat_idx < len(all_difat) else 0xFFFFFFFF
                struct.pack_into("<I", sec_buf, e_idx * 4, val)
                difat_idx += 1
            next_sec = (first_difat_sec + s_idx + 1) if s_idx + 1 < num_difat_secs else 0xFFFFFFFE
            struct.pack_into("<I", sec_buf, sec_size - 4, next_sec)
            difat_bytes.extend(sec_buf)

    fat_bytes = bytearray()
    for f_val in new_fat:
        fat_bytes.extend(struct.pack("<I", f_val))
    pad = (num_fat_secs * sec_size) - len(fat_bytes)
    fat_bytes.extend(b"\xFF" * pad)

    with open(output_path, "wb") as out_f:
        out_f.write(hdr)
        out_f.write(regular_stream_bytes)
        out_f.write(dir_bytes)
        out_f.write(fat_bytes)
        out_f.write(difat_bytes)


def create_dummy_images() -> tuple[bytes, bytes]:
    """
    Return static 1x1 white dummy images: (real_jpg, real_bmp).
    Zero third-party dependencies (no PIL).
    """
    return DUMMY_JPG_1X1, DUMMY_BMP_1X1


def split_hwp_file(input_hwp: str, output_prefix: str | None = None, max_part_mb: float = 38.0) -> list[str]:
    """
    Split a large HWP file into standalone valid HWP part files (<50MB each),
    preserving document header metadata, styles, and controls while partitioning
    image payloads with valid lightweight dummy placeholders.
    """
    abs_input = os.path.abspath(input_hwp)
    if output_prefix is None:
        p = Path(abs_input)
        output_prefix = str(p.parent / p.stem)

    real_jpg, real_bmp = create_dummy_images()

    with CFBFParser(abs_input) as cfbf:
        all_stream_data = {e["name"]: cfbf.get_stream_data(e) for e in cfbf.entries if e["type"] == 2}
        bin_entries = [e for e in cfbf.entries if e["name"].startswith("BIN")]

        # Partition bin items into chunks where each chunk has <= max_part_mb
        parts = []
        cur_part = []
        cur_size = 0.0
        for e in bin_entries:
            sz = e["size"] / (1024 * 1024)
            if cur_size + sz > max_part_mb and cur_part:
                parts.append(cur_part)
                cur_part = [e["name"]]
                cur_size = sz
            else:
                cur_part.append(e["name"])
                cur_size += sz
        if cur_part:
            parts.append(cur_part)

        out_files = []
        for part_idx, active_bins in enumerate(parts, 1):
            active_set = set(active_bins)
            part_entries = []
            for e in cfbf.entries:
                name = e["name"]
                if e["type"] == 2:
                    if name.startswith("BIN"):
                        if name in active_set:
                            data = all_stream_data[name]
                        else:
                            data = real_bmp if name.lower().endswith(".bmp") else real_jpg
                    else:
                        data = all_stream_data.get(name, b"")
                else:
                    data = b""

                entry_copy = {
                    "id": len(part_entries),
                    "name": name,
                    "type": e["type"],
                    "parent_name": cfbf.parent_map.get(name, "Root Entry"),
                    "data": data
                }
                part_entries.append(entry_copy)

            out_path = f"{output_prefix}_part{part_idx}.hwp"
            write_hwp_ole(part_entries, out_path)
            out_files.append(out_path)
            file_mb = os.path.getsize(out_path) / (1024 * 1024)
            print(f"  [+] Created: {os.path.basename(out_path)} ({file_mb:.2f} MB, {len(active_set)} active images)")

    return out_files


def main():
    parser = argparse.ArgumentParser(description="Split HWP 5.0 document into smaller standalone HWP files (<50MB)")
    parser.add_argument("input_hwp", help="Target HWP file to split")
    parser.add_argument("--out-prefix", "-o", default=None, help="Output prefix path")
    parser.add_argument("--max-size", "-s", type=float, default=38.0, help="Max image chunk size in MB (default: 38.0)")
    args = parser.parse_args()

    files = split_hwp_file(args.input_hwp, output_prefix=args.out_prefix, max_part_mb=args.max_size)
    print(f"Successfully split into {len(files)} files.")


if __name__ == "__main__":
    main()
