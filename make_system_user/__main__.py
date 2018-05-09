"""
Copyright (C) 2017 Canonical Ltd

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
import subprocess
import crypt
import json
import time
from datetime import datetime, timedelta
import json
from snapcraft import storeapi

PROGRAM = ''
VERSION = '0.1'

#TODO: arg help i18n'd

def parseargs(argv=None):
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=('Create a self-signed system-user assertion using a local snapcraft key that has been registered with an Ubuntu SSO account.'),
        )
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true'
        )
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
    parser.add_argument('-p', '--password', 
        help=('The password of the account to be created on the device. This password is not saved. Either this or --ssh-keys is required.')
        )
    parser.add_argument('-s', '--ssh-keys', nargs="+",
        help=('One or more public ssh keys to use for SSH using the system user to be created on the device. Either this or --password is required. Enclosed each key string in single quotes. Use a space to delimit them. For example: --ssh-key \'key one\' \'key two\'.')
        )
    required.add_argument('-k', '--key', required=True,
        help=('The name of the snapcraft key to use to sign the system user assertion. The key must exist locally and be reported by "snapcraft keys". The key must also be registered.')
        )
    args = parser.parse_args()
    return args

def ssoAccount():
    try:
        store = storeapi.StoreClient()
        return store.get_account_information()
    except:
        print("Error: You do not appear to be logged in. Try 'snapcraft login'")
        return False

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

def systemUserJson(account, brand, model, username):
    data = dict()
    data["type"] = "system-user"
    data["authority-id"] = account
    data["brand-id"] = brand
    data["series"] = ["16"]
    data["models"] = [model]
    data["name"] = username + " User"
    data["username"] = username
    data["email"] = "{}@localhost".format(username)
    data["revision"] = "1"

    ts = time.time()
    dt = datetime.fromtimestamp(ts)
    dt = dt - timedelta(days=2)   
    d = dt.strftime('%Y-%m-%d')
    t = dt.strftime('%H:%M:%S')
    since = d + 'T00:00:00-00:01'
    data["since"] = since 
    d = dt.replace(year = dt.year + 1).strftime('%Y-%m-%d')
    try:
        dt.replace(year = dt.year + 1)
    except ValueError: #if not a valid day, get the next day
        dt = dt + (date(dt.year + 1, 1, 1) - date(dt.year, 1, 1))
    until = d + 'T' + t + '-00:00'
    data["until"] = until 
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
    if argv is None:
        argv = sys.argv
    PROGRAM = argv[0]
    args = parseargs(argv)
    if args.password is None and args.ssh_keys is None:
        print("Error. You must supply either a password or public SSH keys(s)")
        sys.exit(1)

    # quit if not snapcraft logged in
    account = ssoAccount()
    if not account:
        sys.exit(1)
    # quit if key is not registered
    selfSignKey = key_fingerprint(args.key, account)
    if not selfSignKey:
        sys.exit(1)
    # quit if key does is not local
    if not isLocalKey(args.key):
        sys.exit(1)

    if args.verbose:
        print("==== Args and related:")
        print("Version: ", VERSION)
        print("Brand ", args.brand)
        print("Model", args.model)
        print("Username", args.username)
        print("Password", args.password)
        print("SSH", args.ssh_keys)
        print("Password", args.password)
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
    
    userJson = systemUserJson(account['account_id'], args.brand, args.model, args.username )
    if args.password:
        userJson["password"] = pword_hash(args.password)
    else: #ssh pub key
        userJson["ssh-keys"] = args.ssh_keys
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

    print("Done. You may copy {} to a USB stick and insert it into an unmanaged Core system, after which you can log in using the username and password you provided.".format(filename))

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
