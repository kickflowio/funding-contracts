import smartpy as sp

# The timestamps of the varying periods of a round
# Params:
#   contribution_start    : Timestamp after the entries can start accepting contributions
#   contribution_end      : Timestamp post which the entries can not accept contributions
#   cooldown_period_end   : Timestamp when cooldown period ends. During cooldown contributions can
#                           be assessed and dubious entries could be disqualified.
#   challenge_period      : Timestamp when challenge period ends. During challenge period, the
#                           CLR matches set by the DAO can be challenged and set again.
ROUND_EVENT_TIMESTAMPS_TYPE = sp.TRecord(
    contribution_start=sp.TTimestamp,
    contribution_end=sp.TTimestamp,
    cooldown_period_end=sp.TTimestamp,
    challenge_period_end=sp.TTimestamp,
).layout(
    (
        "contribution_start",
        (
            "contribution_end",
            (
                "cooldown_period_end",
                "challenge_period_end",
            ),
        ),
    )
)

# Pre-set constants holding some of the metadata governing a round
# Params:
#   token_set                 : A set of BYTES type holding packed values of the addresses of tokens
#                               being accepted in a round.
#   security_deposit_amount   : Mandatory security deposit to be given by the entries in tez.
#   stablecoin_address        : Address of the stablecoin in which sponsored amount is accepted.
#   donation_handler_address  : Address of the donation handler contract that relays donations.
#   community_fund_address    : Address of the community fund managed by the DAO.
#
#   NOTE: For tez, the token_set BYTES value is- packed value of string "TEZOS_IDENTIFIER"
ROUND_META_TYPE = sp.TRecord(
    token_set=sp.TSet(sp.TBytes),
    security_deposit_amount=sp.TMutez,
    stablecoin_address=sp.TAddress,
    donation_handler_address=sp.TAddress,
    community_fund_address=sp.TAddress,
).layout(
    (
        "token_set",
        (
            "security_deposit_amount",
            (
                "stablecoin_address",
                (
                    "donation_handler_address",
                    "community_fund_address",
                ),
            ),
        ),
    )
)
