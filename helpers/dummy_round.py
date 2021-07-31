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
                from_=sp.TAddress,
                entry_address=sp.TAddress,
                token_identifier=sp.TBytes,
                value=sp.TNat,
            ).layout(
                (
                    "from_",
                    (
                        "entry_address",
                        ("token_identifier", "value"),
                    ),
                ),
            ),
        )
        pass
