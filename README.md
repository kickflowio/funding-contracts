# Kickflow Funding Round Contracts

Kickflow Funding Rounds are based on the concept of Quadratic Match-funding and are conducted over a stipulated period of time. These rounds are handled entirely by Kickflow's DAO - [flow-dao](https://github.com/kickflowio/flow-dao). The contracts in this repository enables the funding round to be held entirely on-chain.

## Initiation of a new Round

Everytime a new round is to conducted, a fresh Matching Round contract is deployed and a proposal is submitted in the DAO for the approval of the round. If the round is approved, the address of the freshly deployed contract is set in the Donation Handler contract and the round is activated.

![Initiation diagram](https://i.ibb.co/jWWq712/Untitled-Diagram-2.png)

## Lifecycle of a round

Right after a round is approved by the DAO, it is opened up to sponsorship collection and project entries. Sponsoring and entries continue for a pre-decided period of time (specified in the proposal). All sponsoring is done in a stablecoin. Post this, the community can make their contribution count in the CLR match of the projects that have entered the round. Once the contribution period is over, there is a brief cooldown period, followed by which the DAO sets the CLR matches of the entries.
The projects can then retrieve their match amount after a brief challenge period when the clr matches set by the DAO can be disputed and reset through another proposal.

![Lifecycle diagram](https://i.ibb.co/3BGT1Yh/Untitled-Diagram-6.png)

## Development

The funding contracts are written in SmartPy. To know more, view SmartPy's [documentation](https://docs.smartpy.io/).

### Smart Contracts

- `donation_handler.py` : Relays donations to the projects and records the details in the matching round contract.
- `matching_round.py` : Handles the entire funding round - sponsor collection, contributions & match withdrawals.
- `whitelist.py` : Handles the address whitelisting logic of Kickflow.

View the contract storage and entrypoint descriptions [here](https://github.com/kickflowio/funding-contracts/tree/master/docs). For more context view our [docs](https://kickflow.gitbook.io/kickflow-documentation/)

### Folders

- `deploy` : Scripts assisting deployment of the contracts.
- `helpers` : Scripts assisting test scenarios in contracts.
- `michelson` : Compiled michelson code of the contracts.
- `types` : Scripts representing the types used in the contracts.

### Compilation

A shell script has been provided to assist compilation of the contracts. The script can be run using-

```shell
$ bash compile.sh
```

The compiled michelson files are stored in the michelson folder.

### Deployment

View the README in the [deploy](https://github.com/kickflowio/funding-contracts/tree/master/deploy) folder to know the deployment process.
