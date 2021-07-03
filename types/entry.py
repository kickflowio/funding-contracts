import smartpy as sp

# Type of contributions: token identifier bytes => List of contribution values
CONTRIBUTION_TYPE = sp.TMap(sp.TBytes, sp.TList(sp.TNat))

# Type of a matching round project entry
ENTRY_TYPE = sp.TRecord(
    address=sp.TAddress,
    creator=sp.TAddress,
    status=sp.TNat,
    contributions=CONTRIBUTION_TYPE,
    contributors=sp.TSet(sp.TAddress),
    clr_match_ratio=sp.TNat,
    deposit_withdrawn=sp.TBool,
)

#########
# Status
#########

ENTRY_STATUS_ACTIVE = 0
ENTRY_STATUS_DISQUALIFIED = 1
# Entry has withdrawn its match
ENTRY_STATUS_CLOSED = 2
