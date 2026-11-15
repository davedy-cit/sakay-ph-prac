"""Django project package for Sakay.ph.

PyMySQL is registered as a drop-in replacement for ``mysqlclient`` so the
project needs neither a C compiler nor MySQL client libraries — which is what
makes the install reproducible on Windows.

This has to run before Django reads ``DATABASES``, so it lives here: Django
imports the project package before it imports ``settings``.
"""

import pymysql

pymysql.install_as_MySQLdb()
