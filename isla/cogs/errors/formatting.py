# -*- coding: utf-8 -*-

"""
Isla Bot: Reporting functionality for a Terraria Server
Copyright (c) 2016 - 2020 Lilly Rose Berner
Copyright (C) 2020 Rina

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

__all__ = ("remove_accents",)


def remove_accents(text):
    """Replace grave accents (`) with similar ones to not break code blocks."""

    # Always cast to string so we don't have to deal with this elsewhere
    return str(text).replace("\N{GRAVE ACCENT}", "\N{MODIFIER LETTER GRAVE ACCENT}")
