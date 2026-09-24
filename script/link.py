from datetime import datetime
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

# Ensure repo root is on sys.path for direct script execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from script.config import GLOBAL_HOST_ROOTS, get_backup_root
from script.common import get_repo_root, Color


def is_skill_directory(p: Path) -> bool:
    return p.is_dir() and (p / "SKILL.md").is_file()


def is_link(p: Path) -> bool:
    try:
        if p.is_symlink():
            return True
        if sys.platform == "win32":
            return bool(p.lstat().st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except (OSError, ValueError):
        return False
    return False


def remove_link_or_dir(p: Path) -> None:
    if is_link(p):
        if sys.platform == "win32":
            try:
                os.rmdir(p)
                return
            except OSError:
                pass
            try:
                p.unlink()
                return
            except OSError:
                pass
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                p.unlink()
            except OSError:
                shutil.rmtree(p, ignore_errors=True)
    elif p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()


def create_link(target: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or is_link(link_path):
        remove_link_or_dir(link_path)

    if sys.platform == "win32":
        # Create NTFS Directory Junction without requiring Administrator rights
        try:
            import _winapi  # type: ignore

            _winapi.CreateJunction(str(target), str(link_path))
            return
        except Exception:
            pass

        cmd = ["cmd", "/c", "mklink", "/J", str(link_path), str(target)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            # Fallback to os.symlink
            os.symlink(str(target), str(link_path), target_is_directory=True)
    else:
        os.symlink(str(target), str(link_path), target_is_directory=True)


def save_existing_directory(dir_path: Path, root_name: str, backup_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_backup_dir = backup_root / timestamp
    target_backup_dir.mkdir(parents=True, exist_ok=True)
    destination = target_backup_dir / f"{root_name}--{dir_path.name}"
    counter = 1
    while destination.exists():
        destination = target_backup_dir / f"{root_name}--{dir_path.name}-{counter}"
        counter += 1
    shutil.move(str(dir_path), str(destination))
    print(Color.gray(f"  backup: {dir_path} -> {destination}"))
    return destination


def link_skills(repo_root: Path, backup_root: Path, dry_run: bool = False) -> int:
    managed_skills: dict[str, Path] = {}
    for entry in repo_root.iterdir():
        if is_skill_directory(entry):
            managed_skills[entry.name] = entry

    print(Color.bold(f"Central skill repository: {repo_root}"))
    print(Color.bold(f"Existing managed skills: {len(managed_skills)}"))

    # 1. Absorb unmanaged skills from global roots into repo
    for root_name, host_path in GLOBAL_HOST_ROOTS:
        if not host_path.is_dir():
            continue

        try:
            if host_path.resolve() == repo_root.resolve():
                continue
        except Exception:
            pass

        print(f"\nScanning {root_name}: {host_path}")
        for entry in list(host_path.iterdir()):
            if root_name == "codex" and entry.name in {".system", "codex-primary-runtime"}:
                print(Color.gray(f"  keep runtime directory: {entry.name}"))
                continue

            if not is_skill_directory(entry):
                print(Color.gray(f"  keep unmanaged directory: {entry.name}"))
                continue

            try:
                if entry.resolve().is_relative_to(repo_root.resolve()):
                    continue
            except Exception:
                pass

            if entry.name in managed_skills:
                continue

            dest = repo_root / entry.name
            if not dry_run:
                if is_link(entry):
                    shutil.copytree(entry, dest)
                    print(Color.green(f"  import linked skill: {entry.name}"))
                else:
                    shutil.move(str(entry), str(dest))
                    print(Color.green(f"  import skill: {entry.name}"))
            managed_skills[entry.name] = dest

    # 2. Expose every managed skill in each global store
    for root_name, host_path in GLOBAL_HOST_ROOTS:
        try:
            if host_path.exists() and host_path.resolve() == repo_root.resolve():
                print(Color.green(f"\n{root_name} ({host_path}) is already directly linked to repository root."))
                continue
        except Exception:
            pass

        if not dry_run:
            host_path.mkdir(parents=True, exist_ok=True)
        print(f"\nLinking skills into {root_name} ({host_path})")

        for skill_name, skill_path in sorted(managed_skills.items()):
            link_target = host_path / skill_name
            if link_target.exists() or is_link(link_target):
                try:
                    if link_target.resolve() == skill_path.resolve():
                        continue
                except Exception:
                    pass

                if is_link(link_target):
                    if not dry_run:
                        remove_link_or_dir(link_target)
                elif not is_skill_directory(link_target):
                    print(Color.yellow(f"  WARN: Cannot link '{link_target}': non-skill directory exists."))
                    continue
                else:
                    if not dry_run:
                        save_existing_directory(link_target, root_name, backup_root)

            if not dry_run:
                create_link(skill_path, link_target)
            print(f"  • Linked {skill_name}")


    print(Color.green(f"\n✨ Done. Global skill stores now reference: {repo_root}"))
    print(Color.gray(f"Backups (when replacements were needed): {backup_root}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Link central repository skills into global host directories.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate linking operations without altering filesystem.")
    args = parser.parse_args(argv)

    root = get_repo_root()
    backup = get_backup_root()
    return link_skills(root, backup, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
