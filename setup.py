from pathlib import Path
from setuptools import setup

long_description = (Path(__file__).parent / "README.md").read_text()

setup(
    name="duptextfinder",
    description="Detect duplicated zones in (clinical) text",
    license="MIT",
    packages=["duptextfinder"],
    extras_require = {
        "tests": ["pytest", "pytest-mock"],
        "ncls":  ["ncls>=0.0.66", "numpy"],
        "intervaltree":  ["intervaltree>=3.0.0"],
    },
    version="0.3.0",
    keywords = ["TEXT", "DUPLICATION", "DUPLICATE", "CLINICAL"],
    url="https://github.com/equipe22/duplicatedZoneInClinicalText",
    long_description=long_description,
    long_description_content_type="text/markdown"
)
