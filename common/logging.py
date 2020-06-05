"""
Mousey: Discord Moderation Bot
Copyright (c) 2016 - 2020 Lilly Rose Berner

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import contextlib
import logging


@contextlib.contextmanager
def setup_logging():
    """Context manager to set up and shut down logging for the program."""

    try:
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        )

        root.addHandler(handler)

        # Remove all successful member chunking messages on startup/re-connect
        logging.getLogger('discord.state').addFilter(lambda x: 'Processed a chunk' not in x.msg)

        yield
    finally:
        logging.shutdown()
