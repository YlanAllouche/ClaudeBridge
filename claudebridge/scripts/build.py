#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def main():
    from claudebridge.scripts.download_deps import main as download_main

    subprocess.run(
        [
            "tailwindcss",
            "-i",
            "styles/input.css",
            "-o",
            "claudebridge/static/styles.css",
            "--minify",
        ]
    )

    result = download_main()
    if result != 0:
        print("Failed to download dependencies")
        return 1

    try:
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel"],
            check=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        print("==> Build complete! Wheel available in dist/")
        return 0
    except subprocess.CalledProcessError:
        print("Build failed to compile")
        return 1


if __name__ == "__main__":
    sys.exit(main())
