#!/usr/bin/python3

import os
import sys
import argparse
import subprocess
import crypt
import json
import time
import datetime
import json
from snapcraft import storeapi

PROGRAM = 'make-system-user-assertion'
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
    required.add_argument('-p', '--password', required=True,
        help=('The password of the account to be created on the device.i This password is not saved')
        )
    required.add_argument('-k', '--key', required=True,
        help=('The name of the snapcraft key to use to sign the system user assertion. The key must exist locally and be reported by "snapcraft keys". The key must also be registered.')
        )
    args = parser.parse_args()
    return args

def ssoAccountId():
    try:
        store = storeapi.StoreClient()
        account_info = store.get_account_information()
        return account_info['account_id']
    except:
        print("Error: You do not appear to be logged in. Try 'snapcraft login'")
        return False

def pword_hash(pword):
    return crypt.crypt(pword, crypt.mksalt(crypt.METHOD_SHA512))                                                 

def key_fingerprint(key):    
    cmd = ['snapcraft', 'keys']
    res = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    resStr = str(res,'utf-8')
    lines=resStr.split('\n')
    for line in lines:
        if not line.startswith('*'): #exclude non-registered keys
            continue
        tokens = line.split()
        if tokens[1].strip() == key:
            return tokens[2]
    print("Error: key '{}' is not found or is not registered. Please use 'snapcraft keys' to verify your key exists and is registered.".format(key))
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

def systemUserJson(account, brand, model, username, pwhash):
    data = dict()
    data["type"] = "system-user"
    data["authority-id"] = account
    data["brand-id"] = brand
    data["series"] = ["16"]
    data["models"] = [model]
    data["name"] = username + " User"
    data["username"] = username
    data["password"] = pwhash
    data["email"] = "{}@localhost".format(username)
    data["revision"] = "1"

    ts = time.time()
    dt = datetime.datetime.fromtimestamp(ts)
    d = dt.strftime('%Y-%m-%d')
    t = dt.strftime('%H:%M:%S')
    since = d + 'T' + t + '-00:00'
    data["since"] = since 
    d = dt.replace(year = dt.year + 1).strftime('%Y-%m-%d')
    try:
        dt.replace(year = dt.year + 1)
    except ValueError: #if not a valid day, get the next day
        dt = dt + (date(dt.year + 1, 1, 1) - date(dt.year, 1, 1))
    until = d + 'T' + t + '-00:00'
    data["until"] = until 
    return data

def signUser(userJson, key):
    cmd = "echo '" + json.dumps(userJson) + "'| snap sign -k " + key
    res = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]
    signed = str(res,'utf-8')
    return(signed)

def main(argv=None):
    args = parseargs(argv)
    # quit if not snapcraft logged in
    account = ssoAccountId()
    if not account:
        sys.exit(1)
    # quit if key does not exist or is not registered
    selfSignKey = key_fingerprint(args.key)
    if not selfSignKey:
        sys.exit(1)

    if args.verbose:
        print("Version: ", VERSION)
        print("Brand ", args.brand)
        print("Model", args.model)
        print("Username", args.username)
        print("Password", args.password)
        print("Password hash", pword_hash(args.password))
        print("Account-Id: ", account)
        print("Key: ", args.key)
        print("Key Fingerprint: ", selfSignKey)

    accountSigned = accountAssert(account) 
    if args.verbose:
        print("Account signed:")
        print(accountSigned)

    accountKeySigned = accountKeyAssert(selfSignKey) 
    if args.verbose:
        print("Account Key signed:")
        print(accountKeySigned)
    
    userJson = systemUserJson(account, args.brand, args.model, args.username, pword_hash(args.password))
    if args.verbose:
        print("system-user json:")
        print(json.dumps(userJson))
    
    userSigned = signUser(userJson, args.key)

    user = accountSigned + "\n" + accountKeySigned + "\n" + userSigned
    if args.verbose:
        print("system-user signed:")
        print(user)

    filename = "auto-import.assert"
    with open(filename, 'w') as out:
        out.write(user)

    print("Done. You may copy {} to a USB stick and insert it into an unmanaged Core system, after which you can log in using the username and password you provided.".format(filename))

    return 0

if __name__ == '__main__':
    sys.exit(main())
