"""Replacement-install the frozen source-63 APK using the existing save-preserving installer."""
from pathlib import Path
import install_home_lives_build as installer


def main():
    installer.OUT = Path(__file__).resolve().parents[2] / 'Verification/Evidence/GameplayLoadingAndroid'
    installer.main()


if __name__ == '__main__':
    main()
