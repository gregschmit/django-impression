Impression - The CMS For Email
==============================

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


Architectures
=============

There are a few ways to integrate Impression into an environment:

- **Standalone:** Impression can be run from a system to serve RESTful requests from
  your web applications. As long as you use HTTPS, this can be done across the
  internet. Here are some use cases:

  - You have more than 1 web application operating in your ecosystem and want to
    centralize your email templating within your organization.
  - You have a fleet of systems in the hands of customers (untrusted users) to whom
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
============

.. code-block:: shell

    $ pip install django-impression


Installing Using Docker
-----------------------

blah blah blah


Primary System (manual install)
-------------------------------

You can deploy the Dockerfile to a container,

Add ``impression`` to your ``INSTALLED_APPS``, run migrations, and configure some
settings:

.. code-block:: python

    # this should be your *actual* email backend
    IMPRESSION_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_BACKEND = "impression.backends.LocalEmailBackend"

To hook the API endpoint ``/api/send_message`` into your project, just add this entry to
your URL configuration's ``urlpatterns`` list:

.. code-block:: python

    path("api/", include("impression.api.urls")),  # includes the send_message endpoint

If you want to have the Impression branded Admin UI, add this to your URL config in
place of your normal admin URLs:

.. code-block:: python

    from impression.admin_ui.sites import custom_admin_site
    urlpatterns = [
        path("admin/", custom_admin_site.urls),
        ...
    ]

Also, include ``impression.admin_ui`` in your INSTALLED_APPS.


Other Applications
------------------

For remote systems that will talk to your primary Impression server over the REST API,
then do not include ``impression`` in your ``INSTALLED_APPS``, but do add
``django-impression`` to your requirements to ensure it's installed in the environment.
Configure your settings like this:

.. code-block:: python

    EMAIL_BACKEND = "impression.client.backends.RemoteEmailBackend"
    IMPRESSION_DEFAULT_TARGET = "https://impression.example.org/api/send_message/"
    IMPRESSION_DEFAULT_TOKEN = "my_api_auth_token_here"

If you want to store your credentials in the database, include ``impression.client`` in
your ``INSTALLED_APPS``, then run database migrations.


Configuration
=============

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
   use ``send_mail`` to reach your Impression server.


Tests
=====

.. code-block:: shell

    $ python manage.py test
