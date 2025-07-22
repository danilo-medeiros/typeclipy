from setuptools import setup, find_packages

setup(
    name='typeclipy',
    version='0.3.1',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "typeclipy": ["data/*.txt"]
    },
    install_requires=[
        "pytest",
        "Pygments"
    ],
    entry_points={
        "console_scripts": [
            "typeclipy = typeclipy.main:main",
        ],
    },
)
