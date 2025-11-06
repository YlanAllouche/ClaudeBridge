#!/usr/bin/env python3
import os
import re
import sys
import tarfile
import urllib.request
from pathlib import Path
from urllib.error import URLError

STATIC_DIR = Path(__file__).parent.parent / "static"
VENDORS_DIR = STATIC_DIR / "vendors"


# TODO: Consider turning into a manifest at this point
DEPENDENCIES = {
    "webawesome": {
        "url": "https://registry.npmjs.org/@awesome.me/webawesome/-/webawesome-3.0.0.tgz",
        "extract_path": "package/dist-cdn",
        "target_dir": "webawesome",
    },
    "deep-chat": {
        "url": "https://registry.npmjs.org/deep-chat/-/deep-chat-2.3.0.tgz",
        "extract_path": "package/dist",
        "target_dir": "deep-chat",
    },
    "highlight.js": {
        "files": [
            {
                "url": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js",
                "target": "highlight.min.js",
            },
            {
                "url": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/atom-one-light.min.css",
                "target": "styles/atom-one-light.min.css",
            },
        ],
        "target_dir": "highlight.js",
    },
    "htmx": {
        "url": "https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.8.tgz",
        "extract_path": "package/dist",
        "target_dir": "htmx",
    },
    "fontawesome": {
        "url": "https://registry.npmjs.org/@fortawesome/fontawesome-free/-/fontawesome-free-6.7.1.tgz",
        "extract_path": "package",
        "target_dir": "fontawesome",
    },
}

GOOGLE_FONTS_CSS_URL = "https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Merriweather:wght@300;400;700&display=swap"


def download_files(name, config):
    """Download individual files for a dependency."""
    target_dir = VENDORS_DIR / config["target_dir"]

    if target_dir.exists():
        print(f"{name} already exists at {target_dir}")
        return True

    files = config.get("files", [])
    if not files:
        print(f"ERROR: No files specified for {name}")
        return False

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        downloaded_count = 0

        for file_config in files:
            file_url = file_config["url"]
            target_path = target_dir / file_config["target"]

            target_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"Downloading {name}: {file_config['target']}")
            urllib.request.urlretrieve(file_url, target_path)
            downloaded_count += 1

        if downloaded_count == 0:
            print(f"ERROR: No files were downloaded for {name}")
            return False

        print(f"{name} downloaded to {target_dir} ({downloaded_count} files)")
        return True

    except URLError as e:
        print(f"Failed to download {name}: {e}")
        return False
    except Exception as e:
        print(f"Error processing {name}: {e}")
        return False


def download_and_extract(name, config):
    """Download and extract a dependency."""
    target_dir = VENDORS_DIR / config["target_dir"]

    if target_dir.exists():
        print(f"{name} already exists at {target_dir}")
        return True

    tgz_path = VENDORS_DIR / f"{name}.tgz"

    try:
        print(f"Downloading {name}")
        urllib.request.urlretrieve(config["url"], tgz_path)
        print(f"Extracting {name}")

        with tarfile.open(tgz_path, "r:gz") as tar:
            members = tar.getmembers()
            extract_members = [
                m for m in members if m.name.startswith(config["extract_path"])
            ]

            if not extract_members:
                print(
                    f"ERROR: No files found matching extract_path '{config['extract_path']}' in {name}"
                )
                print(f"Available paths in archive:")
                paths = set()
                for m in members[:20]:
                    root_path = m.name.split("/")[0] if "/" in m.name else m.name
                    paths.add(root_path)
                for p in sorted(paths):
                    print(f"  - {p}")
                tgz_path.unlink()
                return False

            extracted_count = 0
            for member in extract_members:
                member.name = member.name.replace(config["extract_path"] + "/", "", 1)
                if member.name:
                    tar.extract(member, target_dir)
                    extracted_count += 1

            if extracted_count == 0:
                print(f"ERROR: No files were extracted for {name}")
                tgz_path.unlink()
                return False

        tgz_path.unlink()
        print(f"{name} extracted to {target_dir} ({extracted_count} files)")
        return True

    except URLError as e:
        print(f"Failed to download {name}: {e}")
        return False
    except Exception as e:
        print(f"Error processing {name}: {e}")
        if tgz_path.exists():
            tgz_path.unlink()
        return False


def download_google_fonts():
    fonts_dir = VENDORS_DIR / "fonts"
    css_file = fonts_dir / "fonts.css"

    if css_file.exists():
        print(f"Google Fonts already exists at {fonts_dir}")
        return True

    try:
        fonts_dir.mkdir(parents=True, exist_ok=True)
        print("Downloading Google Fonts CSS...")

        with urllib.request.urlopen(GOOGLE_FONTS_CSS_URL) as response:
            css_content = response.read().decode("utf-8")

        font_urls = re.findall(r"url\((https://[^\)]+)\)", css_content)

        print(f"Downloading {len(font_urls)} font files...")
        for i, font_url in enumerate(font_urls, 1):
            font_filename = font_url.split("/")[-1]
            font_path = fonts_dir / font_filename
            urllib.request.urlretrieve(font_url, font_path)
            css_content = css_content.replace(font_url, font_filename)

        with open(css_file, "w", encoding="utf-8") as f:
            f.write(css_content)

        print(f"fonts extracted to {fonts_dir}")
        return True

    except Exception as e:
        print(f"Error downloading Google Fonts: {e}")
        return False


def main():
    """Download all external dependencies."""
    VENDORS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Downloading external dependencies...")
    print("=" * 60)

    all_success = True
    for name, config in DEPENDENCIES.items():
        if "files" in config:
            if not download_files(name, config):
                all_success = False
        else:
            if not download_and_extract(name, config):
                all_success = False

    if not download_google_fonts():
        all_success = False

    print("=" * 60)
    if all_success:
        print("All dependencies downloaded successfully!")
        return 0
    else:
        print("Some dependencies failed to download")
        return 1


if __name__ == "__main__":
    sys.exit(main())
