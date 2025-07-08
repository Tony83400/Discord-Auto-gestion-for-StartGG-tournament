import subprocess
import sys

def ensure_pip():
    print("\nChecking pip installation...")
    try:
        # Check if pip is available
        subprocess.check_call([sys.executable, "-m", "pip", "--version"])
    except subprocess.CalledProcessError:
        print("pip not found, attempting installation with ensurepip...")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
        except subprocess.CalledProcessError:
            print("Automatic pip installation failed.")
            sys.exit(1)

def install_package(package):
    print(f"\nInstalling package {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError:
        print(f"Failed to install {package}.")
        sys.exit(1)

# Steps
ensure_pip()
install_package("requests")
install_package("discord")
install_package("python-dotenv")
print("\n\nInstallation completed successfully!")