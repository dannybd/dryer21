
import bitcoin

def send(fromprivkey, toaddr, value):
    transaction_fee = 20000
    print "Sending:", fromprivkey, toaddr, value
    tx = bitcoin.mksend(bitcoin.history(bitcoin.privtoaddr(fromprivkey)), [toaddr+":"+str(value)], bitcoin.privtoaddr(fromprivkey), transaction_fee)
    signed_tx = bitcoin.sign(tx, 0, fromprivkey)
    bitcoin.pushtx(signed_tx)

privkey, toaddr, value = "8b2b8ee26bd4e7ff5ddc64fe4977c595aacdfa42699eea2c8eaa56fe3fdb6602", "1CTcYRJBCC3WLaWJJPp2HA6dRNkmpQ8R2Y", 15000
send(privkey, toaddr, value)

