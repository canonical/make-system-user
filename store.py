# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2021 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import json
import os
import pathlib
from typing import Optional, TextIO
from urllib.parse import urljoin, urlparse

import pymacaroons
import requests
from simplejson.scanner import JSONDecodeError
from xdg import BaseDirectory

#from . import agent, _config, errors, _http_client
from http_clients import _config
from http_clients import  errors
from http_clients import  _http_client


def main():
    print("Hello World!")

if __name__ == "__main__":
    main()
