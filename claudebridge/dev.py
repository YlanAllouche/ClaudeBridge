import os
import signal
import subprocess
import sys


def main():
    """Start Tailwind CSS watch and Flask dev server together."""
    print("=> Starting ClaudeBridge dev environment...")

    print("\nDownloading external dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "claudebridge.scripts.download_deps"],
        capture_output=False,
    )

    print("\nTailwind CSS: watching styles/input.css")
    print("=> Flask: running on http://localhost:8000")
    print("\nPress Ctrl+C to stop both services\n")

    tailwind_proc = subprocess.Popen(
        [
            "tailwindcss",
            "-i",
            "styles/input.css",
            "-o",
            "claudebridge/static/styles.css",
            "--watch",
        ]
    )

    try:
        subprocess.run([sys.executable, "-m", "claudebridge"])
    except KeyboardInterrupt:
        print("\n\n Shutting down...")
    finally:
        tailwind_proc.terminate()
        tailwind_proc.wait()
        print(" Dev environment stopped")


if __name__ == "__main__":
    main()
