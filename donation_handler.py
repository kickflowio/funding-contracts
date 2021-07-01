import smartpy as sp

Addresses = sp.io.import_script_from_url("file:helpers/addresses.py")
DummyRound = sp.io.import_script_from_url("file:helpers/dummy_round.py")
DummyWhitelist = sp.io.import_script_from_url("file:helpers/dummy_whitelist.py")
DummyToken = sp.io.import_script_from_url("file:helpers/dummy_token.py")
Errors = sp.io.import_script_from_url("file:types/errors.py")

TEZOS_IDENTIFIER = sp.pack("TEZOS_IDENTIFIER")


class DonationHandler(sp.Contract):
    def __init__(
        self,
        round_address=sp.none,
        whitelist_address=Addresses.WHITELIST,
        dao_address=Addresses.DAO,
    ):
        self.init(
            round_address=round_address,
            whitelist_address=whitelist_address,
            dao_address=dao_address,
        )

    @sp.entry_point
    def donate(self, params):
        sp.set_type(
            params,
            sp.TRecord(
                identifier=sp.TBytes,
                project_address=sp.TAddress,
                value=sp.TNat,
            ),
        )

        # Verify if round is active
        sp.verify(self.data.round_address.is_some(), Errors.NO_ROUND_IS_ACTIVE)

        # Verify if sender is whitelisted
        c = sp.contract(sp.TAddress, self.data.whitelist_address, "verify_whitelisted").open_some()
        sp.transfer(sp.sender, sp.tez(0), c)

        # Create contract instance for round contract, to call contribute entry point
        cr = sp.contract(
            sp.TRecord(
                from_=sp.TAddress, project_address=sp.TAddress, identifier=sp.TBytes, value=sp.TNat
            ),
            self.data.round_address.open_some(),
            "contribute",
        ).open_some()

        # If identifier is of tez, then transfer tez to the project
        sp.if params.identifier == TEZOS_IDENTIFIER:
            # Get Nat value of sent amount
            tez_val = sp.utils.mutez_to_nat(sp.amount)

            # Verify if parameter value is same as send amount
            sp.verify(params.value == tez_val, Errors.INCORRECT_VALUE_PARAMETER)

            # Store contribution in the round contract
            sp.transfer(
                sp.record(
                    from_=sp.sender,
                    project_address=params.project_address,
                    identifier=params.identifier,
                    value=tez_val,
                ),
                sp.tez(0),
                cr,
            )

            # Send the donation to the project address
            sp.send(params.project_address, sp.amount)
        # Any other FA1.2 compliant token
        sp.else:
            # Store contribution in the round contract
            sp.transfer(
                sp.record(
                    from_=sp.sender,
                    project_address=params.project_address,
                    identifier=params.identifier,
                    value=params.value,
                ),
                sp.tez(0),
                cr,
            )

            # Get token address from identifier bytes
            token_address = sp.unpack(params.identifier, t=sp.TAddress).open_some()

            # Send donation to the project
            ct = sp.contract(
                sp.TRecord(from_=sp.TAddress, to_=sp.TAddress, value=sp.TNat).layout(
                    ("from_ as from", ("to_ as to", "value"))
                ),
                token_address,
                "transfer",
            ).open_some()

            sp.transfer(
                sp.record(
                    from_=sp.sender,
                    to_=params.project_address,
                    value=params.value,
                ),
                sp.tez(0),
                ct,
            )

    @sp.entry_point
    def set_round_address(self, address):
        sp.set_type(address, sp.TOption(sp.TAddress))

        # Ony DAO can change this
        sp.verify(sp.sender == self.data.dao_address, Errors.ONLY_DAO_ALLOWED)

        self.data.round_address = address

    @sp.entry_point
    def set_whitelist_address(self, address):
        sp.set_type(address, sp.TAddress)

        # Ony DAO can change this
        sp.verify(sp.sender == self.data.dao_address, Errors.ONLY_DAO_ALLOWED)

        self.data.whitelist_address = address


if __name__ == "__main__":

    #########
    # donate
    #########

    @sp.add_test(name="donate relays tez donations to the project_address specified")
    def test():
        scenario = sp.test_scenario()

        whitelist = DummyWhitelist.DummyWhitelist(True)
        matching_round = DummyRound.DummyRound()
        donation_handler = DonationHandler(
            round_address=sp.some(matching_round.address), whitelist_address=whitelist.address
        )

        scenario += donation_handler
        scenario += matching_round
        scenario += whitelist

        # Make a donation of 1000 mutez
        scenario += donation_handler.donate(
            identifier=TEZOS_IDENTIFIER, project_address=Addresses.PROJECT_1, value=1000
        ).run(amount=sp.mutez(1000), sender=Addresses.ALICE, valid=True)

    @sp.add_test(name="donate relays FA12 token donations to the project_address specified")
    def test():
        scenario = sp.test_scenario()

        token = DummyToken.FA12(Addresses.ADMIN)
        whitelist = DummyWhitelist.DummyWhitelist(True)
        matching_round = DummyRound.DummyRound()
        donation_handler = DonationHandler(
            round_address=sp.some(matching_round.address), whitelist_address=whitelist.address
        )

        scenario += donation_handler
        scenario += matching_round
        scenario += whitelist
        scenario += token

        # Mint tokens for ALICE
        scenario += token.mint(address=Addresses.ALICE, value=100).run(sender=Addresses.ADMIN)

        # Approve DonationHandler to spend
        scenario += token.approve(spender=donation_handler.address, value=100).run(
            sender=Addresses.ALICE
        )

        # ALICE donates 80 tokens to PROJECT_1
        scenario += donation_handler.donate(
            identifier=sp.pack(token.address), project_address=Addresses.PROJECT_1, value=80
        ).run(sender=Addresses.ALICE)

        # Verify balances of the parties
        scenario.verify(token.data.balances[Addresses.ALICE].balance == 20)
        scenario.verify(token.data.balances[Addresses.PROJECT_1].balance == 80)

    @sp.add_test(name="donate fails if no round is active")
    def test():
        scenario = sp.test_scenario()

        # round_address is sp.none by default
        donation_handler = DonationHandler()

        scenario += donation_handler

        scenario += donation_handler.donate(
            identifier=TEZOS_IDENTIFIER, project_address=Addresses.PROJECT_1, value=1000
        ).run(
            amount=sp.mutez(1000),
            sender=Addresses.ALICE,
            valid=False,
            exception=Errors.NO_ROUND_IS_ACTIVE,
        )

    @sp.add_test(name="donate fails if sender address is not whitelisted")
    def test():
        scenario = sp.test_scenario()

        # verify_whitelist would fail
        whitelist = DummyWhitelist.DummyWhitelist(False)
        matching_round = DummyRound.DummyRound()
        donation_handler = DonationHandler(
            round_address=sp.some(matching_round.address), whitelist_address=whitelist.address
        )

        scenario += donation_handler
        scenario += matching_round
        scenario += whitelist

        # Make a donation of 1000 mutez
        scenario += donation_handler.donate(
            identifier=TEZOS_IDENTIFIER, project_address=Addresses.PROJECT_1, value=1000
        ).run(
            amount=sp.mutez(1000),
            sender=Addresses.ALICE,
            valid=False,
            exception=Errors.ADDRESS_NOT_WHITELISTED,
        )

    @sp.add_test(name="donate fails if parameter value does not match tez transfer AMOUNT")
    def test():
        scenario = sp.test_scenario()

        whitelist = DummyWhitelist.DummyWhitelist(True)
        matching_round = DummyRound.DummyRound()
        donation_handler = DonationHandler(
            round_address=sp.some(matching_round.address), whitelist_address=whitelist.address
        )

        scenario += donation_handler
        scenario += matching_round
        scenario += whitelist

        # Make a donation of 1000 mutez
        scenario += donation_handler.donate(
            identifier=TEZOS_IDENTIFIER, project_address=Addresses.PROJECT_1, value=1200
        ).run(
            amount=sp.mutez(1000),
            sender=Addresses.ALICE,
            valid=False,
            exception=Errors.INCORRECT_VALUE_PARAMETER,
        )

    ####################
    # set_round_address
    ####################

    @sp.add_test(name="set_round_address sets the round address correctly")
    def test():
        scenario = sp.test_scenario()

        donation_handler = DonationHandler()
        scenario += donation_handler

        # Set the round address
        scenario += donation_handler.set_round_address(sp.some(Addresses.ROUND)).run(
            sender=Addresses.DAO
        )

        # Verify if round address is set
        scenario.verify(donation_handler.data.round_address.open_some() == Addresses.ROUND)

        # Set round address to none
        scenario += donation_handler.set_round_address(sp.none).run(sender=Addresses.DAO)

        # Verify if round address is none
        scenario.verify(~donation_handler.data.round_address.is_some())

    @sp.add_test(name="set_round_address fails if sender is not DAO")
    def test():
        scenario = sp.test_scenario()

        donation_handler = DonationHandler()
        scenario += donation_handler

        # ALICE tries to set the round address
        scenario += donation_handler.set_round_address(sp.some(Addresses.ROUND)).run(
            sender=Addresses.ALICE, valid=False
        )

        # Verify if round address is none
        scenario.verify(~donation_handler.data.round_address.is_some())

    #######################
    # set_whitelist_address
    #######################

    @sp.add_test(name="set_whitelist_address sets the whitelist address correctly")
    def test():
        scenario = sp.test_scenario()

        donation_handler = DonationHandler()
        scenario += donation_handler

        # Set the whitelist address
        scenario += donation_handler.set_whitelist_address(Addresses.RANDOM).run(
            sender=Addresses.DAO
        )

        # Verify if whitelist address is set
        scenario.verify(donation_handler.data.whitelist_address == Addresses.RANDOM)

    @sp.add_test(name="set_whitelist_address fails if sender is not DAO")
    def test():
        scenario = sp.test_scenario()

        donation_handler = DonationHandler()

        scenario += donation_handler

        # ALICE tries to set the whitelist address
        scenario += donation_handler.set_whitelist_address(Addresses.RANDOM).run(
            sender=Addresses.ALICE, valid=False
        )

        # Verify if whitelist address is unchanged
        scenario.verify(donation_handler.data.whitelist_address == Addresses.WHITELIST)

sp.add_compilation_target("donation_handler", DonationHandler())