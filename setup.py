from setuptools import setup

setup(
    name="hegpdup",
    description="Duplicate Zone In Clinical Text",
    license="GPLv3",
    packages=["hegpdup"],
    install_requires=["intervaltree>=3.0.0"],
    extras_require={"tests": ["pytest"]},
)
