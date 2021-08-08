"""
Copyright (C) 2021 Canonical Ltd

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
* Authored by:
 Kyle Nitzsche <kyle.nitzsche@canonical.com>
"""

import sys
import argparse
import textwrap
from argparse import RawTextHelpFormatter
import subprocess
import crypt
import json
import time
from datetime import datetime, timedelta
import json
import http_clients
import requests
import getpass


PROGRAM = ''
VERSION = '0.1'

#TODO: arg help i18n'd

def parseargs(argv=None):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        prog=PROGRAM,
        description=textwrap.dedent('''\
Create and sign a System-User Assertion using a local snapcraft key that has been registered with an Ubuntu SSO account.
    * The snapcraft key must have been previously created by the current Linux user (with "snapcraft create-key").
    * The key must have been registered to an Ubuntu SSO Account account that has the authority to sign System-User Assertions accoding to the Model Assertion whose name you specify (see blelow), or the System User cannot be created later at run time. This Ubuntu SSO Account can be the Brand account or another, if so delegated in the Model Assertion.
    * You must enter the login credentials for the Ubuntu SSO Account whose registered key is used to sign the System-User Assertion.
    * You must provide an authentication method for the System User to login later with. This can be either a password or a public SSH key, as described below.
    * It is good practice to use an "until" time that is in the near future (See below).

    On success, an "auto-import.assert" file is created in the current directory. If this file is placed on a USB drive and it is inserted into an Ubuntu Core system, and if the system has neither a System User nor a user created through console-conf, then the System User is created with SSH access using the specified authentication.'''
        ))
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')
    parser.add_argument('-w', '--write', dest='write', action='store_true', help=argparse.SUPPRESS)
    required = parser.add_argument_group('Required arguments')
    required.add_argument('-b', '--brand', required=True,
        help=('The account-id of the account that signed the device\'s model-assertion.')
        )
    required.add_argument('-m', '--model', required=True,
        help=('The model listed in the  device\'s model-assertion.')
        )
    required.add_argument('-u', '--username', required=True,
        help=('The username of the account to be created on the device')
        )
    required.add_argument('-e', '--email', required=True,
        help=('The email address of the login.ubuntu.com account to be created on the device.')
        )
    parser.add_argument('-p', '--password', 
        help=('The password of the account to be created on the device. This password is not saved. Either this or --ssh-keys is required.')
        )
    parser.add_argument('--until', 
        help=('Optionally specify the date until which the system user can be created in the following format: YYYY:MM:DD, for example "2021:02:28" for 28 Feb 2020. If omitted, the value is one year from the "since" date, which is two days before today.')
        )
    parser.add_argument('--serials', nargs='+',  
        help=('Optionally add one or more serial numbers to limit creation of a system-user to a system of one of the specified serial numbers. Use a space to delimit them. For example: --serial-numbers \'123abc\' \'zyx321abc\'.')
        )
    parser.add_argument('-f', '--force-password-change', 
        default=False,
        action="store_true",
        help=('Force the user to change the password on first use. --password flag required.')
        )
    parser.add_argument('-s', '--ssh-keys', nargs="+",
        help=('Optionally add one or more public ssh keys to use for SSH using the system user to be created on the device. Either this or --password is required. Enclosed each key string in single quotes. Use a space to delimit them. For example: --ssh-keys \'key one\' \'key two\'.')
        )
    required.add_argument('-k', '--key', required=True,
        help=('The name of the snapcraft key to use to sign the system user assertion. The key must exist locally and be reported by "snapcraft keys". The key must also be registered.')
        )
    args = parser.parse_args()
    return args

def get_macaroon():
    authClient = http_clients.UbuntuOneAuthClient()

    # get macaroon for account

    url = "https://dashboard.snapcraft.io/dev/api/acl/"
    data = {"permissions":[
                "package_access",
                "package_manage",
                "package_push",
                "package_register",
                "package_release",
                "package_update",
            ]}

    # getting macaroon can only be anonymous, so no auth client
    response = requests.request(
        "POST",
        url,
        data=json.dumps(data),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    if not response.ok:
        print('Error getting macaroon')
        print(response.text)
        exit_msg(1)

    return response.json()["macaroon"]


def ssoAccount(args):
    _macaroon = get_macaroon()
    _email = input("Ubuntu SSO email address: ")
    _password = getpass.getpass("Password: ")
    _otp = input("Second-factor auth: ")

    authClient = http_clients.UbuntuOneAuthClient()

    try:
        if len(_otp) == 0:
           authClient.login(_email, _password, _macaroon)
        else:
           authClient.login(_email, _password, _macaroon, _otp)

    except:
        print("Error: Your login did not succeed")
        return False

    # get account info
    url = "https://dashboard.snapcraft.io/dev/api/account"
    headers = str
    response = authClient.request(
        "GET",
        url,
        headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": authClient.auth},
    )

    if not response.ok:
        print('Error getting account info')
        print(response.text)
        exit_msg(1)

    if args.write: 
        f = open("out.json", "w")
        f.write(json.dumps(response.json(), indent=2))
        f.close()
    return response.json()

def pword_hash(pword):
    return crypt.crypt(pword, crypt.mksalt(crypt.METHOD_SHA512))                                                 
def key_fingerprint(key, account):    
    # ensure store reports key
    if len(account['account_keys']) > 0:
        for k in account['account_keys']:
            if k['name'] == key:
                return k['public-key-sha3-384']
    print("Error: key '{}' is not reported by the store as one of your registered and local keys. Please use snapcraft create-key KEY' or 'snapcraft register-key KEY' and 'snapcraft keys' as needed".format(key))
    return False

def accountAssert(id):
    cmd = ['snap', 'known', '--remote', 'account', 'account-id={}'.format(id)]
    res = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    signed = str(res,'utf-8')
    if "type: account\n" not in signed:
        print("Error: problems getting assertion for this account")
        return False 
    return(signed)

def accountKeyAssert(id):
    cmd = ['snap', 'known', '--remote', 'account-key', 'public-key-sha3-384={}'.format(id)]
    res = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    signed = str(res,'utf-8')
    if "type: account-key\n" not in signed:
        print("Error: problems getting assertion for this account-key")
        return False
    return(signed)

def getUntil(argsuntil, dt, d, t):
    if argsuntil is None:
        d = dt.replace(year = dt.year + 1).strftime('%Y-%m-%d')
        try:
            dt.replace(year = dt.year + 1)
        except ValueError: #if not a valid day, get the next day
            dt = dt + (date(dt.year + 1, 1, 1) - date(dt.year, 1, 1))
        until = d + 'T' + t + '-00:00'
    else:
        print("until is", argsuntil)
        y = argsuntil.split(":")[0]
        m = argsuntil.split(":")[1]
        dy = argsuntil.split(":")[2]
        dt1 = dt.replace(year = int(y))
        dt2 = dt1.replace(month = int(m))
        dt3 = dt2.replace(day = int(dy))
        d2 = dt3.strftime('%Y-%m-%d')
        until = d2 + 'T00:00:00-00:01'
    return(until)

def systemUserJson(account, brand, model, username, until, email):
    data = dict()
    data["type"] = "system-user"
    data["authority-id"] = account
    data["brand-id"] = brand
    data["series"] = ["16"]
    data["models"] = [model]
    data["name"] = username + " User"
    data["username"] = username
    data["email"] = email
    data["revision"] = "1"

    ts = time.time()
    dt = datetime.fromtimestamp(ts)
    dt = dt - timedelta(days=2)   
    d = dt.strftime('%Y-%m-%d')
    t = dt.strftime('%H:%M:%S')
    since = d + 'T00:00:00-00:01'
    data["since"] = since 
    data["until"] = getUntil(until, dt, d, t)
    if data["until"] == None:
        print("Error: until value setting failed")
        exit_msg(1)
    y = data["until"].split("-")[0]
    m = data["until"].split("-")[1]
    dy = data["until"].split("-")[2].split("T")[0]
    untildt = datetime(int(y), int(m), int(dy), 0, 0, 0, 0)
    if dt >= untildt:
        print("Error: until date is not after since date")
        print("since", data["since"])
        print("until", data["until"])
        exit_msg(1)
    return data

def isLocalKey(key):
    cmd = ['snap', 'keys']
    res = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    lines = str(res,'utf-8').split('\n')
    for line in lines:
        if key in line:
            return True
    print("Error: key '{}' is not a local key. Please use snapcraft create-key' and then 'snapcraft register-key'".format(key))
    return False

def signUser(userJson, key):
    cmd = "echo '" + json.dumps(userJson) + "'| snap sign -k " + key
    res = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]
    signed = str(res,'utf-8')
    return(signed)

def main(argv=None):
    args = parseargs(argv)
    if args.password is None and args.ssh_keys is None:
        print("Error. You must supply either a password or public SSH keys(s).")
        exit_msg(1)
    if args.password is not None and args.ssh_keys is not None:
        print("Error. You cannot use both a password and an ssh key.")
        exit_msg(1)
    if args.force_password_change and args.password is None:
        print("Error. Using --force-password-change also requires --password.")
        exit_msg(1)
    if args.force_password_change and args.ssh_keys is not None:
        print("Error. Using --force-password-change with --ssh-keys is not allowed.")
        exit_msg(1)

    # quit if not snapcraft logged in
    account = ssoAccount(args)
    if not account:
        exit_msg(1)
    # quit if key is not registered
    selfSignKey = key_fingerprint(args.key, account)
    if not selfSignKey:
        exit_msg(1)
    # quit if key does is not local
    if not isLocalKey(args.key):
        exit_msg(1)

    if args.verbose:
        print("==== Args and related:")
        print("Version: ", VERSION)
        print("Brand ", args.brand)
        print("Model", args.model)
        print("Username", args.username)
        print("Password", args.password)
        print("Email", args.email)
        print("SSH", args.ssh_keys)
        print("ForcePasswordChange", args.force_password_change)
        print("Account-Id: ", json.dumps(account, sort_keys=True, indent=4))
        print("Key: ", args.key)
        print("Key Fingerprint: ", selfSignKey)
        print("")

    accountSigned = accountAssert(account['account_id']) 
    if args.verbose:
        print("==== Account signed:")
        print(accountSigned)

    accountKeySigned = accountKeyAssert(selfSignKey) 
    if args.verbose:
        print("==== Account Key signed:")
        print(accountKeySigned)
    
    userJson = systemUserJson(account['account_id'], args.brand, args.model, args.username, args.until, args.email)
    if args.password:
        userJson["password"] = pword_hash(args.password)
        if args.force_password_change:
            userJson["force-password-change"] = "true"
    else: #ssh pub key
        userJson["ssh-keys"] = args.ssh_keys

    if args.serials:
        userJson["format"] = "1";
        userJson["serials"] = args.serials

    if args.verbose:
        print("==== system-user json:")
        print(json.dumps(userJson, sort_keys=True, indent=4))
    
    userSigned = signUser(userJson, args.key)

    user = accountSigned + "\n" + accountKeySigned + "\n" + userSigned
    if args.verbose:
        print("==== System-user signed:")
        print(user)

    filename = "auto-import.assert"
    with open(filename, 'w') as out:
        out.write(user)

    print("Done. You may copy {} to a USB stick and insert it into an unmanaged Core system, after which you can log in using the credentials you provided.".format(filename))
    exit_msg(0)

def exit_msg(status):
    print("\nNOTE: You may have been logged out of snapcraft. Please log back in with 'snapcraft login'")
    if status == 0:
        print("\nExiting.")
        sys.exit(0)
    else:
        print("Exiting with an error condition.")
        sys.exit(status)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
