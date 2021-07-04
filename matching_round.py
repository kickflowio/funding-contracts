import smartpy as sp

Addresses = sp.io.import_script_from_url("file:helpers/addresses.py")
DummyToken = sp.io.import_script_from_url("file:helpers/dummy_token.py")
DummyCommunityFund = sp.io.import_script_from_url("file:helpers/dummy_community_fund.py")
Errors = sp.io.import_script_from_url("file:types/errors.py")
Round = sp.io.import_script_from_url("file:types/round.py")
Entry = sp.io.import_script_from_url("file:types/entry.py")

############
# Constants
############

TEZOS_IDENTIFIER = sp.pack("TEZOS_IDENTIFIER")

SECURITY_DEPOSIT_AMOUNT = sp.tez(10)

# Seconds in a day
DAY = 86400

# Time contants
CONTRIBUTION_START = sp.timestamp(5)
CONTRIBUTION_PERIOD = 30 * DAY
COOLDOWN_PERIOD = 7 * DAY
CHALLENGE_PERIOD = 7 * DAY

#################
# Default values
#################

ROUND_EVENT_TIMESTAMPS = sp.record(
    contribution_start=CONTRIBUTION_START,
    contribution_end=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD),
    cooldown_period_end=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD),
    challenge_period_end=sp.timestamp(0),
)

ROUND_META = sp.record(
    token_set=sp.set([TEZOS_IDENTIFIER]),
    security_deposit_amount=SECURITY_DEPOSIT_AMOUNT,
    dao_address=Addresses.DAO,
    stablecoin_address=Addresses.STABLECOIN,
    donation_handler_address=Addresses.DONATION_HANDLER,
    community_fund_address=Addresses.COMMUNITY_FUND,
)

###########
# Contract
###########


class MatchingRound(sp.Contract):
    def __init__(
        self,
        round_event_timestamps=ROUND_EVENT_TIMESTAMPS,
        round_meta=ROUND_META,
        entries=sp.big_map(
            l={},
            tkey=sp.TNat,
            tvalue=Entry.ENTRY_TYPE,
        ),
        entry_address_to_id=sp.big_map(
            l={},
            tkey=sp.TAddress,
            tvalue=sp.TNat,
        ),
        sponsors=sp.map(
            l={},
            tkey=sp.TAddress,
            tvalue=sp.TNat,
        ),
        total_sponsored_amount=sp.nat(0),
        matches_set=sp.bool(False),
    ):
        self.init_type(
            sp.TRecord(
                round_event_timestamps=Round.ROUND_EVENT_TIMESTAMPS_TYPE,
                round_meta=Round.ROUND_META_TYPE,
                entries=sp.TBigMap(sp.TNat, Entry.ENTRY_TYPE),
                entry_address_to_id=sp.TBigMap(sp.TAddress, sp.TNat),
                sponsors=sp.TMap(sp.TAddress, sp.TNat),
                total_sponsored_amount=sp.TNat,
                uuid=sp.TNat,
                matches_set=sp.TBool,
            )
        )

        self.init(
            round_event_timestamps=round_event_timestamps,
            round_meta=round_meta,
            entries=entries,
            entry_address_to_id=entry_address_to_id,
            sponsors=sponsors,
            total_sponsored_amount=total_sponsored_amount,
            uuid=sp.nat(0),
            matches_set=matches_set,
        )

    @sp.entry_point
    def sponsor(self, value):
        sp.set_type(value, sp.TNat)

        # Verify that sender has not sponsored already
        sp.verify(~self.data.sponsors.contains(sp.sender), Errors.ALREADY_SPONSORED)

        # Verify that sponsored amount is greater than 0
        sp.verify(value > 0, Errors.ZERO_VALUE_NOT_ALLOWED)

        # Verify that sponsorship period is still active
        sp.verify(
            sp.now < self.data.round_event_timestamps.contribution_start,
            Errors.NOT_ACCEPTING_SPONSORS,
        )

        # Retrieve sponsored amount in mentioned stablecoin
        c = sp.contract(
            sp.TRecord(from_=sp.TAddress, to_=sp.TAddress, value=sp.TNat).layout(
                ("from_ as from", ("to_ as to", "value"))
            ),
            self.data.round_meta.stablecoin_address,
            "transfer",
        ).open_some()
        sp.transfer(sp.record(from_=sp.sender, to_=sp.self_address, value=value), sp.mutez(0), c)

        # Required storage updates
        self.data.sponsors[sp.sender] = value
        self.data.total_sponsored_amount += value

    @sp.entry_point
    def enter_round(self, address):
        sp.set_type(address, sp.TAddress)

        # Verify that entry is not in the round already
        sp.verify(~self.data.entry_address_to_id.contains(address), Errors.ALREADY_IN_ROUND)

        # Verify that timing is correct
        sp.verify(
            sp.now < self.data.round_event_timestamps.contribution_start, Errors.ENTRY_PERIOD_OVER
        )

        # Verify that sent amount equals the security deposit
        sp.verify(
            sp.amount == self.data.round_meta.security_deposit_amount,
            Errors.INVALID_SECURITY_DEPOSIT,
        )

        entry = sp.record(
            address=address,
            creator=sp.sender,
            status=Entry.ENTRY_STATUS_ACTIVE,
            contributions={},
            contributors=sp.set([]),
            clr_match=0,
            deposit_withdrawn=False,
        )

        # Insert entry into storage
        self.data.uuid += 1
        self.data.entries[self.data.uuid] = entry
        self.data.entry_address_to_id[address] = self.data.uuid

    @sp.entry_point
    def contribute(self, params):
        sp.set_type(
            params,
            sp.TRecord(
                from_=sp.TAddress,
                entry_address=sp.TAddress,
                token_identifier=sp.TBytes,
                value=sp.TNat,
            ),
        )

        # Verify that the sender is the donation handler
        sp.verify(sp.sender == self.data.round_meta.donation_handler_address, Errors.NOT_ALLOWED)

        # Verify that the entry exists
        sp.verify(
            self.data.entry_address_to_id.contains(params.entry_address),
            Errors.INVALID_ENTRY_ADDRESS,
        )

        timestamps = self.data.round_event_timestamps

        # Verify that contribution period is on-going
        sp.verify(
            (sp.now >= timestamps.contribution_start) & (sp.now < timestamps.contribution_end),
            Errors.NOT_ACCEPTING_CONTRIBUTIONS,
        )

        entry_id = self.data.entry_address_to_id[params.entry_address]
        entry = self.data.entries[entry_id]

        # Verify that entry is active i.e not disqualified
        sp.verify(entry.status == Entry.ENTRY_STATUS_ACTIVE, Errors.ENTRY_NOT_ACTIVE)

        # Verify that the contributor has not contributed already
        sp.verify(~entry.contributors.contains(params.from_), Errors.ALREADY_CONTRIBUTED)

        # Verify that it is not a self contribution
        sp.verify(
            (params.from_ != entry.address) & (params.from_ != entry.creator),
            Errors.SELF_CONTRIBUTION_NOT_ALLOWED,
        )

        # Verify that the token_identifier is accepted
        sp.verify(
            self.data.round_meta.token_set.contains(params.token_identifier),
            Errors.INVALID_TOKEN_IDENTIFIER,
        )

        # Insert contribution into the entry
        sp.if ~entry.contributions.contains(params.token_identifier):
            entry.contributions[params.token_identifier] = []
        entry.contributions[params.token_identifier].push(params.value)
        entry.contributors.add(params.from_)

    @sp.entry_point
    def disqualify_entries(self, entry_list):
        sp.set_type(entry_list, sp.TList(sp.TNat))

        # Verify that the sender is the DAO
        sp.verify(sp.sender == self.data.round_meta.dao_address, Errors.NOT_ALLOWED)

        # Verify that the timing is correct
        sp.verify(
            sp.now < self.data.round_event_timestamps.cooldown_period_end,
            Errors.COOLDOWN_PERIOD_OVER,
        )

        # Loop through the supplied entries and disqualify them
        sp.for entry_id in entry_list:
            # If entry is already disqualified then revert the operation
            sp.if self.data.entries[entry_id].status == Entry.ENTRY_STATUS_DISQUALIFIED:
                sp.failwith(Errors.ENTRY_ALREADY_DISQUALIFIED)
            self.data.entries[entry_id].status = Entry.ENTRY_STATUS_DISQUALIFIED

        # Transfer security deposit of the disqualified entries to the community-fund
        security_deposit_nat = sp.utils.mutez_to_nat(self.data.round_meta.security_deposit_amount)
        sp.send(
            self.data.round_meta.community_fund_address,
            sp.utils.nat_to_mutez(security_deposit_nat * sp.len(entry_list)),
        )

    @sp.entry_point
    def set_clr_matches(self, matches_map):
        sp.set_type(matches_map, sp.TMap(sp.TNat, sp.TNat))

        # Verify that sender is the DAO
        sp.verify(sp.sender == self.data.round_meta.dao_address, Errors.NOT_ALLOWED)

        sp.verify(
            sp.now > self.data.round_event_timestamps.cooldown_period_end, Errors.COOLDOWN_NOT_OVER
        )

        sp.if ~self.data.matches_set:
            # Set the challenge period end timestamp
            self.data.round_event_timestamps.challenge_period_end = sp.now.add_seconds(
                CHALLENGE_PERIOD
            )
            self.data.matches_set = True

        # Verify that the timing is correct
        sp.verify(
            sp.now < self.data.round_event_timestamps.challenge_period_end,
            Errors.CHALLENGE_PERIOD_OVER,
        )

        # Loop through the matches map and set the clr match
        sp.for entry_id in matches_map.keys():
            self.data.entries[entry_id].clr_match = matches_map[entry_id]

    @sp.entry_point
    def withdraw_match(self, address):
        sp.set_type(address, sp.TAddress)

        # Verify that entry address exists in the round
        sp.verify(self.data.entry_address_to_id.contains(address), Errors.INVALID_ENTRY_ADDRESS)

        entry_id = self.data.entry_address_to_id[address]
        entry = self.data.entries[entry_id]

        # Verify that the entry is still active (not disqualified or already retrieved match)
        sp.verify(entry.status == Entry.ENTRY_STATUS_ACTIVE, Errors.ENTRY_NOT_ACTIVE)

        # Verify that the matches have been set
        sp.verify(self.data.matches_set, Errors.MATCHES_NOT_SET)

        # Verify that timing is correct
        sp.verify(
            sp.now > self.data.round_event_timestamps.challenge_period_end,
            Errors.CHALLENGE_PERIOD_ONGOING,
        )

        # Verify that entry has a non-zero match
        sp.verify(entry.clr_match != 0, Errors.ZERO_CLR_MATCH)

        # Transfer the match to the entry address
        c = sp.contract(
            sp.TRecord(from_=sp.TAddress, to_=sp.TAddress, value=sp.TNat).layout(
                ("from_ as from", ("to_ as to", "value"))
            ),
            self.data.round_meta.stablecoin_address,
            "transfer",
        ).open_some()

        sp.transfer(
            sp.record(
                from_=sp.self_address,
                to_=entry.address,
                value=entry.clr_match,
            ),
            sp.tez(0),
            c,
        )

        # Set entry status to closed
        entry.status = Entry.ENTRY_STATUS_CLOSED

    @sp.entry_point
    def withdraw_deposit(self, address):
        sp.set_type(address, sp.TAddress)

        # Verify that entry address exists in the round
        sp.verify(self.data.entry_address_to_id.contains(address), Errors.INVALID_ENTRY_ADDRESS)

        entry_id = self.data.entry_address_to_id[address]
        entry = self.data.entries[entry_id]

        # Verify that the entry has not been disqualified
        sp.verify(entry.status != Entry.ENTRY_STATUS_DISQUALIFIED, Errors.ENTRY_DISQUALIFIED)

        # Verify that cooldown period is over
        sp.verify(
            sp.now > self.data.round_event_timestamps.cooldown_period_end, Errors.COOLDOWN_NOT_OVER
        )

        # Verify that entry has not withdrawn the deposit already
        sp.verify(~entry.deposit_withdrawn, Errors.DEPOSIT_ALREADY_WITHDRAWN)

        # Send deposit back to entry's creator
        sp.send(entry.creator, self.data.round_meta.security_deposit_amount)

        entry.deposit_withdrawn = True


##########
#  Tests
##########

if __name__ == "__main__":

    ##########
    # sponsor
    ##########

    @sp.add_test(name="sponsor accepts sponsored amount")
    def test():
        scenario = sp.test_scenario()

        stablecoin = DummyToken.FA12(Addresses.ADMIN)

        round_meta = sp.record(
            token_set=sp.set([TEZOS_IDENTIFIER]),
            security_deposit_amount=SECURITY_DEPOSIT_AMOUNT,
            dao_address=Addresses.DAO,
            stablecoin_address=stablecoin.address,
            donation_handler_address=Addresses.DONATION_HANDLER,
            community_fund_address=Addresses.COMMUNITY_FUND,
        )

        matching_round = MatchingRound(round_meta=round_meta)

        scenario += matching_round
        scenario += stablecoin

        # Mint the stablecoin for ALICE and BOB
        scenario += stablecoin.mint(address=Addresses.ALICE, value=1000).run(sender=Addresses.ADMIN)
        scenario += stablecoin.mint(address=Addresses.BOB, value=1000).run(sender=Addresses.ADMIN)

        # Approve matching round contract to spend the tokens
        scenario += stablecoin.approve(spender=matching_round.address, value=1000).run(
            sender=Addresses.ALICE
        )
        scenario += stablecoin.approve(spender=matching_round.address, value=1000).run(
            sender=Addresses.BOB
        )

        # ALICE calls sponsor entrypoint
        scenario += matching_round.sponsor(800).run(sender=Addresses.ALICE, now=sp.timestamp(1))

        # BOB calls sponsor entrypoint
        scenario += matching_round.sponsor(500).run(sender=Addresses.BOB, now=sp.timestamp(2))

        # Sponsorship has been correctly recorded
        scenario.verify(sp.len(matching_round.data.sponsors) == 2)
        scenario.verify(matching_round.data.sponsors[Addresses.ALICE] == 800)
        scenario.verify(matching_round.data.sponsors[Addresses.BOB] == 500)
        scenario.verify(matching_round.data.total_sponsored_amount == 1300)

        # Token balance check for matching round
        scenario.verify(stablecoin.data.balances[matching_round.address].balance == 1300)

    @sp.add_test(name="sponsor fails if sender has already sponsored")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(sponsors={Addresses.ALICE: 1000})

        scenario += matching_round

        # ALICE calls sponsor even though she sponsored before
        scenario += matching_round.sponsor(1000).run(
            sender=Addresses.ALICE, valid=False, exception=Errors.ALREADY_SPONSORED
        )

    @sp.add_test(name="sponsor fails if the sponsor period is over")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound()

        scenario += matching_round

        # ALICE calls sponsor when public contributions have already started
        scenario += matching_round.sponsor(1000).run(
            sender=Addresses.ALICE,
            now=sp.timestamp(6),
            valid=False,
            exception=Errors.NOT_ACCEPTING_SPONSORS,
        )

    @sp.add_test(name="sponsor fails if zero value is sponsored")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound()

        scenario += matching_round

        # ALICE calls sponsor when public contributions have already started
        scenario += matching_round.sponsor(0).run(
            sender=Addresses.ALICE,
            now=sp.timestamp(3),
            valid=False,
            exception=Errors.ZERO_VALUE_NOT_ALLOWED,
        )

    ##############
    # enter_round
    ##############

    @sp.add_test(name="enter_round allows entry to the round")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound()

        scenario += matching_round

        scenario += matching_round.enter_round(Addresses.ENTRY_1).run(
            sender=Addresses.JOHN, now=sp.timestamp(2), amount=SECURITY_DEPOSIT_AMOUNT
        )
        scenario += matching_round.enter_round(Addresses.ENTRY_2).run(
            sender=Addresses.BOB, now=sp.timestamp(2), amount=SECURITY_DEPOSIT_AMOUNT
        )

        # Sanity checks
        scenario.verify(matching_round.data.entry_address_to_id.contains(Addresses.ENTRY_1))
        scenario.verify(matching_round.data.entry_address_to_id.contains(Addresses.ENTRY_2))

        entry_1 = matching_round.data.entries[
            matching_round.data.entry_address_to_id[Addresses.ENTRY_1]
        ]
        entry_2 = matching_round.data.entries[
            matching_round.data.entry_address_to_id[Addresses.ENTRY_2]
        ]

        # Verify that ENTRY_1 has the correct fields
        scenario.verify(entry_1.address == Addresses.ENTRY_1)
        scenario.verify(entry_1.creator == Addresses.JOHN)
        scenario.verify(entry_1.status == Entry.ENTRY_STATUS_ACTIVE)
        scenario.verify(sp.len(entry_1.contributions) == 0)
        scenario.verify(sp.len(entry_1.contributors.elements()) == 0)
        scenario.verify(entry_1.clr_match == 0)
        scenario.verify(entry_1.deposit_withdrawn == False)

        # Verify that ENTRY_2 has the correct fields
        scenario.verify(entry_2.address == Addresses.ENTRY_2)
        scenario.verify(entry_2.creator == Addresses.BOB)
        scenario.verify(entry_2.status == Entry.ENTRY_STATUS_ACTIVE)
        scenario.verify(sp.len(entry_2.contributions) == 0)
        scenario.verify(sp.len(entry_2.contributors.elements()) == 0)
        scenario.verify(entry_2.clr_match == 0)
        scenario.verify(entry_2.deposit_withdrawn == False)

    @sp.add_test(name="enter_round fails if address is already in the round")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}))
        scenario += matching_round

        # ENTRY_1 is already in the round, but still tries to re-enter
        scenario += matching_round.enter_round(Addresses.ENTRY_1).run(
            sender=Addresses.JOHN,
            now=sp.timestamp(1),
            amount=SECURITY_DEPOSIT_AMOUNT,
            valid=False,
            exception=Errors.ALREADY_IN_ROUND,
        )

    @sp.add_test(name="enter_round fails if entry period is over")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound()
        scenario += matching_round

        # Entry requested 1 second after contribution starts (not valid)
        scenario += matching_round.enter_round(Addresses.ENTRY_1).run(
            sender=Addresses.JOHN,
            now=sp.timestamp(6),
            amount=SECURITY_DEPOSIT_AMOUNT,
            valid=False,
            exception=Errors.ENTRY_PERIOD_OVER,
        )

    @sp.add_test(name="enter_round fails if incorrect security deposit it made")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound()
        scenario += matching_round

        # Sender has not provided sufficient security deposit
        scenario += matching_round.enter_round(Addresses.ENTRY_1).run(
            sender=Addresses.JOHN,
            now=sp.timestamp(3),
            amount=sp.tez(1),
            valid=False,
            exception=Errors.INVALID_SECURITY_DEPOSIT,
        )

    #############
    # contribute
    #############

    # Generic entry
    ENTRY = sp.record(
        address=Addresses.ENTRY_1,
        creator=Addresses.JOHN,
        status=Entry.ENTRY_STATUS_ACTIVE,
        contributions={},
        contributors=sp.set([]),
        clr_match=0,
        deposit_withdrawn=False,
    )

    @sp.add_test(name="contribute records the contribution properly")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Contribution from ALICE to ENTRY_1
        scenario += matching_round.contribute(
            from_=Addresses.ALICE,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(6),
        )

        # Contribution from BOB to ENTRY_1
        scenario += matching_round.contribute(
            from_=Addresses.BOB,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=200,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(6),
        )

        entry = matching_round.data.entries[1]

        # Verify the number of contributors
        scenario.verify(sp.len(entry.contributors.elements()) == 2)
        scenario.verify(sp.len(entry.contributions[TEZOS_IDENTIFIER]) == 2)

        # Verify that correct contributors are recorded
        scenario.verify(entry.contributors.contains(Addresses.ALICE))
        scenario.verify(entry.contributors.contains(Addresses.BOB))

        # Verify the correctness of the contributions
        l = entry.contributions[TEZOS_IDENTIFIER]
        scenario.verify_equal(l, [200, 100])

    @sp.add_test(name="contribute fails if the sender is not donation_handler")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Contribution from ALICE to ENTRY_1 not sent through donation handler contracr
        scenario += matching_round.contribute(
            from_=Addresses.ALICE,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.RANDOM,
            now=sp.timestamp(6),
            valid=False,
            exception=Errors.NOT_ALLOWED,
        )

    @sp.add_test(name="contribute fails if the entry_address is not in the round")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Contribution from ALICE to non existing entry address
        scenario += matching_round.contribute(
            from_=Addresses.ALICE,
            entry_address=Addresses.RANDOM,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(6),
            valid=False,
            exception=Errors.INVALID_ENTRY_ADDRESS,
        )

    @sp.add_test(name="contribute fails if the contribution is not made in the correct period")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Contribution from ALICE to ENTRY_1 before contribution starts
        scenario += matching_round.contribute(
            from_=Addresses.ALICE,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(4),
            valid=False,
            exception=Errors.NOT_ACCEPTING_CONTRIBUTIONS,
        )

        # Contribution from ALICE to ENTRY_1 after contribution period ends
        scenario += matching_round.contribute(
            from_=Addresses.ALICE,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + 1),
            valid=False,
            exception=Errors.NOT_ACCEPTING_CONTRIBUTIONS,
        )

    @sp.add_test(name="contribute fails if the entry is not active")
    def test():
        scenario = sp.test_scenario()

        entry = sp.record(
            address=Addresses.ENTRY_1,
            creator=Addresses.JOHN,
            status=Entry.ENTRY_STATUS_DISQUALIFIED,
            contributions={},
            contributors=sp.set([]),
            clr_match=0,
            deposit_withdrawn=False,
        )

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: entry}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Contribution from ALICE to disqualified ENTRY_1
        scenario += matching_round.contribute(
            from_=Addresses.ALICE,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(6),
            valid=False,
            exception=Errors.ENTRY_NOT_ACTIVE,
        )

    @sp.add_test(name="contribute fails if the contributor has already contributed")
    def test():
        scenario = sp.test_scenario()

        entry = sp.record(
            address=Addresses.ENTRY_1,
            creator=Addresses.JOHN,
            status=Entry.ENTRY_STATUS_ACTIVE,
            contributions={},
            contributors=sp.set([Addresses.ALICE]),
            clr_match=0,
            deposit_withdrawn=False,
        )

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: entry}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # ALICE re-contributes to ENTRY_1
        scenario += matching_round.contribute(
            from_=Addresses.ALICE,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(6),
            valid=False,
            exception=Errors.ALREADY_CONTRIBUTED,
        )

    @sp.add_test(name="contribute fails for self-contributions")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # JOHN (creator of ENTRY_1) self contributes
        scenario += matching_round.contribute(
            from_=Addresses.JOHN,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(6),
            valid=False,
            exception=Errors.SELF_CONTRIBUTION_NOT_ALLOWED,
        )

        # ENTRY_1 self contributes to itself
        scenario += matching_round.contribute(
            from_=Addresses.ENTRY_1,
            entry_address=Addresses.ENTRY_1,
            token_identifier=TEZOS_IDENTIFIER,
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(6),
            valid=False,
            exception=Errors.SELF_CONTRIBUTION_NOT_ALLOWED,
        )

    @sp.add_test(name="contribute fails if incorrect token identifier is used")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # ALICE uses an unknown token identifier
        scenario += matching_round.contribute(
            from_=Addresses.ALICE,
            entry_address=Addresses.ENTRY_1,
            token_identifier=sp.pack("unknown"),
            value=100,
        ).run(
            sender=Addresses.DONATION_HANDLER,
            now=sp.timestamp(6),
            valid=False,
            exception=Errors.INVALID_TOKEN_IDENTIFIER,
        )

    #####################
    # disqualify_entries
    #####################

    @sp.add_test(name="disqualify_entries can disqualify a single entry")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                2: sp.record(
                    address=Addresses.ENTRY_2,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                3: sp.record(
                    address=Addresses.ENTRY_3,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
            }
        )

        community_fund = DummyCommunityFund.DummyCommunityFund()
        community_fund.set_initial_balance(sp.tez(0))

        round_meta = sp.record(
            token_set=sp.set([TEZOS_IDENTIFIER]),
            security_deposit_amount=SECURITY_DEPOSIT_AMOUNT,
            dao_address=Addresses.DAO,
            stablecoin_address=Addresses.STABLECOIN,
            donation_handler_address=Addresses.DONATION_HANDLER,
            community_fund_address=community_fund.address,
        )

        matching_round = MatchingRound(entries=entries, round_meta=round_meta)

        security_deposit_nat = sp.utils.mutez_to_nat(SECURITY_DEPOSIT_AMOUNT)
        matching_round.set_initial_balance(sp.utils.nat_to_mutez(security_deposit_nat * 3))

        scenario += matching_round
        scenario += community_fund

        # Disqualify entry 1
        scenario += matching_round.disqualify_entries(sp.list([1])).run(
            sender=Addresses.DAO, now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + 1)
        )

        # Verify that the entries have correct status after disqualification
        scenario.verify(matching_round.data.entries[1].status == Entry.ENTRY_STATUS_DISQUALIFIED)
        scenario.verify(matching_round.data.entries[2].status == Entry.ENTRY_STATUS_ACTIVE)
        scenario.verify(matching_round.data.entries[3].status == Entry.ENTRY_STATUS_ACTIVE)

        # Verify that the final balances of community fund and matching round are correct
        scenario.verify(matching_round.balance == sp.utils.nat_to_mutez(security_deposit_nat * 2))
        scenario.verify(community_fund.balance == sp.utils.nat_to_mutez(security_deposit_nat * 1))

    @sp.add_test(name="disqualify_entries can disqualify multiple entries")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                2: sp.record(
                    address=Addresses.ENTRY_2,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                3: sp.record(
                    address=Addresses.ENTRY_3,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
            }
        )

        community_fund = DummyCommunityFund.DummyCommunityFund()
        community_fund.set_initial_balance(sp.tez(0))

        round_meta = sp.record(
            token_set=sp.set([TEZOS_IDENTIFIER]),
            security_deposit_amount=SECURITY_DEPOSIT_AMOUNT,
            dao_address=Addresses.DAO,
            stablecoin_address=Addresses.STABLECOIN,
            donation_handler_address=Addresses.DONATION_HANDLER,
            community_fund_address=community_fund.address,
        )

        matching_round = MatchingRound(entries=entries, round_meta=round_meta)

        security_deposit_nat = sp.utils.mutez_to_nat(SECURITY_DEPOSIT_AMOUNT)
        matching_round.set_initial_balance(sp.utils.nat_to_mutez(security_deposit_nat * 3))

        scenario += matching_round
        scenario += community_fund

        # Disqualify entries 2 and 3
        scenario += matching_round.disqualify_entries(sp.list([2, 3])).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + 1),
        )

        # Verify that the entries have correct status after diaqualification
        scenario.verify(matching_round.data.entries[1].status == Entry.ENTRY_STATUS_ACTIVE)
        scenario.verify(matching_round.data.entries[2].status == Entry.ENTRY_STATUS_DISQUALIFIED)
        scenario.verify(matching_round.data.entries[3].status == Entry.ENTRY_STATUS_DISQUALIFIED)

        # Verify that the final balances of community fund and matching round are correct
        scenario.verify(matching_round.balance == sp.utils.nat_to_mutez(security_deposit_nat * 1))
        scenario.verify(community_fund.balance == sp.utils.nat_to_mutez(security_deposit_nat * 2))

    @sp.add_test(name="disqualify_entries fail if sender is not the DAO")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # RANDOM tries to disqualify ENTRY_1
        scenario += matching_round.disqualify_entries(sp.list([1])).run(
            sender=Addresses.RANDOM,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + 1),
            valid=False,
            exception=Errors.NOT_ALLOWED,
        )

    @sp.add_test(name="disqualify_entries fails if the timing is not correct")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Disqualification of ENTRY_1 after cooldown period
        scenario += matching_round.disqualify_entries(sp.list([1])).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD),
            valid=False,
            exception=Errors.COOLDOWN_PERIOD_OVER,
        )

    @sp.add_test(name="disqualify_entries fails if an entry is already disqualified")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                2: sp.record(
                    address=Addresses.ENTRY_2,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_DISQUALIFIED,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                3: sp.record(
                    address=Addresses.ENTRY_3,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
            }
        )

        matching_round = MatchingRound(entries=entries)

        scenario += matching_round

        # Disqualify all entries (2 is already disqualified)
        scenario += matching_round.disqualify_entries(sp.list([1, 2, 3])).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + 1),
            valid=False,
            exception=Errors.ENTRY_ALREADY_DISQUALIFIED,
        )

    ##################
    # set_clr_matches
    ##################

    @sp.add_test(name="set_clr_matches sets the match properly")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                2: sp.record(
                    address=Addresses.ENTRY_2,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                3: sp.record(
                    address=Addresses.ENTRY_3,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
            }
        )

        matching_round = MatchingRound(entries=entries)

        scenario += matching_round

        # Set the matches
        scenario += matching_round.set_clr_matches(sp.map(l={1: 4000, 2: 3500, 3: 2500})).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
        )

        # verify if matches_set is set to True
        scenario.verify(matching_round.data.matches_set)

        # Verify that the set matches are correct
        scenario.verify(matching_round.data.entries[1].clr_match == 4000)
        scenario.verify(matching_round.data.entries[2].clr_match == 3500)
        scenario.verify(matching_round.data.entries[3].clr_match == 2500)

        # Verify that the challenge period end has been set properly
        scenario.verify(
            matching_round.data.round_event_timestamps.challenge_period_end
            == CONTRIBUTION_START.add_seconds(
                CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + CHALLENGE_PERIOD + 1
            )
        )

    @sp.add_test(name="set_clr_matches sets the match correctly more than once")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                2: sp.record(
                    address=Addresses.ENTRY_2,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                3: sp.record(
                    address=Addresses.ENTRY_3,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
            }
        )

        matching_round = MatchingRound(entries=entries)

        scenario += matching_round

        # Set the match
        scenario += matching_round.set_clr_matches(sp.map(l={1: 4000, 2: 3500, 3: 2500})).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
        )

        # Re-set the match before the challenge period is over
        scenario += matching_round.set_clr_matches(sp.map(l={1: 5000, 3: 1500})).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(
                CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + CHALLENGE_PERIOD - 1
            ),
        )

        # Verify that the set matches are correct
        scenario.verify(matching_round.data.entries[1].clr_match == 5000)
        scenario.verify(matching_round.data.entries[2].clr_match == 3500)
        scenario.verify(matching_round.data.entries[3].clr_match == 1500)

        # Verify that the challenge period end has been set properly
        scenario.verify(
            matching_round.data.round_event_timestamps.challenge_period_end
            == CONTRIBUTION_START.add_seconds(
                CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + CHALLENGE_PERIOD + 1
            )
        )

    @sp.add_test(name="set_clr_matches fails if sender is not the DAO")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # RANDOM tries to set the clr matches
        scenario += matching_round.set_clr_matches(sp.map(l={1: 4000,})).run(
            sender=Addresses.RANDOM,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
            valid=False,
            exception=Errors.NOT_ALLOWED,
        )

    @sp.add_test(name="set_clr_matches fail if timing is incorrect")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Setting the match before cooldown is over
        scenario += matching_round.set_clr_matches(sp.map(l={1: 4000,})).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD - 1),
            valid=False,
            exception=Errors.COOLDOWN_NOT_OVER,
        )

        # Set the match at the correct time
        scenario += matching_round.set_clr_matches(sp.map(l={1: 4000,})).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
        )

        # Verify if the match is set, and challenge period updated
        scenario.verify(matching_round.data.entries[1].clr_match == 4000)
        scenario.verify(
            matching_round.data.round_event_timestamps.challenge_period_end
            == CONTRIBUTION_START.add_seconds(
                CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + CHALLENGE_PERIOD + 1
            )
        )

        # Set the match again after the challenge period is over
        scenario += matching_round.set_clr_matches(sp.map(l={1: 4000,})).run(
            sender=Addresses.DAO,
            now=CONTRIBUTION_START.add_seconds(
                CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + CHALLENGE_PERIOD + 1
            ),
            valid=False,
            exception=Errors.CHALLENGE_PERIOD_OVER,
        )

    #################
    # withdraw_match
    #################

    @sp.add_test(name="withdraw_match allows entries to withdraw their match correctly")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=1000,
                    deposit_withdrawn=False,
                ),
                2: sp.record(
                    address=Addresses.ENTRY_2,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=2000,
                    deposit_withdrawn=False,
                ),
                3: sp.record(
                    address=Addresses.ENTRY_3,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=3000,
                    deposit_withdrawn=False,
                ),
            }
        )

        entry_address_to_id = sp.big_map(
            l={Addresses.ENTRY_1: 1, Addresses.ENTRY_2: 2, Addresses.ENTRY_3: 3}
        )

        stablecoin = DummyToken.FA12(Addresses.ADMIN)

        round_meta = sp.record(
            token_set=sp.set([TEZOS_IDENTIFIER]),
            security_deposit_amount=SECURITY_DEPOSIT_AMOUNT,
            dao_address=Addresses.DAO,
            stablecoin_address=stablecoin.address,
            donation_handler_address=Addresses.DONATION_HANDLER,
            community_fund_address=Addresses.COMMUNITY_FUND,
        )

        round_event_timestamps = sp.record(
            contribution_start=sp.timestamp(0),
            contribution_end=sp.timestamp(0),
            cooldown_period_end=sp.timestamp(0),
            challenge_period_end=sp.timestamp(1),
        )

        matching_round = MatchingRound(
            round_meta=round_meta,
            round_event_timestamps=round_event_timestamps,
            entries=entries,
            entry_address_to_id=entry_address_to_id,
            matches_set=sp.bool(True),
        )

        scenario += stablecoin
        scenario += matching_round

        # Mint stablecoin for the Matching Round contract
        scenario += stablecoin.mint(address=matching_round.address, value=6000).run(
            sender=Addresses.ADMIN
        )

        # ENTRY_1 withdraws match
        scenario += matching_round.withdraw_match(Addresses.ENTRY_1).run(now=sp.timestamp(2))

        # ENTRY_2 withdraws match
        scenario += matching_round.withdraw_match(Addresses.ENTRY_2).run(now=sp.timestamp(3))

        # ENTRY_3 withdraws match
        scenario += matching_round.withdraw_match(Addresses.ENTRY_3).run(now=sp.timestamp(4))

        # Verify the balances of the entries
        scenario.verify(stablecoin.data.balances[Addresses.ENTRY_1].balance == 1000)
        scenario.verify(stablecoin.data.balances[Addresses.ENTRY_2].balance == 2000)
        scenario.verify(stablecoin.data.balances[Addresses.ENTRY_3].balance == 3000)

        # Verify the entry status
        scenario.verify(matching_round.data.entries[1].status == Entry.ENTRY_STATUS_CLOSED)
        scenario.verify(matching_round.data.entries[2].status == Entry.ENTRY_STATUS_CLOSED)
        scenario.verify(matching_round.data.entries[3].status == Entry.ENTRY_STATUS_CLOSED)

    @sp.add_test(name="withdraw_match fails if entry address is not in round")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound()
        scenario += matching_round

        # Try to withdraw match for ENTRY_1 (not in round)
        scenario += matching_round.withdraw_match(Addresses.ENTRY_1).run(
            valid=False, exception=Errors.INVALID_ENTRY_ADDRESS
        )

    @sp.add_test(name="withdraw_match fails if entry is not active")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_DISQUALIFIED,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
            }
        )

        entry_address_to_id = sp.big_map(
            l={
                Addresses.ENTRY_1: 1,
            }
        )
        matching_round = MatchingRound(
            entries=entries,
            entry_address_to_id=entry_address_to_id,
            matches_set=sp.bool(True),
        )

        scenario += matching_round

        # ENTRY_1 (disqualified) withdraws match
        scenario += matching_round.withdraw_match(Addresses.ENTRY_1).run(
            valid=False, exception=Errors.ENTRY_NOT_ACTIVE
        )

    @sp.add_test(name="withdraw_match fails if matches are not yet set")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=1000,
                    deposit_withdrawn=False,
                ),
            }
        )

        entry_address_to_id = sp.big_map(
            l={
                Addresses.ENTRY_1: 1,
            }
        )

        round_event_timestamps = sp.record(
            contribution_start=sp.timestamp(0),
            contribution_end=sp.timestamp(0),
            cooldown_period_end=sp.timestamp(0),
            challenge_period_end=sp.timestamp(1),
        )

        matching_round = MatchingRound(
            round_event_timestamps=round_event_timestamps,
            entries=entries,
            entry_address_to_id=entry_address_to_id,
        )

        scenario += matching_round

        # ENTRY_1 withdraws match before challenge period is over
        scenario += matching_round.withdraw_match(Addresses.ENTRY_1).run(
            now=sp.timestamp(0), valid=False, exception=Errors.MATCHES_NOT_SET
        )

    @sp.add_test(name="withdraw_match fails if timing is incorrect")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=1000,
                    deposit_withdrawn=False,
                ),
            }
        )

        entry_address_to_id = sp.big_map(
            l={
                Addresses.ENTRY_1: 1,
            }
        )

        round_event_timestamps = sp.record(
            contribution_start=sp.timestamp(0),
            contribution_end=sp.timestamp(0),
            cooldown_period_end=sp.timestamp(0),
            challenge_period_end=sp.timestamp(1),
        )

        matching_round = MatchingRound(
            round_event_timestamps=round_event_timestamps,
            entries=entries,
            entry_address_to_id=entry_address_to_id,
            matches_set=True,
        )

        scenario += matching_round

        # ENTRY_1 withdraws match before challenge period is over
        scenario += matching_round.withdraw_match(Addresses.ENTRY_1).run(
            now=sp.timestamp(0), valid=False, exception=Errors.CHALLENGE_PERIOD_ONGOING
        )

    @sp.add_test(name="withdraw_match fails if entries match is zero")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
            }
        )

        entry_address_to_id = sp.big_map(
            l={
                Addresses.ENTRY_1: 1,
            }
        )

        round_event_timestamps = sp.record(
            contribution_start=sp.timestamp(0),
            contribution_end=sp.timestamp(0),
            cooldown_period_end=sp.timestamp(0),
            challenge_period_end=sp.timestamp(1),
        )

        matching_round = MatchingRound(
            round_event_timestamps=round_event_timestamps,
            entries=entries,
            entry_address_to_id=entry_address_to_id,
            matches_set=sp.bool(True),
        )

        scenario += matching_round

        # ENTRY_1, with 0 match calls withdraws_match
        scenario += matching_round.withdraw_match(Addresses.ENTRY_1).run(
            now=sp.timestamp(2),
            valid=False,
            exception=Errors.ZERO_CLR_MATCH,
        )

    ###################
    # withdraw_deposit
    ###################

    @sp.add_test(name="withdraw_deposit allows entries to withdraw their security deposit")
    def test():
        scenario = sp.test_scenario()

        entries = sp.big_map(
            l={
                1: sp.record(
                    address=Addresses.ENTRY_1,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                2: sp.record(
                    address=Addresses.ENTRY_2,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_CLOSED,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
                3: sp.record(
                    address=Addresses.ENTRY_3,
                    creator=Addresses.JOHN,
                    status=Entry.ENTRY_STATUS_ACTIVE,
                    contributions={},
                    contributors=sp.set([]),
                    clr_match=0,
                    deposit_withdrawn=False,
                ),
            }
        )

        entry_address_to_id = sp.big_map(
            l={Addresses.ENTRY_1: 1, Addresses.ENTRY_2: 2, Addresses.ENTRY_3: 3}
        )

        matching_round = MatchingRound(entries=entries, entry_address_to_id=entry_address_to_id)

        security_deposit_nat = sp.utils.mutez_to_nat(SECURITY_DEPOSIT_AMOUNT)
        matching_round.set_initial_balance(sp.utils.nat_to_mutez(security_deposit_nat * 3))

        scenario += matching_round

        # ENTRY_1 withdraws deposit
        scenario += matching_round.withdraw_deposit(Addresses.ENTRY_1).run(
            sender=Addresses.JOHN,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
        )

        # ENTRY_2 withdraws deposit
        scenario += matching_round.withdraw_deposit(Addresses.ENTRY_2).run(
            sender=Addresses.JOHN,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
        )

        # Verify final balance of matching round
        scenario.verify(matching_round.balance == sp.utils.nat_to_mutez(security_deposit_nat * 1))

        # Verify that the entry field is properly updated
        scenario.verify(matching_round.data.entries[1].deposit_withdrawn)
        scenario.verify(matching_round.data.entries[2].deposit_withdrawn)
        scenario.verify(~matching_round.data.entries[3].deposit_withdrawn)

    @sp.add_test(name="withdraw_deposit fails if invalid entry address is provided")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Withdraw deposit for ENTRY_2 (not present in round)
        scenario += matching_round.withdraw_deposit(Addresses.ENTRY_2).run(
            sender=Addresses.JOHN,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
            valid=False,
            exception=Errors.INVALID_ENTRY_ADDRESS,
        )

    @sp.add_test(name="withdraw_deposit fails if entry is disqualified")
    def test():
        scenario = sp.test_scenario()

        entry = sp.record(
            address=Addresses.ENTRY_1,
            creator=Addresses.JOHN,
            status=Entry.ENTRY_STATUS_DISQUALIFIED,
            contributions={},
            contributors=sp.set([]),
            clr_match=0,
            deposit_withdrawn=False,
        )

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: entry}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Withdraw deposit for ENTRY_1 (disqualified)
        scenario += matching_round.withdraw_deposit(Addresses.ENTRY_1).run(
            sender=Addresses.JOHN,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
            valid=False,
            exception=Errors.ENTRY_DISQUALIFIED,
        )

    @sp.add_test(name="withdraw_deposit fails if the timing is incorrect")
    def test():
        scenario = sp.test_scenario()

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: ENTRY}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Withdraw deposit for ENTRY_1 before cooldown period is over
        scenario += matching_round.withdraw_deposit(Addresses.ENTRY_1).run(
            sender=Addresses.JOHN,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD - 1),
            valid=False,
            exception=Errors.COOLDOWN_NOT_OVER,
        )

    @sp.add_test(name="withdraw_deposit fails if the deposit is already withdrawn")
    def test():
        scenario = sp.test_scenario()

        entry = sp.record(
            address=Addresses.ENTRY_1,
            creator=Addresses.JOHN,
            status=Entry.ENTRY_STATUS_ACTIVE,
            contributions={},
            contributors=sp.set([]),
            clr_match=0,
            deposit_withdrawn=True,
        )

        matching_round = MatchingRound(
            entries=sp.big_map(l={1: entry}),
            entry_address_to_id=sp.big_map(l={Addresses.ENTRY_1: 1}),
        )

        scenario += matching_round

        # Withdraw deposit for ENTRY_1 (already withdrawn earlier)
        scenario += matching_round.withdraw_deposit(Addresses.ENTRY_1).run(
            sender=Addresses.JOHN,
            now=CONTRIBUTION_START.add_seconds(CONTRIBUTION_PERIOD + COOLDOWN_PERIOD + 1),
            valid=False,
            exception=Errors.DEPOSIT_ALREADY_WITHDRAWN,
        )


sp.add_compilation_target("matching_round", MatchingRound())
