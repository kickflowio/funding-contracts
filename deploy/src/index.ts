import { DeployParams, deploy } from "./deploy";
import { TezosToolkit } from "@taquito/taquito";
import { InMemorySigner } from "@taquito/signer";

const Tezos = new TezosToolkit("https://granadanet.smartpy.io");

Tezos.setProvider({
  signer: new InMemorySigner(process.env.PRIVATE_KEY as string),
});

// Admin address of the whitelist contract
const ADMIN = "tz1ZczbHu1iLWRa88n9CUiCKDGex5ticp19S";

// DAO address
const DAO_ADDRESS = "KT1D43mie6Y74voYLuE6XgBVWH1cjFuvtcsG";

// Community fund address
const COMMUNITY_FUND_ADDRESS = "KT19hqfKLmyWMTdQSigiQdMjdtKLBasveLtV";

// Stablecoin address used in the round
const STABLECOIN_ADDRESS = "KT1BU6kT5ht1K2pXDdgxyr6zw4NVMtDhoPiJ";

// Security deposit for the round in mutez
const SECURITY_DEPOSIT = "10000000";

// Contribution start time
const CONTRIBUTION_START = "2021-08-01T18:00:00+05:30";

// Contribution end time
const CONTRIBUTION_END = "2021-08-07T18:00:00+05:30";

// Cooldown period end time
const COOLDOWN_END = "2021-08-08T18:00:00+05:30";

// Set of token address being used for contribution in a round
const TOKEN_SET = [
  "KT1VMgEsfnBxUu997nu7sHKHUa4DXva9a3eB",
  "KT1E7uZZivBtj4iATgBTiaiHxhpgL9pfkbHr",
  "KT1CyyE1VASYXFAQTkaYKw7QVKkJuc1xrFoc",
  "KT199ba3eQ2XgBmzviAKmnoPtk5eh6VzU6HM",
  "KT1BU6kT5ht1K2pXDdgxyr6zw4NVMtDhoPiJ",
];

const deployParams: DeployParams = {
  admin: ADMIN,
  tezos: Tezos,
  daoAddress: DAO_ADDRESS,
  communityFundAddress: COMMUNITY_FUND_ADDRESS,
  stablecoinAddress: STABLECOIN_ADDRESS,
  securityDeposit: SECURITY_DEPOSIT,
  tokenSet: TOKEN_SET,
  contributionStart: CONTRIBUTION_START,
  contributionEnd: CONTRIBUTION_END,
  cooldownEnd: COOLDOWN_END,
};

void deploy(deployParams);
