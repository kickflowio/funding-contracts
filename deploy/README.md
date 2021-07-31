# Deploy

The scripts provided in this folder assist the deployment of funding contracts. We have used [Taquito](https://tezostaquito.io/) library to simplify the process.

## Installing Dependencies

To install the dependencies run:

```
$ npm install
```

## Preparing Storage

The storage fields which are required to be mentioned pre-deployment can be set in the `index.ts` file in the `src` folder. The fields to be set are

- `ADMIN` : Admin address of the whitelist contract
- `DAO_ADDRESS` : Tezos address of deployed DAO contract
- `COMMUNITY_FUND_ADDRESS` : tezos address of deployed community fund contract.
- `STABLECOIN_ADDRESS` : The address of the stablecoin accepted as sponsor in the round.
- `SECURITY_DEPOSIT` : Security deposit amount of a round (in mutez)
- `CONTRIBUTION_START` : Time at which contributions to a round starts
- `CONTRIBUTION_END` : Time at which contributions to a round ends
- `COOLDOWN_END` : Time at which cooldown period ends
- `TOKEN_SET` : List of addresses of tokens being accepted as a contribution in the round.

## Deployment

Once the storage is prepared, the deployment can be done by providing a private key as an environment variable and running `index.ts`:

```
$ PRIVATE_KEY=<Your private key> npx ts-node ./src/
```
