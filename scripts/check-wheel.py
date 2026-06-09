import argparse
import os
import shutil
import subprocess
import tempfile
import textwrap
import zipfile
from pathlib import Path


REQUIRED_WHEEL_FILES = [
    "saturn_notebook/assets/katex/katex.min.css",
    "saturn_notebook/assets/katex/katex.min.js",
    "saturn_notebook/assets/katex/auto-render.min.js",
    "saturn_notebook/assets/katex/copy-tex.min.js",
    "saturn_notebook/assets/katex/LICENSE",
    "saturn_notebook/assets/katex/NOTICE.md",
    "saturn_notebook/assets/katex/fonts/KaTeX_Main-Regular.woff2",
]


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def assert_wheel_contents(wheel):
    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
        dist_info = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        missing = [name for name in REQUIRED_WHEEL_FILES if name not in names]
        if missing:
            raise SystemExit(f"Wheel is missing required files: {', '.join(missing)}")
        if not dist_info:
            raise SystemExit("Wheel is missing entry_points.txt")
        entry_points = zf.read(dist_info[0]).decode("utf-8")
        if "saturn = saturn_notebook.__main__:main" not in entry_points:
            raise SystemExit("Wheel entry point does not define saturn console script")


def smoke_install_wheel(wheel):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        venv_dir = tmp_path / "venv"
        uv = shutil.which("uv")
        if uv is None:
            raise SystemExit("uv is required for wheel install smoke validation")
        run([uv, "venv", "--seed", str(venv_dir)])
        if os.name == "nt":
            python = venv_dir / "Scripts" / "python.exe"
            saturn = venv_dir / "Scripts" / "saturn.exe"
        else:
            python = venv_dir / "bin" / "python"
            saturn = venv_dir / "bin" / "saturn"

        run([uv, "pip", "install", "--python", str(python), str(wheel)])
        run([str(saturn), "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        run([str(saturn), "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        notebook = tmp_path / "smoke.py"
        output = tmp_path / "smoke.out.py"
        html = tmp_path / "smoke.html"
        notebook.write_text(
            textwrap.dedent(
                """
                #m> # Smoke
                #m>
                #m> Math: $x + 1$.

                print(41 + 1)
                """
            ).lstrip()
        )

        run([str(saturn), "show", str(notebook), "--html", str(html), "--standalone", "--katex"])
        run([str(saturn), "run", str(notebook), str(output), "--no-mpi"])

        if "renderMathInElement" not in html.read_text():
            raise SystemExit("Standalone KaTeX smoke HTML did not include math renderer")
        if "#o> 42" not in output.read_text():
            raise SystemExit("Wheel smoke run did not save expected output")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()

    assert_wheel_contents(args.wheel)
    smoke_install_wheel(args.wheel)


if __name__ == "__main__":
    main()
