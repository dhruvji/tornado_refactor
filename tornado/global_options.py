#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A command line parsing module that lets modules define their own options.

This module is inspired by Google's `gflags
<https://github.com/google/python-gflags>`_. The primary difference
with libraries such as `argparse` is that a global registry is used so
that options may be defined in any module (it also enables
`tornado.log` by default). The rest of Tornado does not depend on this
module, so feel free to use `argparse` or other configuration
libraries if you prefer them.

Options must be defined with `define` before use,
generally at the top level of a module. The options are then
accessible as attributes of `options`::

    # myapp/db.py
    from tornado.global_options import define, options

    define("mysql_host", default="127.0.0.1:3306", help="Main user DB")
    define("memcache_hosts", default="127.0.0.1:11011", multiple=True,
           help="Main user memcache servers")

    def connect():
        db = database.Connection(options.mysql_host)
        ...

    # myapp/server.py
    from tornado.global_options import define, options

    define("port", default=8080, help="port to listen on")

    def start_server():
        app = make_app()
        app.listen(options.port)

The ``main()`` method of your application does not need to be aware of all of
the options used throughout your program; they are all automatically loaded
when the modules are loaded.  However, all modules that define options
must have been imported before the command line is parsed.

Your ``main()`` method can parse the command line or parse a config file with
either `parse_command_line` or `parse_config_file`::

    import myapp.db, myapp.server
    import tornado

    if __name__ == '__main__':
        tornado.global_options.parse_command_line()
        # or
        tornado.global_options.parse_config_file("/etc/server.conf")

.. note::

   When using multiple ``parse_*`` functions, pass ``final=False`` to all
   but the last one, or side effects may occur twice (in particular,
   this can result in log messages being doubled).

`options` is a singleton instance of `tornado.options.OptionParser`, and
the top-level functions in this module (`define`, `parse_command_line`, etc)
simply call methods on it.  You may create additional `tornado.options.OptionParser`
instances to define isolated sets of options, such as for subcommands.

.. note::

   By default, several options are defined that will configure the
   standard `logging` module when `parse_command_line` or `parse_config_file`
   are called.  If you want Tornado to leave the logging configuration
   alone so you can manage it yourself, either pass ``--logging=none``
   on the command line or do the following to disable it in code::

       from tornado.global_options import options, parse_command_line
       options.logging = None
       parse_command_line()

.. note::

   `parse_command_line` or `parse_config_file` function should called after
   logging configuration and user-defined command line flags using the
   ``callback`` option definition, or these configurations will not take effect.

.. versionchanged:: 4.3
   Dashes and underscores are fully interchangeable in option names;
   options can be defined, set, and read with any mix of the two.
   Dashes are typical for command-line usage while config files require
   underscores.
"""

from tornado.log import define_logging_options
from tornado.options import OptionParser

from typing import (
    Any,
    Callable,
    List,
    TextIO,
    Optional,
)

options = OptionParser()
"""Global options object.

All defined options are available as attributes on this object.
"""


def define(
    name: str,
    default: Any = None,
    type: Optional[type] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
    multiple: bool = False,
    group: Optional[str] = None,
    callback: Optional[Callable[[Any], None]] = None,
) -> None:
    """Defines an option in the global namespace.

    See `tornado.options.OptionParser.define`.
    """
    return options.define(
        name,
        default=default,
        type=type,
        help=help,
        metavar=metavar,
        multiple=multiple,
        group=group,
        callback=callback,
    )


def parse_command_line(
    args: Optional[List[str]] = None, final: bool = True
) -> List[str]:
    """Parses global options from the command line.

    See `tornado.options.OptionParser.parse_command_line`.
    """
    return options.parse_command_line(args, final=final)


def parse_config_file(path: str, final: bool = True) -> None:
    """Parses global options from a config file.

    See `tornado.options.OptionParser.parse_config_file`.
    """
    return options.parse_config_file(path, final=final)


def print_help(file: Optional[TextIO] = None) -> None:
    """Prints all the command line options to stderr (or another file).

    See `tornado.options.OptionParser.print_help`.
    """
    return options.print_help(file)


def add_parse_callback(callback: Callable[[], None]) -> None:
    """Adds a parse callback, to be invoked when option parsing is done.

    See `tornado.options.OptionParser.add_parse_callback`
    """
    options.add_parse_callback(callback)


# Default options
define_logging_options(options)
