from setuptools import setup

setup(
    name="hegpdup",
    description="Duplicate Zone In Clinical Text",
    license="GPLv3",
    packages=["hegpdup"],
    extras_require = {
        "tests": ["pytest"],
        "ncls":  ["ncls>=0.0.66", "numpy"],
        "intervaltree":  ["intervaltree>=3.0.0"],
    },
)
