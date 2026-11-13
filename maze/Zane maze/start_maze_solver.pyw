from pathlib import Path
import subprocess
import sys

from Zane_maze import main


if __name__ == "__main__":
    app_directory = Path(__file__).resolve().parent
    virtualenv_python = app_directory / ".venv" / "Scripts" / "pythonw.exe"
    if virtualenv_python.is_file() and Path(sys.executable).resolve() != virtualenv_python.resolve():
        subprocess.Popen(
            [str(virtualenv_python), str(Path(__file__).resolve())],
            cwd=app_directory,
        )
    else:
        main()
