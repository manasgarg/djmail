#!/usr/bin/env python

config = {
    "DEFAULT_FROM_EMAIL": "",
    "DEFAULT_CHARSET": "utf8",
    "EMAIL_BACKEND": "djmail.backends.console.EmailBackend",
    "ADMINS": [],
    "EMAIL_SUBJECT_PREFIX": "",
    "SERVER_EMAIL": None,
    "EMAIL_FILE_PATH": None,
    "EMAIL_HOST": "localhost",
    "EMAIL_PORT": 25,
    "EMAIL_HOST_USER": None,
    "EMAIL_HOST_PASSWORD": None,
    "EMAIL_USE_TLS": False,

    # For the SES.
    "AWS_KEY": "",
    "AWS_SECRET": "",
    "AWS_SES_AUTO_THROTTLE": 0.5,
    "AWS_SES_RETURN_PATH": "",
}

def update_djmail_config( new_config):
    config.update( new_config)
