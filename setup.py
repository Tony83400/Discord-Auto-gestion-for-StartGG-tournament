import subprocess
import sys

def ensure_pip():
    print("\nVérification de l'installation de pip...")
    try:
        # Vérifie si pip est dispo
        subprocess.check_call([sys.executable, "-m", "pip", "--version"])
    except subprocess.CalledProcessError:
        print("pip non trouvé, tentative d'installation avec ensurepip...")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
        except subprocess.CalledProcessError:
            print("Échec de l'installation automatique de pip.")
            sys.exit(1)

def install_package(package):
    print(f"\nInstallation du package {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError:
        print(f"Échec de l'installation de {package}.")
        sys.exit(1)

# Étapes
ensure_pip()
install_package("requests")
install_package("discord")
install_package("python-dotenv")
print("\n\nInstallation terminée avec succès !")  