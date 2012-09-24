Django's core mail package outside django's codebase
====================================================

I had a need to send emails in a flask app but didn't find anything to my liking.
django.core.mail has always looked good to me and I wondered if something
similar was available outside django. When I didn't find anything that would
make me happy, I just extracted the django.core.mail code and rolled it out in
a separate package.

The interface is same as django.core.mail with the following two differences:

* import from djmail instead of django.core.mail.

* django.core.mail uses django.conf.settings for configuration. I had to build
the config into djmail. You'll need to call djmail.config.update_djmail_config()
method once on startup and pass the relevant configuration as a dictionary. e.g.

```
from djmail.config import djmail_update_config

djmail_update_config({"EMAIL_HOST": "mysmtp.server.com", "EMAIL_PORT": 255})
```

You can call djmail_update_config as many times as you wish.

This package works independent of django, flask or any other framework.
