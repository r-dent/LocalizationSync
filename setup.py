import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="localization-sync",
    entry_points= {
        'console_scripts': [
            'l10n_sync = Sources.data_sync:main',
        ],
    },
    version="0.1.0",
    author="Roman Gille",
    author_email="developer@romangille.com",
    description="A python script that generates localization files for iOS and Android projects from a public GoogleSheet.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/r-dent/LocalizationSync",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Localization",
        "Topic :: Software Development :: Embedded Systems",
        "Topic :: Utilities",
    ],
    python_requires='>=3.6',
)