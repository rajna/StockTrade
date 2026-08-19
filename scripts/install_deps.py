#!/usr/bin/env python3
"""
Dependency installer for Stock Data Fetcher skill

This script installs all required dependencies for the stock-data-fetcher skill.
"""

import subprocess
import sys


def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """Install all dependencies"""
    print("=" * 70)
    print("Stock Data Fetcher - Dependency Installer")
    print("=" * 70)
    
    # Required packages
    packages = [
        "akshare>=1.12.0",
        "baostock>=0.8.9",
        "selenium>=4.15.0",
        "webdriver-manager>=4.0.1",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "requests>=2.31.0",
    ]
    
    print(f"\n📦 Installing {len(packages)} packages...\n")
    
    failed = []
    
    for package in packages:
        print(f"Installing {package}...")
        if install_package(package):
            print(f"✅ {package} installed successfully")
        else:
            print(f"❌ Failed to install {package}")
            failed.append(package)
    
    print("\n" + "=" * 70)
    print("Installation Summary")
    print("=" * 70)
    
    if failed:
        print(f"\n❌ Failed to install {len(failed)} packages:")
        for package in failed:
            print(f"   - {package}")
        print("\nPlease try installing them manually:")
        print(f"   pip install {' '.join(failed)}")
        return 1
    else:
        print("\n✅ All dependencies installed successfully!")
        print("\nNext steps:")
        print("1. Install Chrome browser (required for real-time quotes)")
        print("2. Run test_skill.py to verify installation")
        print("3. Check usage_examples.py for usage examples")
        return 0


if __name__ == '__main__':
    sys.exit(main())
