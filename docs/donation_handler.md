# Donation Handler

The Donation Handler contract relays the donations made to a project address during a funding round. It also points to the currently active Matching Round contract and records the details of the every contribution in the same.

## Storage

- `round_address` : Tezos contract address of the currently active or last activated round.
- `whitelist_address` : Tezos contract address of the whitelisting contract.
- `dao_address` : Tezos contract address of the DAO.

## Entrypoints

- `donate` : Relays the donation to the specified project entry and records the details in the Matching Round contract. It can relay tez and FA1.2 tokens. This can only be called by whitelisted addresses.
- `set_round_address` : Can be called by the DAO to set the address of the newly deployed Matching Round contract.
- `set_whitelist_address` : Can be called by the DAO to set the address of the whitelist address.

## Donation Handling Technique

As mentioned above- the Donation Handler can relay tez, as well as FA1.2 tokens. The currency of donation is represented in `BYTES` value, sent along in the `token_identifier` parameter of the `donate` entrypoint. For tez, the bytes value is retrieved by performing a michelson `PACK` on the string `"TEZ_IDENTIFIER"`, whereas for FA1.2 the same is retrieved by packing the Tezos address of the token.

Donation Handler also makes a call to the Whitelist contract to check if an incoming donation is by a whitelisted address or not. It rejects all donations that are coming through a non-whitelisted sender.
