#!/usr/bin/env python3
"""
Merge segmented STT markdown files into a master transcript with calculated continuous timestamps.
"""

import argparse
import os
import re
import sys


def merge_transcripts(
    target_dir: str,
    prefix: str = "",
    segment_seconds: int = 600,
    keep_parts: bool = False,
    output_file: str = "",
    timestamps: bool = False,
) -> str:
    target_dir = os.path.abspath(target_dir)
    pattern = re.compile(rf"^{re.escape(prefix)}.*part(\d+)\.md$" if prefix else r"^.*part(\d+)\.md$")
    timestamp_pattern = re.compile(r"^(\d{1,2}):(\d{2})$")

    part_files = []
    if not os.path.isdir(target_dir):
        print(f"Error: Target directory does not exist: {target_dir}", file=sys.stderr)
        return ""

    for f in os.listdir(target_dir):
        m = pattern.match(f)
        if m:
            part_files.append((int(m.group(1)), f))

    if not part_files:
        print(f"Error: No matching part markdown files found in {target_dir}", file=sys.stderr)
        return ""

    part_files.sort(key=lambda x: x[0])

    if output_file:
        if os.path.isabs(output_file):
            output_path = os.path.abspath(output_file)
        else:
            output_path = os.path.abspath(os.path.join(target_dir, output_file))
    elif prefix:
        output_path = os.path.join(target_dir, f"{prefix}.md")
    else:
        output_path = os.path.join(target_dir, "transcript.md")

    full_content = [
        f"# {prefix or os.path.basename(target_dir)} 전체 오디오 전사본\n\n",
    ]

    for part_num, p_file in part_files:
        offset_seconds = (part_num - 1) * segment_seconds
        part_path = os.path.join(target_dir, p_file)
        if timestamps:
            start_min = (part_num - 1) * (segment_seconds // 60)
            full_content.append(f"## Part {part_num:02d} ({start_min:02d}:00 ~ )\n\n")
        else:
            full_content.append(f"## Part {part_num:02d}\n\n")

        with open(part_path, "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                match = timestamp_pattern.match(line_clean)
                if match:
                    if timestamps:
                        mm, ss = int(match.group(1)), int(match.group(2))
                        total_sec = offset_seconds + mm * 60 + ss
                        new_mm = total_sec // 60
                        new_ss = total_sec % 60
                        full_content.append(f"{new_mm:02d}:{new_ss:02d}\n")
                    else:
                        # Strip timestamp line when timestamps is False
                        continue
                else:
                    full_content.append(line)

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        raw_text = "".join(full_content)
        cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
    except Exception as e:
        print(f"Error writing output file {output_path}: {e}", file=sys.stderr)
        return ""

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        print(f"Error: Output file {output_path} does not exist or is empty.", file=sys.stderr)
        return ""

    print(f"Successfully generated: {output_path}")

    if not keep_parts:
        media_pattern = re.compile(
            rf"^{re.escape(prefix)}.*(part.*|.*_temp)\.(mp3|mp4)$" if prefix else r"^.*(part.*|.*_temp)\.(mp3|mp4)$",
            re.IGNORECASE,
        )
        md_pattern = re.compile(
            rf"^{re.escape(prefix)}.*part.*\.md$" if prefix else r"^.*part.*\.md$",
            re.IGNORECASE,
        )

        files_to_remove = set()
        for _, p_file in part_files:
            files_to_remove.add(p_file)

        for fname in os.listdir(target_dir):
            if md_pattern.match(fname) or media_pattern.match(fname):
                files_to_remove.add(fname)

        output_abs = os.path.abspath(output_path)
        for fname in files_to_remove:
            fpath = os.path.join(target_dir, fname)
            if os.path.abspath(fpath) == output_abs:
                continue
            try:
                if os.path.isfile(fpath) or os.path.islink(fpath):
                    os.remove(fpath)
            except OSError as e:
                print(f"Warning: Failed to remove {fpath}: {e}", file=sys.stderr)

        print("Cleaned up intermediate part files (keep_parts=False).")
    else:
        print("Retained intermediate part files (keep_parts=True).")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Merge segmented STT markdown files into a master transcript.")
    parser.add_argument("--dir", required=True, help="Directory containing part markdown files")
    parser.add_argument("--prefix", default="", help="Prefix of the files (e.g. recording name)")
    parser.add_argument("--segment-seconds", type=int, default=600, help="Duration of each segment in seconds (default: 600)")
    parser.add_argument("--keep-parts", action="store_true", default=False, help="Keep intermediate part files (default: False, clean them up)")
    parser.add_argument("--output", default="", help="Custom output filename or path (default: <prefix>.md)")
    parser.add_argument(
        "--timestamps",
        "-t",
        action="store_true",
        default=False,
        help="Include continuous MM:SS timestamps in merged transcript (default: False)",
    )
    args = parser.parse_args()

    out = merge_transcripts(
        target_dir=args.dir,
        prefix=args.prefix,
        segment_seconds=args.segment_seconds,
        keep_parts=args.keep_parts,
        output_file=args.output,
        timestamps=args.timestamps,
    )
    if not out:
        sys.exit(1)


if __name__ == "__main__":
    main()
