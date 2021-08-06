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
from http_clients import  store_api
import http_clients


def main():
    print("Hello World!")
    #authClient = http_clients.AuthClient    
    httpClient = http_clients.Client()
    authClient = http_clients.UbuntuOneAuthClient() 
    authClient.login()
    url = "https://dashboard.snapcraft.io/dev/api/account"
    data = {"account-keys": str,
            "display-name": str,
            "email": str,
            "id": str,
            "validation": str,
            "stores": [],
            "username": str,
            "account-id": str,
            "account-keys": [],
            } 
    #data = dict()
    headers = str
    response = authClient.request(
        "GET",
        url,
        headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": authClient.auth},
    )

    print("status code", response.status_code)
    if response.ok:
       print(data)
    else:
        print('response error')
        print("text", response.text)

    print("json", response.json())
    print("encoding", response.encoding)
    

if __name__ == "__main__":
    main()
