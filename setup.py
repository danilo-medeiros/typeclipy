from setuptools import setup, find_packages

setup(
    name='typeclipy',
    version='0.2.0',
    packages=find_packages(),
    install_requires=[
        "pytest",
    ],
    entry_points={
        "console_scripts": [
            "typeclipy = typeclipy.main:main",
        ],
    },
)
