import urllib, urllib2
import json, base64
import os, time
from sys import stdout
printf = stdout.write

BASE_URL = 'http://dannybd.mit.edu/6.858/'
n = None
e = None
k0 = None
k1 = None
token = None
nonce = None

def get_crypto_vars():
    url = BASE_URL + 'get_crypto_vars.php'
    response = urllib2.urlopen(url)
    data = json.load(response)
    return (data['n'], data['e'], data['k0'], data['k1'])

def gen_token(n, e, k0, k1):
    x = base64.b64encode(os.urandom(256))
    m = x # in reality, OAEP(H(k0, x), H(k1, x) + x)
    r = base64.b64encode(os.urandom(256))
    token = m # in reality, m*r^e mod n
    return (m, r)

def send_token(token):
    url = BASE_URL + 'send_token.php'
    data = urllib.urlencode({'token': token})
    response = urllib2.urlopen(url, data)
    return json.load(response)

def fetch_bit_price_and_addr(token):
    data = send_token(token)
    if 'error' in data:
        print 'Error occurred fetching price and addr:', data['error']
        return (None, None)
    return (data['price'], data['addr'])

def fetch_proto_bond(token):
    url = BASE_URL + 'gen_bond.php'
    data = urllib.urlencode({'token': token})
    response = urllib2.urlopen(url, data)
    return json.load(response)

def try_fetch_proto_bond(token):
    data = fetch_proto_bond(token)
    if 'bond' in data:
        return data['bond']
    return None

def gen_bond(proto_bond):
    global nonce
    #use nonce to decrypt proto_bond --> bond
    destroy_nonce()
    return proto_bond[::-1]

def destroy_nonce():
    global nonce
    nonce = base64.b64encode(os.urandom(256))
    nonce = None
    del nonce

def gen_bond_filename():
    hashstr = base64.b16encode(os.urandom(16))
    return hashstr + '.bond'

def horiz_line():
    print "=================================================="

def interface():
    print "\n" * 100
    print
    print "##################################################"
    print "#             DRYER 21 PYTHON SCRIPT             #"
    print "#             by asuhl, snp, dannybd             #"
    print "##################################################"
    print
    print "Hello, and welcome to the Dryer 21 Python script!"
    print
    printf("Connecting to Dryer 21 server.................")

    global n, e, k0, k1
    (n, e, k0, k1) = get_crypto_vars()

    print "DONE"
    printf("Generating token..............................")

    global token, nonce
    (token, nonce) = gen_token(n, e, k0, k1)

    print "DONE"
    print
    print "Please copy the following token into your browser:"
    print token
    horiz_line()
    print "Type 'c' to continue, or 'p' to submit via Python."
    user_input = raw_input('(c or p, then Enter) > ')
    while len(user_input) < 1 or user_input[0] not in 'cp':
        print
        print "Sorry, that's not a valid entry."
        print "Type 'c' to continue, or 'p' to submit via Python."
        user_input = raw_input('(c or p, then Enter) > ')
    print
    if user_input == 'c':
        interface_wait_for_proto_bond()
    elif user_input == 'p':
        interface_auto_submit()

def interface_wait_for_proto_bond():
    print "Paste the text from Step 4 below, and press Enter:"
    horiz_line()
    proto_bond = raw_input()
    horiz_line()
    print
    interface_gen_bond(proto_bond)

def interface_auto_submit():
    printf("Sending token to server.......................")

    global token
    (price, addr) = fetch_bit_price_and_addr(token)

    print "DONE"
    print
    print "Now, please send " + price + "to this address:"
    print addr
    horiz_line()
    print
    
    check_period = 10
    proto_bond = try_fetch_proto_bond(token)
    while proto_bond == None:
        printf("Checking transaction status...")
        for i in range(check_period):
            time.sleep(1)
            printf(".")
        proto_bond = try_fetch_proto_bond(token)
        print
    print
    print "Transaction cleared!"
    horiz_line()
    print
    interface_gen_bond(proto_bond)
    
    

def interface_gen_bond(proto_bond):
    printf("Generating bond...............................")

    bond = gen_bond(proto_bond)

    print "DONE"
    printf("Saving bond...................................")

    filename = gen_bond_filename()
    with open(filename, 'w+') as f:
        f.write(bond)

    print "DONE"
    print
    horiz_line()
    print "Congrats! You have successfully generated a bond."
    print "It has been stored at this path:"
    print os.path.abspath('.') + '\\' + filename
    print
    print "Remember to wait a few days before trying to cash"
    print "in your bond for 0.1BTC."
    print
    print


interface()


# (n, e, k0, k1) = get_crypto_vars()
# token = gen_token(n, e, k0, k1)
# (price, addr) = get_bit_price_and_addr(token)
