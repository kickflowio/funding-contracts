import smartpy as sp

Addresses = sp.io.import_script_from_url("file:helpers/addresses.py")
Errors = sp.io.import_script_from_url("file:types/errors.py")

class Whitelist(sp.Contract):
    def __init__(
        self,
        admin=Addresses.ADMIN,
        proposed_admin=sp.none,
        whitelist=sp.set(t=sp.TAddress),
        governors=sp.set(l=[Addresses.ADMIN], t=sp.TAddress),
    ):
        self.init(
            admin=admin,
            proposed_admin=proposed_admin,
            governors=governors,
            whitelist=whitelist,
        )

        self.init_type(
            sp.TRecord(
                admin=sp.TAddress,
                proposed_admin=sp.TOption(sp.TAddress),
                governors=sp.TSet(sp.TAddress),
                whitelist=sp.TSet(sp.TAddress),
            )
        )

    @sp.entry_point
    def whitelist_addresses(self, list_):
        sp.set_type(list_, sp.TList(sp.TAddress))

        # Verify if sender is a governor
        sp.verify(self.data.governors.contains(sp.sender), Errors.NOT_ALLOWED)
        sp.for addr in list_:
            self.data.whitelist.add(addr)

    @sp.entry_point
    def verify_whitelisted(self, address):
        sp.set_type(address, sp.TAddress)

        # Verify that the address is present in the whitelist set
        sp.verify(self.data.whitelist.contains(address), Errors.ADDRESS_NOT_WHITELISTED)

    @sp.entry_point
    def add_governor(self, address):
        sp.set_type(address, sp.TAddress)

        # Verify that sender is the admin
        sp.verify(sp.sender == self.data.admin, Errors.NOT_ALLOWED)

        # Add address to set of governors
        self.data.governors.add(address)

    # Allows for removal of a governor
    @sp.entry_point
    def remove_governor(self, address):
        sp.set_type(address, sp.TAddress)

        # Verify if sender is the admin
        sp.verify(sp.sender == self.data.admin, Errors.NOT_ALLOWED)

        # Remove address from set of governors
        self.data.governors.remove(address)

    @sp.entry_point
    def propose_new_admin(self, admin_):
        sp.set_type(admin_, sp.TAddress)

        # Verify if sender is the admin
        sp.verify(sp.sender == self.data.admin, Errors.NOT_ALLOWED)

        self.data.proposed_admin = sp.some(admin_)

    @sp.entry_point
    def accept_administration(self):
        # Verify if new admin has been proposed
        sp.verify(self.data.proposed_admin.is_some(), Errors.NO_ADMIN_PROPOSED)

        # Verify if the sender is the newly proposed admin
        sp.verify(sp.sender == self.data.proposed_admin.open_some(), Errors.NOT_ALLOWED)

        # Transfer administration
        self.data.admin = sp.sender
        self.data.proposed_admin = sp.none


########
# Tests
########

if __name__ == "__main__":

    ######################
    # whitelist_addresses
    ######################

    @sp.add_test(name="whitelist_addresses allows a governor to whitelist addresses")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist()

        scenario += whitelist

        # ADMIN whitelist addresses
        scenario += whitelist.whitelist_addresses([Addresses.ALICE, Addresses.BOB]).run(
            sender=Addresses.ADMIN
        )

        # Verify that ALICE and BOB have been added to the whitelist
        scenario.verify(whitelist.data.whitelist.contains(Addresses.ALICE))
        scenario.verify(whitelist.data.whitelist.contains(Addresses.BOB))

    @sp.add_test(name="whitelist_addresses fail if sender is not a governor")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist()

        scenario += whitelist

        # JOHN tries to whitelist addresses
        scenario += whitelist.whitelist_addresses([Addresses.ALICE, Addresses.BOB]).run(
            sender=Addresses.JOHN,
            valid=False,
            exception=Errors.NOT_ALLOWED,
        )

    #####################
    # verify_whitelisted
    #####################

    @sp.add_test(name="verify_whitelisted works correctly")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist(whitelist=sp.set([Addresses.ALICE, Addresses.BOB]))

        scenario += whitelist

        # Verify if ALICE is whitelisted
        scenario += whitelist.verify_whitelisted(Addresses.ALICE).run(valid=True)

        # Verify if BOB is whitelisted
        scenario += whitelist.verify_whitelisted(Addresses.BOB).run(valid=True)

        # Verify if JOHN is whitelisted
        scenario += whitelist.verify_whitelisted(Addresses.JOHN).run(
            valid=False, exception=Errors.ADDRESS_NOT_WHITELISTED
        )

    ###############
    # add_governor
    ###############

    @sp.add_test(name="add_governor allows admin to add a new governor")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist()

        scenario += whitelist

        # ADMIN adds a new governor
        scenario += whitelist.add_governor(Addresses.GOVERNOR).run(sender=Addresses.ADMIN)

        # Verify that the new governor is added
        scenario.verify(whitelist.data.governors.contains(Addresses.GOVERNOR))

    @sp.add_test(name="add_governor fails if non-admin address calls it")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist()

        scenario += whitelist

        # ALICE tries to add a new governor
        scenario += whitelist.add_governor(Addresses.GOVERNOR).run(
            sender=Addresses.ALICE,
            valid=False,
            exception=Errors.NOT_ALLOWED,
        )

    ##################
    # remove_governor
    ##################

    @sp.add_test(name="remove_governor allows admin to remove a governor")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist(governors=sp.set([Addresses.GOVERNOR]))

        scenario += whitelist

        # ADMIN adds a new governor
        scenario += whitelist.remove_governor(Addresses.GOVERNOR).run(sender=Addresses.ADMIN)

        # Verify that the governor is removed
        scenario.verify(~whitelist.data.governors.contains(Addresses.GOVERNOR))

    @sp.add_test(name="remove_governor fails if a non-admin address calls it")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist()

        scenario += whitelist

        # ALICE tries to add new governor
        scenario += whitelist.remove_governor(Addresses.GOVERNOR).run(
            sender=Addresses.ALICE,
            valid=False,
            exception=Errors.NOT_ALLOWED,
        )

    ################
    # propose_admin
    ################

    @sp.add_test(name="propose_new_admin allows admin to propose a new admin")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist()

        scenario += whitelist

        # ADMIN proposes a new admin
        scenario += whitelist.propose_new_admin(Addresses.ALICE).run(sender=Addresses.ADMIN)

        # Verify that new admin is proposed
        scenario.verify(whitelist.data.proposed_admin.open_some() == Addresses.ALICE)

    @sp.add_test(name="propose_new_admin fails if non admin address calls it")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist()

        scenario += whitelist

        # RANDOM proposes a new admin
        scenario += whitelist.propose_new_admin(Addresses.ALICE).run(
            sender=Addresses.RANDOM, valid=False, exception=Errors.NOT_ALLOWED
        )

    ########################
    # accept_administration
    ########################

    @sp.add_test(name="accept_administration allows proposed admin to take over")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist(proposed_admin=sp.some(Addresses.ALICE))

        scenario += whitelist

        # ALICE takes over
        scenario += whitelist.accept_administration().run(sender=Addresses.ALICE)

        # Verify that ALICE is the new admin
        scenario.verify(whitelist.data.admin == Addresses.ALICE)

    @sp.add_test(name="accept_administration fails if no admin is propsoed")
    def test():
        scenario = sp.test_scenario()

        whitelist = Whitelist()

        scenario += whitelist

        # ALICE tries to take over even though no admin is proposed
        scenario += whitelist.accept_administration().run(
            sender=Addresses.ALICE, valid=False, exception=Errors.NO_ADMIN_PROPOSED
        )

    @sp.add_test(name="accept_administration fails if incorrect address tries to take over")
    def test():
        scenario = sp.test_scenario()

        # ALICE is the new proposed admin
        whitelist = Whitelist(proposed_admin=sp.some(Addresses.ALICE))

        scenario += whitelist

        # BOB tries to takes over
        scenario += whitelist.accept_administration().run(
            sender=Addresses.BOB, valid=False, exception=Errors.NOT_ALLOWED
        )

sp.add_compilation_target('whitelist', Whitelist())