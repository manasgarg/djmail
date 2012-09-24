"""
Backend for test environment.
"""

from base import BaseEmailBackend

class EmailBackend(BaseEmailBackend):
    """A email backend for use during test sessions.

    The test connection stores email messages in a dummy outbox,
    rather than sending them out on the wire.

    The dummy outbox is accessible through the outbox instance attribute.
    """
    def __init__(self, *args, **kwargs):
        super(EmailBackend, self).__init__(*args, **kwargs)
        self.outbox = []

    def send_messages(self, messages):
        """Redirect messages to the dummy outbox"""
        self.outbox.extend(messages)
        return len(messages)
