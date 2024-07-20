from setuptools import setup

setup(
    name="bagelshop",
    version="2024.07.19",
    description="Library procedures and cogs for Bagelbot",
    author="Wade Foster",
    author_email="jwade109@vt.edu",
    packages=["bagelshop"],
    scripts=[
       "scripts/bagelbot",
       "scripts/ipcam.py"
    ],
)
