#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
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

    # handles dynamic version
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"
    build_version = os.getenv("BUILD_VERSION")

    if build_version:
        original_content = pyproject_path.read_text()

        modified_content = original_content.replace(
            f'version = "', f'version = "{build_version}"', 1
        )
        import re

        modified_content = re.sub(
            r'version = "[^"]+"',
            f'version = "{build_version}"',
            original_content,
            count=1,
        )

        try:
            pyproject_path.write_text(modified_content)

            subprocess.run(
                [sys.executable, "-m", "build", "--wheel"],
                check=True,
                cwd=project_root,
            )
            print(
                f"==> Build complete! Wheel available in dist/ (version: {build_version})"
            )
            return 0
        except subprocess.CalledProcessError:
            print("Build failed to compile")
            return 1
        finally:
            # Restore original pyproject.toml
            pyproject_path.write_text(original_content)
    else:
        try:
            subprocess.run(
                [sys.executable, "-m", "build", "--wheel"],
                check=True,
                cwd=project_root,
            )
            print("==> Build complete! Wheel available in dist/")
            return 0
        except subprocess.CalledProcessError:
            print("Build failed to compile")
            return 1


if __name__ == "__main__":
    sys.exit(main())
