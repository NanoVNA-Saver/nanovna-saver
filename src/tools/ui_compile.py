import glob
import subprocess
from pathlib import Path


def main() -> None:
    print("Generation python classes for ui files...")
    for p in glob.glob("./src/**/*.ui", recursive=True):
        handle_ui(Path(p))

    print("Generation resource files...")
    for p in glob.glob("./src/**/*.qrc", recursive=True):
        handle_qrc(Path(p))


def handle_ui(ui_file: Path) -> None:
    dir = ui_file.parent
    ui_file_name = ui_file.name
    python_name = f'{ui_file_name.replace(".ui", "")}.py'

    cmd = [
        "pyside6-uic",
        str(ui_file),
        "-o",
        str(dir / python_name),
        "--from-imports",
    ]
    print(f'{" ".join(cmd)}')
    subprocess.run(cmd, check=True)


def handle_qrc(qrc_file: Path) -> None:
    dir = qrc_file.parent
    ui_file_name = qrc_file.name
    python_name = f'{ui_file_name.replace(".qrc", "")}_rc.py'

    cmd = ["pyside6-rcc", str(qrc_file), "-o", str(dir / python_name)]
    print(f'{" ".join(cmd)}')
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
