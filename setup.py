from setuptools import setup
import sdist_upip

from wifi_manager import __version__, __author__, __description__

from os import path

this_directory = path.abspath(path.dirname(__file__))

with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

classifiers = [
    'Development Status :: 2 - Pre-Alpha',
    'Intended Audience :: Education',
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Embedded Systems',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3',
]

setup(
    author=__author__,
    author_email='',
    name="",  # library name
    version=__version__,
    packages=['wifi_manager'],
    classifiers=classifiers,
    cmdclass={'sdist': sdist_upip.sdist},
    license='MIT',
    description=__description__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Saketh-Chandra/micropython-wifi_manager',
    keywords=["micropython", "esp8266", "wifi", "Wi-Fi", "manager", "wifi-manager"],
)
