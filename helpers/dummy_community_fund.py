import smartpy as sp


class DummyCommunityFund(sp.Contract):
    def __init__(self):
        self.init()

    @sp.entry_point
    def default(self):
        pass
