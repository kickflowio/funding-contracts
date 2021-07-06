import smartpy as sp

# Type of contributions: token identifier bytes => List of contribution values
CONTRIBUTION_TYPE = sp.TMap(sp.TBytes, sp.TList(sp.TNat))

# Type of a matching round entry
# Params:
#   address           : The payout address of the entry, where donations and match amount is sent
#   creator           : Address of the creator of the entry
#   status            : The current status of the entry
#   contributions     : A mapping from token identifier BYTES => NAT list of contributions
#   contributors      : A set of addresses who contributed to the project
#   clr_match         : The final match to be collected by the entry. Could be 0.
#   deposit_withdrawn : True when the entry has withdrawn the security deposit
ENTRY_TYPE = sp.TRecord(
    address=sp.TAddress,
    creator=sp.TAddress,
    status=sp.TNat,
    contributions=CONTRIBUTION_TYPE,
    contributors=sp.TSet(sp.TAddress),
    clr_match=sp.TNat,
    deposit_withdrawn=sp.TBool,
).layout(
    (
        "address",
        (
            "creator",
            (
                "status",
                (
                    "contributions",
                    (
                        "contributors",
                        (
                            "clr_match",
                            "deposit_withdrawn",
                        ),
                    ),
                ),
            ),
        ),
    )
)

#########
# Status
#########

# The entry is active and collecting community contributions
ENTRY_STATUS_ACTIVE = 0
# The entry is disqualified by the DAO
ENTRY_STATUS_DISQUALIFIED = 1
# Entry has withdrawn its match
ENTRY_STATUS_CLOSED = 2
