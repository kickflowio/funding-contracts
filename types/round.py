import smartpy as sp

ROUND_EVENT_TIMESTAMPS_TYPE = sp.TRecord(
    contribution_start=sp.TTimestamp,
    contribution_end=sp.TTimestamp,
    cooldown_period_end=sp.TTimestamp,
    challenge_period_end=sp.TTimestamp,
    withdrawal_period_end=sp.TTimestamp,
)

ROUND_META_TYPE = sp.TRecord(
    token_set=sp.TSet(sp.TBytes),
    security_deposit_amount=sp.TMutez,
    dao_address=sp.TAddress,
    stablecoin_address=sp.TAddress,
    donation_handler_address=sp.TAddress,
)
