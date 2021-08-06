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

import getpass
import logging
import json
import os
import sys 
import pathlib
from typing import Optional, TextIO
from urllib.parse import urljoin, urlparse

import pymacaroons
import requests
from simplejson.scanner import JSONDecodeError
from xdg import BaseDirectory

from http_clients import _config
from http_clients import  _http_client
import http_clients


def main():
    authClient = http_clients.UbuntuOneAuthClient() 

    # get macaroon for account 

    url = "https://dashboard.snapcraft.io/dev/api/acl/"
    data = {"permissions":["package_access"]}
    # getting macaroon can only be anonymous, so no auth client
    response = requests.request(
        "POST",
        url,
        data=json.dumps(data),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    #if response.ok:
    #    print(json.dumps(response.json(), indent=2))
    #else:
    #    print(' mac response error')
    #    print("mac text", response.text)

    _macaroon = response.json()["macaroon"]
    #_email = "ce-team-test@canonical.com"
    #_password  = "TheLastThingThatHarryToldSally"
    _email = input("Ubuntu SSO email address: ")
    _password = getpass.getpass("password: ")
    _otp = input("two factor: ") 
    authClient.login(_email, _password, _macaroon, _otp)

    # sys.exit()
    # get account info

    url = "https://dashboard.snapcraft.io/dev/api/account"
    headers = str
    response = authClient.request(
        "GET",
        url,
        headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": authClient.auth},
    )

    #print("status code", response.status_code)
    if response.ok:
        print(json.dumps(response.json(), indent=2))
    else:    
        print('response error')
        print("text", response.text)

    #print("encoding", response.encoding)

if __name__ == "__main__":
    main()
