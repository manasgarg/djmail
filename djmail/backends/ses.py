#!/usr/bin/env python
#
# Copyright (c) 2011 Harry Marr
#  
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#  
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#  
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from djmail.backends.base import BaseEmailBackend
from djmail.config import config

from boto.regioninfo import RegionInfo
from boto.ses import SESConnection

from datetime import datetime, timedelta
from time import sleep


# When changing this, remember to change it in setup.py
VERSION = (0, "5alpha", 0)
__version__ = '.'.join([str(x) for x in VERSION])
__author__ = 'Harry Marr'
__all__ = ('SESBackend',)

# These would be nice to make class-level variables, but the backend is
# re-created for each outgoing email/batch.
# recent_send_times also is not going to work quite right if there are multiple
# email backends with different rate limits returned by SES, but that seems
# like it would be rare.
cached_rate_limits = {}
recent_send_times = []

def dkim_sign(message):
    """Return signed email message if dkim package and settings are available."""

    if "DKIM_DOMAIN" not in config:
        return message

    try:
        import dkim
    except ImportError:
        pass
    else:
        dkim_domain = config["DKIM_DOMAIN"]
        dkim_key = config["DKIM_PRIVATE_KEY"]
        dkim_selector = config["DKIM_SELECTOR"]
        dkim_headers = config["DKIM_HEADERS"]
        if dkim_domain and dkim_key:
            sig = dkim.sign(message,
                            dkim_selector,
                            dkim_domain,
                            dkim_key,
                            include_headers=dkim_headers)
            message = sig + message
    return message


class SESBackend(BaseEmailBackend):
    """An Email backend that uses Amazon's Simple Email Service.
    """

    def __init__(self, fail_silently=False, *args, **kwargs):
        super(SESBackend, self).__init__(fail_silently=fail_silently, *args,
                                         **kwargs)

        self._access_key_id = config["AWS_KEY"]
        self._access_key = config["AWS_SECRET"]
        self._throttle = config["AWS_SES_AUTO_THROTTLE"]

        self.connection = None

    def open(self):
        """Create a connection to the AWS API server. This can be reused for
        sending multiple emails.
        """
        if self.connection:
            return False

        try:
            self.connection = SESConnection(
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._access_key
            )
        except:
            if not self.fail_silently:
                raise

    def close(self):
        """Close any open HTTP connections to the API server.
        """
        try:
            self.connection.close()
            self.connection = None
        except:
            if not self.fail_silently:
                raise

    def send_messages(self, email_messages):
        """Sends one or more EmailMessage objects and returns the number of
        email messages sent.
        """
        if not email_messages:
            return

        new_conn_created = self.open()
        if not self.connection:
            # Failed silently
            return

        num_sent = 0
        source = config["AWS_SES_RETURN_PATH"]
        for message in email_messages:
            # Automatic throttling. Assumes that this is the only SES client
            # currently operating. The AWS_SES_AUTO_THROTTLE setting is a
            # factor to apply to the rate limit, with a default of 0.5 to stay
            # well below the actual SES throttle.
            # Set the setting to 0 or None to disable throttling.
            if self._throttle:
                global recent_send_times

                now = datetime.now()

                # Get and cache the current SES max-per-second rate limit
                # returned by the SES API.
                rate_limit = self.get_rate_limit()

                # Prune from recent_send_times anything more than a few seconds
                # ago. Even though SES reports a maximum per-second, the way
                # they enforce the limit may not be on a one-second window.
                # To be safe, we use a two-second window (but allow 2 times the
                # rate limit) and then also have a default rate limit factor of
                # 0.5 so that we really limit the one-second amount in two
                # seconds.
                window = 2.0  # seconds
                window_start = now - timedelta(seconds=window)
                new_send_times = []
                for time in recent_send_times:
                    if time > window_start:
                        new_send_times.append(time)
                recent_send_times = new_send_times

                # If the number of recent send times in the last 1/_throttle
                # seconds exceeds the rate limit, add a delay.
                # Since I'm not sure how Amazon determines at exactly what
                # point to throttle, better be safe than sorry and let in, say,
                # half of the allowed rate.
                if len(new_send_times) > rate_limit * window * self._throttle:
                    # Sleep the remainder of the window period.
                    delta = now - new_send_times[0]
                    total_seconds = (delta.microseconds + (delta.seconds +
                            delta.days * 24 * 3600) * 10**6) / 10**6
                    delay = window - total_seconds
                    if delay > 0:
                        sleep(delay)

                recent_send_times.append(now)
                # end of throttling

            try:
                response = self.connection.send_raw_email(
                    source=source or message.from_email,
                    destinations=message.recipients(),
                    raw_message=unicode(dkim_sign(message.message().as_string()), 'utf-8')
                )
                message.extra_headers['status'] = 200
                message.extra_headers['message_id'] = response[
                    'SendRawEmailResponse']['SendRawEmailResult']['MessageId']
                message.extra_headers['request_id'] = response[
                    'SendRawEmailResponse']['ResponseMetadata']['RequestId']
                num_sent += 1
            except SESConnection.ResponseError, err:
                # Store failure information so to post process it if required
                error_keys = ['status', 'reason', 'body', 'request_id',
                                'error_code', 'error_message']
                for key in error_keys:
                    message.extra_headers[key] = getattr(err, key, None)
                if not self.fail_silently:
                    raise

        if new_conn_created:
            self.close()

        return num_sent

    def get_rate_limit(self):
        if self._access_key_id in cached_rate_limits:
            return cached_rate_limits[self._access_key_id]

        new_conn_created = self.open()
        if not self.connection:
            raise Exception(
                "No connection is available to check current SES rate limit.")
        try:
            quota_dict = self.connection.get_send_quota()
            max_per_second = quota_dict['GetSendQuotaResponse'][
                'GetSendQuotaResult']['MaxSendRate']
            ret = float(max_per_second)
            cached_rate_limits[self._access_key_id] = ret
            return ret
        finally:
            if new_conn_created:
                self.close()
