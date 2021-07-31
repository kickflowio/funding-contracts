# Matching Round

The Matching Round contract handles the logic for Kickflow's Quadratic Funding rounds. It accepts sponsor funds, projects entries, records contributions made to the CLR match, and allows entries to withdraw their match payout.

## Storage

- `round_event_timestamps` : Contains the timestamps of relevant events across the round.
  - `contribution_start` : Timestamp after which the contributions can be accepted by the Matching Round contract.
  - `contribution_end` : Timestamp after which contributions are no longer accepted by the Matching Round contract.
  - `cooldown_period_end` : Timestamp at which cooldown period ends.
  - `challenge_period_end` : Timestamp at which clr match challenge period ends.
- `round_meta` : Miscellaneous data associated to the round
  - `token_set` : A set of bytes value representing the tokens being accepted in the round.
  - `security_deposit_amount`: Mandatory security deposit to be paid by the entries in tez.
  - `dao_address`: The Tezos address of the DAO contract.
  - `stablecoin_address`: The address of the stablecoin being accepted from sponsors.
  - `donation_handler_address`: Tezos address of the Donation Handler contract.
  - `community_fund_address`: Tezos address of the Community Fund contract.
- `entries` : A `BIGMAP` mapping from a unique id to a project of type ENTRY_TYPE as described in [types/entry.py](https://github.com/kickflowio/funding-contracts/blob/master/types/entry.py)
- `contributions` : A `BIGMAP` mapping from a `PAIR` of contributor address & project-id to a `PAIR` of token identifier bytes and donation value.
- `entry_address_to_id` : A `BIGMAP` mapping from entry address to its unique id.
- `sponsors` : A `MAP` mapping from sponsors tezos address to the sponsored amount.
- `total_sponsored_amount` : The total value of funds in the sponsor pool.
- `matches_set` : A `BOOL` that is set to true when the CLR matches are set by the DAO.

## Entrypoints

- `sponsor` : Accepts the sponsored amount in the specified stablecoin.
- `enter_round` : Called by projects in order to register themselves to the round by paying a refundable security deposit.
- `contribute` : Called by the Donation Handler to record the details of a contributon.
- `disqualify_entries` : Called by the DAO to disqualify entries that appeared to have gamed with the system.
- `set_clr_matches` : Called by the DAO to set the matches of the individual projects.
- `withdraw_match` : Allows entries to withdraw their clr matches.
- `withdraw_deposit` : Allows entries to witdraw their security deposit, considering the entry is not disqualified.

## Timeline

| Event                                                 | Start                                        | End                                |
| ----------------------------------------------------- | -------------------------------------------- | ---------------------------------- |
| Sponsor collection and project entry to funding round | Approval of the round in the DAO             | **contribution_start** timestamp   |
| Contribution to the CLR match                         | **contribution_start** timestamp             | **contribution_end** timestamp     |
| Cooldown period                                       | **contribution_end** timestamp               | **cooldown_period_end** timestamp  |
| Setting of CLR match by the DAO                       | Anytime after cooldown period has ended      | -                                  |
| Challenge of CLR match                                | From the time the matches are set by the DAO | **challenge_period_end** timestamp |
| Withdrawal of match by the entries                    | **challenge_period_end** timestamp           | -                                  |
