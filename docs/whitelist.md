# Whitelist

The Whitelist contract handles the whitelisting feature on Kickflow. Only addresses stored in the whitelist contract can make their contribution count in the CLR match of a project entry.

## Storage

- `admin` : Tezos address that has administrtive rights in the whitelist. Here, this is an address controlled by a private key owned by Kickflow.
- `proposed_admin` : The intermediary proposed admin in a two step admin changing process.
- `governors` : A set of Tezos addresses who are allowed to whitelist other addresses.
- `whitelist` : A set containing the whitelisted addresses.

## Entrypoints

- `whitelist_addresses` : Called by one of the governors to whitelist a LIST of tezos addresses.
- `verify_whitelisted` : Can be called to verify whether an address is whitelisted. Call to this entrypoint fails if the address is not whitelisted.
- `add_governor` : Called by admin to add a new governor.
- `remove_governor` : Called by admin to remove an existing governor.
- `propose_new_admin` : Called by current admin to propose a new admin.
- `accept_administration` : Called by the proposed admin address to up the administration of the whitelist.

## Whitelisting Criteria on Kickflow

- As mentioned earlier- on Kickflow, only whitelisted addresses will be allowed to include their contribution in the CLR match calculation of a project entry. This is done as a step to prevent uncontrolled number of pseudonymous identities showing up on the system.
- Profiles on Kickflow with a Github/Twitter account older than 2 years will be allowed to whitelist one address. A whitelisting request can be sent to our servers through our user interface.
