import glob
import shutil
from pathlib import Path


def main() -> None:
    print("Removing 'dist' dir...")
    rm_dir("dist")

    print("Removing 'build' dir...")
    rm_dir("build")

    print("Removing '*.egg-info' dir...")
    for dir in glob.glob("./src/**/*.egg-info", recursive=True):
        rm_dir(dir)

    print("Removing '__pycache__' dirs...")
    for dir in glob.glob("./src/**/__pycache__", recursive=True):
        rm_dir(dir)
    for dir in glob.glob("./tests/**/__pycache__", recursive=True):
        rm_dir(dir)

    print("Removing log files...")
    for file in glob.glob("./**/*.log", recursive=True):
        rm_dir(file)


def rm_dir(dir_or_file: str | Path) -> None:
    if isinstance(dir_or_file, str):
        dir_or_file = Path(dir_or_file)
    if dir_or_file.is_file():
        dir_or_file.unlink()
    elif dir_or_file.is_dir():
        shutil.rmtree(dir_or_file)


if __name__ == "__main__":
    main()
