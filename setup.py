from setuptools import find_packages, setup

__version__ = '1.2.0'

tests_require = [
    "flake8",
    "pytest",
    "pytest-cov",
]

with open('README.md', 'r') as fh:
    long_description = fh.read()


setup(
    name='next_theme_kit',
    author="29next",
    author_email="dev@29next.com",
    url='https://github.com/29next/theme-kit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    version=__version__,
    install_requires=[
        "PyYAML>=5.4",
        "requests>=2.25",
        "watchfiles>=0.18",
        "libsass>=0.21.0"
    ],
    entry_points={
        'console_scripts': [
            'ntk = ntk.__main__:main',
        ],
    },
    extras_require={"test": tests_require},
    packages=find_packages(),
    python_requires='>=3.10'
)
