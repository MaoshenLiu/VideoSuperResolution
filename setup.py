from setuptools import find_packages
from setuptools import setup

VERSION = '0.2.14'

REQUIRED_PACKAGES = [
    'numpy',
    'Image',
]

if __name__ == '__main__':
    setup(
        name='VSR',
        version=VERSION,
        description='Video Super-Resolution Framework',
        url='https://github.com/LoSealL/VideoSuperResolution',
        packages=find_packages(),
        install_requires=REQUIRED_PACKAGES,
        license='MIT',
        author='Wenyi Tang',
        author_email='wenyitang@outlook.com'
    )
