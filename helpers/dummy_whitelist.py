import smartpy as sp


class DummyWhitelist(sp.Contract):
    def __init__(self, val):
        self.init(val=val)

    @sp.entry_point
    def default(self):
        pass

    @sp.entry_point
    def verify_whitelisted(self, address):
        sp.set_type(address, sp.TAddress)
        sp.verify(self.data.val, "ADDRESS_NOT_WHITELISTED")
