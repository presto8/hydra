from setuptools import setup, find_packages

setup(
    name='hydra',
    version='0.1',
    python_requires='>=3.10',
    packages=find_packages(),
    package_data={'hydra': ['py.typed']},
    include_package_data=True,
    install_requires=[
        'attrs',
        'pyyaml',
    ],
    entry_points='''
        [console_scripts]
        hydra=src.cli:entrypoint
    ''',

    author="Preston Hunt",
    author_email="me@prestonhunt.com",
    description="Hydra",
    keywords="meta backup asymmetric public-key lockss",
    url="https://github.com/presto8/hydra",
)
