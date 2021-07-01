import smartpy as sp


class DummyRound(sp.Contract):
    def __init__(self):
        self.init()

    @sp.entry_point
    def default(self):
        pass

    @sp.entry_point
    def contribute(self, params):
        sp.set_type(
            params,
            sp.TRecord(
                from_=sp.TAddress, project_address=sp.TAddress, identifier=sp.TBytes, value=sp.TNat
            ),
        )
        pass
