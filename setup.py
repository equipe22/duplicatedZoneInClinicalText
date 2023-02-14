from setuptools import setup

setup(
    name="hegpdup",
    description="Duplicate Zone In Clinical Text",
    license="GPLv3",
    packages=["hegpdup"],
    install_requires=["intervaltree==2.1.0"],
    extras_require={"tests": ["pytest"]},
)
