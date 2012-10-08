#!/usr/bin/env python

import sys

from djmail.config import config
from djmail.message import EmailMessage, EmailMultiAlternatives

def get_connection(backend=None, fail_silently=False, **kwds):
    """Load an e-mail backend and return an instance of it.

    If backend is None (default) config["EMAIL_BACKEND"] is used.

    Both fail_silently and other keyword arguments are used in the
    constructor of the backend.
    """
    path = backend or config["EMAIL_BACKEND"]
    try:
        mod_name, klass_name = path.rsplit('.', 1)
        __import__(mod_name)
        mod = sys.modules[mod_name]
    except ImportError, e:
        raise Exception('Error importing email backend module %s: "%s"' % (mod_name, e))

    try:
        klass = getattr(mod, klass_name)
    except AttributeError:
        raise Exception('Module "%s" does not define a '
                                    '"%s" class' % (mod_name, klass_name))
    return klass(fail_silently=fail_silently, **kwds)


def send_mail(subject, message, from_email, recipient_list,
              fail_silently=False, auth_user=None, auth_password=None,
              connection=None):
    """
    Easy wrapper for sending a single message to a recipient list. All members
    of the recipient list will see the other recipients in the 'To' field.

    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    connection = connection or get_connection(username=auth_user,
                                    password=auth_password,
                                    fail_silently=fail_silently)
    return EmailMessage(subject, message, from_email, recipient_list,
                        connection=connection).send()


def send_mass_mail(datatuple, fail_silently=False, auth_user=None,
                   auth_password=None, connection=None):
    """
    Given a datatuple of (subject, message, from_email, recipient_list), sends
    each message to each recipient list. Returns the number of e-mails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    Note: The API for this method is frozen. New code wanting to extend the
    functionality should use the EmailMessage class directly.
    """
    connection = connection or get_connection(username=auth_user,
                                    password=auth_password,
                                    fail_silently=fail_silently)
    messages = [EmailMessage(subject, message, sender, recipient)
                for subject, message, sender, recipient in datatuple]
    return connection.send_messages(messages)

def send_alternative_mail(subject, message, from_email, recipient_list, 
                fail_silently=False, connection=None, html_message=None):
    """Sends a multipart/alternative message."""

    mail = EmailMultiAlternatives(subject,
                message, from_email, recipient_list,
                connection=connection)
    if html_message:
        mail.attach_alternative(html_message, 'text/html')
    mail.send(fail_silently=fail_silently)

def mail_admins(subject, message, fail_silently=False, connection=None,
                html_message=None):
    """Sends a message to the admins, as defined by the ADMINS setting."""
    if not config["ADMINS"]:
        return
    mail = EmailMultiAlternatives(u'%s%s' % (config["EMAIL_SUBJECT_PREFIX"], subject),
                message, config["SERVER_EMAIL"], [a[1] for a in config["ADMINS"]],
                connection=connection)
    if html_message:
        mail.attach_alternative(html_message, 'text/html')
    mail.send(fail_silently=fail_silently)
