import { TezosToolkit } from "@taquito/taquito";
import { loadContract, deployContract, getSortedTokenSet } from "./utils";

export type DeployParams = {
  // Admin for the whitelist
  admin: string;

  // Tezos instance
  tezos: TezosToolkit;

  // The DAO address
  daoAddress: string;

  // Token set accepted in the round
  tokenSet: Array<string>;

  // Security deposit amount in tez
  securityDeposit: string;

  // Stablecoin accepted as sponsor in round
  stablecoinAddress: string;

  // Community fund contract
  communityFundAddress: string;

  // Match round contribution starting time
  contributionStart: string;

  // Match round contribution ending time
  contributionEnd: string;

  // Match round cooldown ending time
  cooldownEnd: string;
};

export const deploy = async (deployParams: DeployParams): Promise<void> => {
  try {
    // Whitelist

    const whitelistStorage = {
      prim: "Pair",
      args: [
        {
          prim: "Pair",
          args: [{ string: deployParams.admin }, [{ string: deployParams.admin }]],
        },
        { prim: "Pair", args: [{ prim: "None" }, []] },
      ],
    };

    const whitelistCode = loadContract(`${__dirname}/../../michelson/whitelist.tz`);

    console.log(">> Deploying Whitelist Contract \n\n");

    const whitelistAddress = await deployContract(
      whitelistCode,
      whitelistStorage,
      deployParams.tezos
    );

    console.log(`Whitelist deployed at: ${whitelistAddress}\n\n`);

    // Donation Handler

    const donationHandlerStorage = {
      prim: "Pair",
      args: [
        { string: deployParams.daoAddress },
        {
          prim: "Pair",
          args: [{ prim: "None" }, { string: whitelistAddress }],
        },
      ],
    };

    const donationHandlerCode = loadContract(`${__dirname}/../../michelson/donation_handler.tz`);

    console.log(">> Deploying Donation Handler Contract \n\n");

    const donationHandlerAddress = await deployContract(
      donationHandlerCode,
      donationHandlerStorage,
      deployParams.tezos
    );

    console.log(`Donation Handler deployed at: ${donationHandlerAddress}\n\n`);

    // Matching Round

    const tokenSetObj = await getSortedTokenSet(deployParams.tokenSet, deployParams.tezos);

    const matchingRoundStorage = {
      prim: "Pair",
      args: [
        {
          prim: "Pair",
          args: [
            { prim: "Pair", args: [[], []] },
            { prim: "Pair", args: [[], { prim: "False" }] },
          ],
        },
        {
          prim: "Pair",
          args: [
            {
              prim: "Pair",
              args: [
                {
                  prim: "Pair",
                  args: [
                    { string: deployParams.contributionStart },
                    {
                      prim: "Pair",
                      args: [
                        { string: deployParams.contributionEnd },
                        {
                          prim: "Pair",
                          args: [
                            { string: deployParams.cooldownEnd },
                            { string: "1970-01-01T00:00:00Z" },
                          ],
                        },
                      ],
                    },
                  ],
                },
                {
                  prim: "Pair",
                  args: [
                    tokenSetObj,
                    {
                      prim: "Pair",
                      args: [
                        { int: deployParams.securityDeposit },
                        {
                          prim: "Pair",
                          args: [
                            { string: deployParams.daoAddress },
                            {
                              prim: "Pair",
                              args: [
                                { string: deployParams.stablecoinAddress },
                                {
                                  prim: "Pair",
                                  args: [
                                    { string: donationHandlerAddress },
                                    { string: deployParams.communityFundAddress },
                                  ],
                                },
                              ],
                            },
                          ],
                        },
                      ],
                    },
                  ],
                },
              ],
            },
            {
              prim: "Pair",
              args: [[], { prim: "Pair", args: [{ int: "0" }, { int: "0" }] }],
            },
          ],
        },
      ],
    };

    const matchingRoundCode = loadContract(`${__dirname}/../../michelson/matching_round.tz`);

    console.log(">> Deploying Matching Round Contract\n\n");

    const matchingRoundAddress = await deployContract(
      matchingRoundCode,
      matchingRoundStorage,
      deployParams.tezos
    );

    console.log(`Matching Round deployed at: ${matchingRoundAddress}\n\n`);
  } catch (err) {}
};
