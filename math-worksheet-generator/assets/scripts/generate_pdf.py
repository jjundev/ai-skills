#!/usr/bin/env python3
"""
generate_pdf.py - Headless Google Chrome 기반 수학 II 문제지, 정답표 및 해설지 PDF 자동 빌더

Usage:
    python3 generate_pdf.py part1               # Part 1 문제지 PDF 생성
    python3 generate_pdf.py part1 --with-answers # Part 1 정답표 포함 PDF 생성
    python3 generate_pdf.py part1 --solution    # Part 1 해설지 PDF 생성
    python3 generate_pdf.py part2               # Part 2 문제지 PDF 생성
    python3 generate_pdf.py part2 --with-answers # Part 2 정답표 포함 PDF 생성
    python3 generate_pdf.py part2 --solution    # Part 2 해설지 PDF 생성
    python3 generate_pdf.py solution            # Part 1, Part 2 해설지 PDF 2종 생성
    python3 generate_pdf.py all                 # Part 1, Part 2 문제지 및 해설지 PDF 4종 일괄 생성
    python3 generate_pdf.py all --with-answers  # Part 1, Part 2 정답표 포함 PDF 2종 생성
    python3 generate_pdf.py all --no-answers    # Part 1, Part 2 문제지 PDF 2종 생성
    python3 generate_pdf.py all --solution      # Part 1, Part 2 해설지 PDF 2종 생성
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]

PARTS_CONFIG = {
    1: {
        "part_key": "1",
        "title": "Part 1 (함수의 극한과 연속)",
        "without_answers_filename": "서영이_수학II_Part1_함수의극한과연속.pdf",
        "with_answers_filename": "서영이_수학II_Part1_함수의극한과연속_정답포함.pdf",
        "solution_filename": "서영이_수학II_Part1_함수의극한과연속_해설지.pdf",
    },
    2: {
        "part_key": "2",
        "title": "Part 2 (미분계수와 도함수)",
        "without_answers_filename": "서영이_수학II_Part2_미분계수와도함수.pdf",
        "with_answers_filename": "서영이_수학II_Part2_미분계수와도함수_정답포함.pdf",
        "solution_filename": "서영이_수학II_Part2_미분계수와도함수_해설지.pdf",
    },
}


def get_chrome_path():
    """Google Chrome 실행 파일 경로 탐색 (macOS 기본 경로, PATH, 환경변수)"""
    env_path = os.environ.get("CHROME_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path

    for binary in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
        found = shutil.which(binary)
        if found:
            return found

    raise FileNotFoundError(
        "Google Chrome 실행 파일을 찾을 수 없습니다.\n"
        "macOS 표준 경로(/Applications/Google Chrome.app/Contents/MacOS/Google Chrome)를 확인하거나 "
        "CHROME_PATH 환경 변수를 설정해 주세요."
    )


def get_pdf_page_count(pdf_path):
    """pdfinfo 유틸리티를 사용하여 PDF 총 페이지 수 조회"""
    try:
        res = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in res.stdout.splitlines():
            if line.startswith("Pages:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def format_bytes(size):
    """파일 크기를 사람이 읽기 쉬운 문자열로 변환"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def build_pdf(chrome_path, base_dir, part_num, with_answers, output_filename, is_solution=False):
    """지정된 Part 및 모드(문제지/정답표/해설지)에 따라 Headless Chrome으로 PDF 생성"""
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / output_filename

    html_path = (base_dir / "template" / "worksheet.html").resolve()
    query_parts = [f"part={part_num}"]
    if is_solution:
        query_parts.append("mode=solution")
    if with_answers:
        query_parts.append("answers=1")

    query = "?" + "&".join(query_parts)
    file_url = f"file://{html_path}{query}"

    cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=4000",
        f"--print-to-pdf={out_path}",
        file_url,
    ]

    if is_solution:
        tag = "해설지"
    elif with_answers:
        tag = "정답포함"
    else:
        tag = "문제지"

    print(f"📄 [Part {part_num} | {tag}] 빌드 시작 -> {output_filename} ...")

    try:
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ PDF 생성 실패: {e}", file=sys.stderr)
        if e.stderr:
            print(f"Chrome Stderr:\n{e.stderr}", file=sys.stderr)
        raise

    if not out_path.exists():
        raise RuntimeError(f"산출물 파일이 생성되지 않았습니다: {out_path}")

    file_size = out_path.stat().st_size
    pages = get_pdf_page_count(out_path)
    page_info = f"{pages} 쪽" if pages else "페이지 확인 불가"

    print(
        f"✅ [Part {part_num} | {tag}] 완료: {output_filename} "
        f"({format_bytes(file_size)}, {page_info})"
    )
    return {
        "part": part_num,
        "with_answers": with_answers,
        "is_solution": is_solution,
        "tag": tag,
        "filename": output_filename,
        "path": str(out_path),
        "size": file_size,
        "pages": pages,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Headless Google Chrome 기반 수학 II 문제지, 정답표 및 해설지 PDF 자동 빌더",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""예시:
  python3 generate_pdf.py part1                # Part 1 문제지 PDF 생성
  python3 generate_pdf.py part1 --with-answers  # Part 1 정답표 포함 PDF 생성
  python3 generate_pdf.py part1 --solution     # Part 1 해설지 PDF 생성
  python3 generate_pdf.py part2                # Part 2 문제지 PDF 생성
  python3 generate_pdf.py part2 --with-answers  # Part 2 정답표 포함 PDF 생성
  python3 generate_pdf.py part2 --solution     # Part 2 해설지 PDF 생성
  python3 generate_pdf.py solution             # Part 1, Part 2 해설지 PDF 2종 생성
  python3 generate_pdf.py all                  # Part 1, Part 2 문제지, 정답포함, 해설지 PDF 6종 일괄 생성
  python3 generate_pdf.py all --with-answers   # Part 1, Part 2 정답표 포함 PDF 2종 생성
  python3 generate_pdf.py all --no-answers     # Part 1, Part 2 문제지 PDF 2종 생성
  python3 generate_pdf.py all --solution       # Part 1, Part 2 해설지 PDF 2종 생성
""",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["part1", "part2", "solution", "solutions", "all", "1", "2"],
        help="생성할 대상: part1, part2, solution, all (기본값: all)",
    )

    ans_group = parser.add_mutually_exclusive_group()
    ans_group.add_argument(
        "--with-answers",
        action="store_true",
        help="맨 뒤에 빠른 정답표를 부록으로 포함하여 생성",
    )
    ans_group.add_argument(
        "--no-answers",
        action="store_true",
        help="정답표 없이 순수 문제지만 생성",
    )
    ans_group.add_argument(
        "--solution",
        action="store_true",
        help="풀이 및 빠른 정답표가 포함된 해설지 PDF 생성",
    )

    args = parser.parse_args()

    try:
        chrome_path = get_chrome_path()
    except FileNotFoundError as err:
        print(f"❌ 오류: {err}", file=sys.stderr)
        sys.exit(1)

    base_dir = Path(__file__).resolve().parent
    print(f"🚀 Google Chrome 경로: {chrome_path}")
    print(f"📂 작업 디렉토리: {base_dir}")

    # 작업 목록 구성: (part_num, with_answers, is_solution, filename)
    tasks = []

    if args.target in ("solution", "solutions"):
        for part_num in [1, 2]:
            cfg = PARTS_CONFIG[part_num]
            tasks.append((part_num, True, True, cfg["solution_filename"]))
    elif args.target in ("part1", "1"):
        cfg = PARTS_CONFIG[1]
        if args.solution:
            tasks.append((1, True, True, cfg["solution_filename"]))
        elif args.with_answers:
            tasks.append((1, True, False, cfg["with_answers_filename"]))
        else:
            tasks.append((1, False, False, cfg["without_answers_filename"]))
    elif args.target in ("part2", "2"):
        cfg = PARTS_CONFIG[2]
        if args.solution:
            tasks.append((2, True, True, cfg["solution_filename"]))
        elif args.with_answers:
            tasks.append((2, True, False, cfg["with_answers_filename"]))
        else:
            tasks.append((2, False, False, cfg["without_answers_filename"]))
    else:  # all
        for part_num in [1, 2]:
            cfg = PARTS_CONFIG[part_num]
            if args.solution:
                tasks.append((part_num, True, True, cfg["solution_filename"]))
            elif args.with_answers:
                tasks.append((part_num, True, False, cfg["with_answers_filename"]))
            elif args.no_answers:
                tasks.append((part_num, False, False, cfg["without_answers_filename"]))
            else:
                # 'all' 기본 모드: 문제지 2종 + 해설지 2종 (총 4종) 일괄 생성
                tasks.append((part_num, False, False, cfg["without_answers_filename"]))
                tasks.append((part_num, True, True, cfg["solution_filename"]))

    print(f"총 {len(tasks)}개 PDF 빌드 예정\n" + "-" * 50)

    results = []
    for part_num, with_answers, is_solution, filename in tasks:
        res = build_pdf(
            chrome_path,
            base_dir,
            part_num,
            with_answers,
            filename,
            is_solution=is_solution,
        )
        results.append(res)

    print("-" * 50)
    print("🎉 모든 PDF 빌드가 성공적으로 완료되었습니다!")
    print("\n[생성된 산출물 요약]")
    for r in results:
        print(
            f" - {r['filename']:<44} | Part {r['part']} ({r['tag']}) | "
            f"{r['pages'] or '?'}쪽 | {format_bytes(r['size'])}"
        )


if __name__ == "__main__":
    main()
