from setuptools import setup, find_packages
import brickmaster2

setup(
    name="BrickMaster2",
    version=brickmaster2.__version__,
    packages=find_packages(),
    include_package_data=False,
    entry_points={
        "console_scripts": [
            "brickmaster = brickmaster.cli.main:main"
        ]
    }
)