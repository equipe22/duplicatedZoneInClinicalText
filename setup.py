from setuptools import setup

setup(
    name="duplicatefinder",
    description="Duplicate Zone In Clinical Text",
    license="GPLv3",
    packages=["duplicatefinder"],
    extras_require = {
        "tests": ["pytest", "pytest-mock"],
        "ncls":  ["ncls>=0.0.66", "numpy"],
        "intervaltree":  ["intervaltree>=3.0.0"],
    },
)
