##########
# Generic
##########

# Only DAO is allowed to go through
ONLY_DAO_ALLOWED = "ONLY_DAO_ALLOWED"

# Generic not allowed
NOT_ALLOWED = "NOT_ALLOWED"

###################
# Donation Handler
###################

# Round is not active right now
NO_ROUND_IS_ACTIVE = "NO_ROUND_IS_ACTIVE"

# Given round contract is not valid
INVALID_ROUND_CONTRACT = "INVALID_ROUND_CONTRACT"

# The token identifier bytes do not resolve to a valid address
INVALID_IDENTIFIER_BYTES = "INVALID_IDENTIFIER_BYTES"

# TOken resolved from the identifier bytes is invalid
INVALID_TOKEN_CONTRACT = "INVALID_TOKEN_CONTRACT"

# The whitelist contract address is invalid
INVALID_WHITELIST = "INVALID_WHITELIST"

# Incorrect value parameter in donate
INCORRECT_VALUE_PARAMETER = "INCORRECT_VALUE_PARAMETER"

# The value of donation is zero
ZERO_DONATION_NOT_ALLOWED = "ZERO_DONATION_NOT_ALLOWED"

#################
# Matching Round
#################

# The sender is already a sponsor
ALREADY_SPONSORED = "ALREADY_SPONSORED"

# Zero value can't be offered for sponsorship
ZERO_VALUE_NOT_ALLOWED = "ZERO_VALUE_NOT_ALLOWED"

# Sponsorship period is over
NOT_ACCEPTING_SPONSORS = "NOT_ACCEPTING_SPONSORS"

# Entry is already in the round
ALREADY_IN_ROUND = "ALREADY_IN_ROUND"

# Entry period is over
ENTRY_PERIOD_OVER = "ENTRY_PERIOD_OVER"

# Invalid security deposit amount
INVALID_SECURITY_DEPOSIT = "INVALID_SECURITY_DEPOSIT"

# provided stablecoin address is invalid
INVALID_STABLECOIN = "INVALID_STABLECOIN"

# The entry address provided is not in the round
INVALID_ENTRY_ADDRESS = "INVALID_ENTRY_ADDRESS"

# Not the correct period for contributions
NOT_ACCEPTING_CONTRIBUTIONS = "NOT_ACCEPTING_CONTRIBUTIONS"

# The entry is not in the active state
ENTRY_NOT_ACTIVE = "ENTRY_NOT_ACTIVE"

# Sender has already contributed to the project
ALREADY_CONTRIBUTED = "ALREADY_CONTRBUTED"

# Project creator is self contributing
SELF_CONTRIBUTION_NOT_ALLOWED = "SELF_CONTRIBUTION_NOT_ALLOWED"

# The given token identifier is not present in the token set
INVALID_TOKEN_IDENTIFIER = "INVALID_TOKEN_IDENTIFIER"

# Can not disqualify the entries since the cooldown period is over
COOLDOWN_PERIOD_OVER = "COOLDOWN_PERIOD_OVER"

# The entry is already disqualified
ENTRY_ALREADY_DISQUALIFIED = "ENTRY_ALREADY_DISQUALIFIED"

# The cooldown period is not over yet
COOLDOWN_NOT_OVER = "COOLDOWN_NOT_OVER"

# The period to set and challenge CLR is over
CHALLENGE_PERIOD_OVER = "CLR_SETTING_PERIOD_OVER"

# Challenge period is still on
CHALLENGE_PERIOD_ONGOING = "CHALLENGE_PERIOD_ONGOING"

# Matches haven't been set yet
MATCHES_NOT_SET = "MATCHES_NOT_SET"

# The entry has a zero match
ZERO_CLR_MATCH = "ZERO_CLR_MATCH"

# The entry is disqualified
ENTRY_DISQUALIFIED = "ENTRY_DISQUALIFIED"

# Entry has already withdrawn the deposit
DEPOSIT_ALREADY_WITHDRAWN = "DEPOSIT_ALREADY_WITHDRAWN"

############
# Whitelist
############

# Address is not in the whitelist
ADDRESS_NOT_WHITELISTED = "ADDRESS_NOT_WHITELISTED"

# No admin has been proposed for the contract
NO_ADMIN_PROPOSED = "NO_ADMIN_PROPOSED"

# The given address is not whitelisted
ADDRESS_NOT_WHITELISTED = "ADDRESS_NOT_WHITELISTED"
