
import os

try:
    os.system("python -m ensurepip --upgrade")
    os.system("python -m pip install --upgrade setuptools")
except:
    pass

from setuptools import setup, find_packages

req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
if os.path.exists(req_file):
    with open(req_file) as f:
        requirements = f.read().splitlines()
else:
    requirements = []

with open(os.path.join('pyfortracc', '_version.py')) as f:
    version_line = next(filter(lambda line: line.startswith('__version__'), f))
    __version__ = version_line.split('=')[-1]

setup(
    name="pyfortracc",
    version=__version__.strip().strip('"'),
    author="Helvecio B. L. Neto, Alan J. P. Calheiros",
    author_email="fortracc.project@inpe.br",
    description="A Python package for track and forecasting configurable clusters.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/fortracc/pyfortracc",
    packages=find_packages(),
    install_requires=requirements,
    license="LICENSE",
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Hydrology",
    ]
)
