Impression - The CMS For Email
##############################

.. image:: https://travis-ci.org/gregschmit/django-impression.svg?branch=master
    :alt: TravisCI
    :target: https://travis-ci.org/gregschmit/django-impression

.. image:: https://img.shields.io/pypi/v/django-impression
    :alt: PyPI
    :target: https://pypi.org/project/django-impression/

.. image:: https://coveralls.io/repos/github/gregschmit/django-impression/badge.svg?branch=master
    :alt: Coverage
    :target: https://coveralls.io/github/gregschmit/django-impression?branch=master

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code Style
    :target: https://github.com/ambv/black

Source: https://github.com/gregschmit/django-impression

PyPI: https://pypi.org/project/django-impression/

Django Impression is a reusable Django app that provides you with the ability to edit
your email templates in a web interface and configure distribution lists if you don't
have them configured on your email provider. It also implements a RESTful API so any
other web applications you have in your ecosystem can send consistent-looking emails.

**The Problem**: Email lists and templates for Django projects and other web
applications are often kept in source control, requiring developers to edit code when,
for example, your marketing guru wants to tweak the layout of one of your emails. They
may not want to sift through your backend code to make such changes. Even if they do,
you may want to have your email templates accessible over an API so all of your
organization's email templates can be centralized.

**The Solution**: Impression provides the ability to separate your email template system
from your source code, by building email templates as model instances. You can still use
file-based templates if you would like, and the model templates can even
``{% extend %}`` those file-based templates. This allows email templates to be modified
in the admin UI by a wider variety of users; not just those who have access to your
source code. Impression also exposes a REST API endpoint for sending emails from other
web applications, with easy-to-configure access controls. This makes it easier to
centralize your email brand and keep things looking awesome and consistent. You can run
Impression in an existing project, or you can run it standalone by itself (e.g.,
``impression.example.com``).

Key Features:

- Email templates are editable by users in the UI.
- API endpoints allow remote systems to send emails.
- API requests can contain a JSON for the "email body" which allows clean separation
  between the content (data sent by the remote system) and the presentation (defined by
  the Impression templates).
- Impression is protected by a system of semi-trust, where you can apply rate limits on
  the systems which use Impression, constrain which services/templates each remote
  system has access to, and control the format of the emails that are sent.


Architectures
#############

There are a few ways to integrate Impression into an environment:

- **Standalone:** Impression can be run from a system to serve RESTful requests from
  your web applications. As long as you use HTTPS, this can be done across the
  internet. Here are some use cases:

  - You have more than 1 web application operating in your ecosystem and want to
    centralize your email templating within your organization.
  - You have a fleet of systems in the hands of customers (semi-trusted users) to whom
    you cannot provide your SMTP details. You want them to be able to request emails to
    be sent (e.g., for notification systems).

- **Integrated:** Impression can be mixed in with an existing Django project. A use
  case could be:

  - A company has a couple people in the marketing department who are wizards with the
    Bootstrap Email framework; they don't need to have access to the source and they
    really want to quickly test and push out new designs. Using Impression along with
    the sleek template editing UI, powered by `CodeMirror <https://codemirror.net>`_,
    they can quickly develop email templates and deploy them without involving the
    development team.


Installation
############

.. code-block:: shell

    $ pip install django-impression


Configuration
*************

Whether you are going to run Impression from your existing project locally, or whether
you are going to integrate your existing project with a standalone Impression system
affects how you should configure
the settings.

There are 2 configuration schemes:

- Local: You wish to send emails from a project that has Impression integrated into it.
- Remote: You wish to send email remotely via the REST API of an Impression instance
  running in another project. (For our purposes, "Remote" means on another system, or
  even another project running on the same system, in which case you'll use localhost.)

Local
-----

Add ``impression`` to your ``INSTALLED_APPS``, run migrations, and configure some
settings:

.. code-block:: python

    # This should be your *actual* email backend.
    IMPRESSION_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

    # this is configured to pass emails to Impression.
    EMAIL_BACKEND = "impression.backends.LocalEmailBackend"

To hook the API endpoint ``/api/send_message`` into your project for remote systems,
just add this entry to your URL dispatcher's ``urlpatterns`` list:

.. code-block:: python

    path("api/", include("impression.api.urls")),  # includes the send_message endpoint


Remote
------

For remote systems that will talk to your Impression server over the REST API, use the
`Impression Client <https://github.com/gregschmit/django-impression-client>`_.


Installing as Standalone System
*******************************

It's a very good idea to setup a dedicated Django application on a server for your
organization (then all of your apps can use that system remotely).

To make things really easy, if you have a Docker or Virtual environment, or just wish to
spin Impression up on it's own server, you can check out
`ImpressionOS <https://github.com/gregschmit/impression_os>`_ to deploy Impression as
a standalone system. That project provides the ability to configure everything about the
system in the Admin UI, and even configure Let's Encrypt certificates to ensure your
email API is secure.


Model Configuration
###################

To get familiar with Impression models, here is a quick guide on which models to visit
first, in order:

1) Email addresses (the ``EmailAddress`` model): You should create email addresses for
   the email that you will be sending from.
2) Services (the ``Service`` model): You should create at least one "default" service.
   If you permit users to specify the emails that they send to (only for trusted
   systems!), then those emails will be created on the fly when those messages are
   created.
3) Templates (the ``Template`` model): Go ahead and create a template that adds a
   footer. Ensure you add ``{{ body }}`` somewhere in the body, and ``{{ subject }}`` in
   the subject and the subject/body of the email request will be inserted there. You can
   then hook it into your Service by editing your service and selecting it under the
   ``template`` field. If you're feeling adventurous, you can use an email template from
   `Bootstrap <https://bootstrapemail.com>`_ or
   `Foundation <https://foundation.zurb.com/emails.html>`_.
4) Now you can either send email with Django's ``send_mail``, and remote systems can
   use ``send_mail`` to reach your Impression server, provided they have followed the
   configuration instructions above.


Tests
#####

.. code-block:: shell

    $ python manage.py test
