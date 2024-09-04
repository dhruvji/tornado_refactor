import logging

from tornado.log import LogFormatter

from typing import Any, Optional


def enable_pretty_logging(
    options: Any = None, logger: Optional[logging.Logger] = None
) -> None:
    """Turns on formatted logging output as configured.

    This is called automatically by `tornado.options.parse_command_line`
    and `tornado.options.parse_config_file`.
    """
    if options is None:
        import tornado.options

        options = tornado.options.options
    if options.logging is None or options.logging.lower() == "none":
        return
    if logger is None:
        logger = logging.getLogger()
    logger.setLevel(getattr(logging, options.logging.upper()))
    if options.log_file_prefix:
        rotate_mode = options.log_rotate_mode
        if rotate_mode == "size":
            channel = logging.handlers.RotatingFileHandler(
                filename=options.log_file_prefix,
                maxBytes=options.log_file_max_size,
                backupCount=options.log_file_num_backups,
                encoding="utf-8",
            )  # type: logging.Handler
        elif rotate_mode == "time":
            channel = logging.handlers.TimedRotatingFileHandler(
                filename=options.log_file_prefix,
                when=options.log_rotate_when,
                interval=options.log_rotate_interval,
                backupCount=options.log_file_num_backups,
                encoding="utf-8",
            )
        else:
            error_message = (
                "The value of log_rotate_mode option should be "
                + '"size" or "time", not "%s".' % rotate_mode
            )
            raise ValueError(error_message)
        channel.setFormatter(LogFormatter(color=False))
        logger.addHandler(channel)

    if options.log_to_stderr or (options.log_to_stderr is None and not logger.handlers):
        # Set up color if we are in a tty and curses is installed
        channel = logging.StreamHandler()
        channel.setFormatter(LogFormatter())
        logger.addHandler(channel)


def define_logging_options(options: Any = None) -> None:
    """Add logging-related flags to ``options``.

    These options are present automatically on the default options instance;
    this method is only necessary if you have created your own `.OptionParser`.

    .. versionadded:: 4.2
        This function existed in prior versions but was broken and undocumented until 4.2.
    """
    if options is None:
        # late import to prevent cycle
        import tornado.options

        options = tornado.options.options
    options.define(
        "logging",
        default="info",
        help=(
            "Set the Python log level. If 'none', tornado won't touch the "
            "logging configuration."
        ),
        metavar="debug|info|warning|error|none",
    )
    options.define(
        "log_to_stderr",
        type=bool,
        default=None,
        help=(
            "Send log output to stderr (colorized if possible). "
            "By default use stderr if --log_file_prefix is not set and "
            "no other logging is configured."
        ),
    )
    options.define(
        "log_file_prefix",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Path prefix for log files. "
            "Note that if you are running multiple tornado processes, "
            "log_file_prefix must be different for each of them (e.g. "
            "include the port number)"
        ),
    )
    options.define(
        "log_file_max_size",
        type=int,
        default=100 * 1000 * 1000,
        help="max size of log files before rollover",
    )
    options.define(
        "log_file_num_backups", type=int, default=10, help="number of log files to keep"
    )

    options.define(
        "log_rotate_when",
        type=str,
        default="midnight",
        help=(
            "specify the type of TimedRotatingFileHandler interval "
            "other options:('S', 'M', 'H', 'D', 'W0'-'W6')"
        ),
    )
    options.define(
        "log_rotate_interval",
        type=int,
        default=1,
        help="The interval value of timed rotating",
    )

    options.define(
        "log_rotate_mode",
        type=str,
        default="size",
        help="The mode of rotating files(time or size)",
    )

    options.add_parse_callback(lambda: enable_pretty_logging(options))
