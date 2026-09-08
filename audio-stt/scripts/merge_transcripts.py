#!/usr/bin/env python3
"""
Merge segmented STT markdown files into a master transcript with calculated continuous timestamps.
"""

import argparse
import os
import re
import sys


def merge_transcripts(target_dir: str, prefix: str = "", segment_seconds: int = 600) -> str:
    target_dir = os.path.abspath(target_dir)
    pattern = re.compile(rf"^{re.escape(prefix)}.*part(\d+)\.md$" if prefix else r"^.*part(\d+)\.md$")
    timestamp_pattern = re.compile(r"^(\d{1,2}):(\d{2})$")

    part_files = []
    for f in os.listdir(target_dir):
        m = pattern.match(f)
        if m:
            part_files.append((int(m.group(1)), f))

    if not part_files:
        print(f"Error: No matching part markdown files found in {target_dir}", file=sys.stderr)
        return ""

    part_files.sort(key=lambda x: x[0])
    output_name = f"{prefix}_full.md" if prefix else "transcript_full.md"
    output_path = os.path.join(target_dir, output_name)

    full_content = [
        f"# {prefix or os.path.basename(target_dir)} 전체 오디오 전사본\n\n",
        f"- **총 세그먼트**: {len(part_files)}개 파트 (각 약 {segment_seconds // 60}분)\n",
        f"- **파트 목록**: " + ", ".join([f[1] for f in part_files]) + "\n\n---\n\n"
    ]

    for part_num, p_file in part_files:
        offset_seconds = (part_num - 1) * segment_seconds
        part_path = os.path.join(target_dir, p_file)
        start_min = (part_num - 1) * (segment_seconds // 60)
        full_content.append(f"## Part {part_num:02d} ({start_min:02d}:00 ~ )\n\n")

        with open(part_path, "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                match = timestamp_pattern.match(line_clean)
                if match:
                    mm, ss = int(match.group(1)), int(match.group(2))
                    total_sec = offset_seconds + mm * 60 + ss
                    new_mm = total_sec // 60
                    new_ss = total_sec % 60
                    full_content.append(f"{new_mm:02d}:{new_ss:02d}\n")
                else:
                    full_content.append(line)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(full_content)

    print(f"Successfully generated: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Merge segmented STT markdown files into a master transcript.")
    parser.add_argument("--dir", required=True, help="Directory containing part markdown files")
    parser.add_argument("--prefix", default="", help="Prefix of the files (e.g. recording name)")
    parser.add_argument("--segment-seconds", type=int, default=600, help="Duration of each segment in seconds (default: 600)")
    args = parser.parse_args()

    out = merge_transcripts(args.dir, args.prefix, args.segment_seconds)
    if not out:
        sys.exit(1)


if __name__ == "__main__":
    main()
