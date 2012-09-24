#!/usr/bin/env python

from distutils.core import setup

setup( name="djmail",
    version = "0.1",
    description = "django.core.mail code extracted from django and usable from non-django applications.",
    author = "Manas Garg",
    author_email = "manasgarg@gmail.com",
    license = "BSD License",
    url = "https://github.com/manasgarg/djmail",
    #data_files = ["LICENSE", "Readme.md"],
    packages = ["djmail", "djmail.backends"],
    long_description = ""
)
