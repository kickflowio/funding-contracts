import { TezosToolkit } from "@taquito/taquito";
import BigNumber from "bignumber.js";
import fs = require("fs");

export const loadContract = (filename: string): string => {
  const contractFile = filename;
  const contract = fs.readFileSync(contractFile).toString();
  return contract;
};

export const getSortedTokenSet = async (tokenSet: string[], tezos: TezosToolkit): Promise<any> => {
  // Initialize token set with the packed bytes for 'TEZ_IDENTIFIER';
  const tokenSetObj = [{ bytes: "05010000000e54455a5f4944454e544946494552" }];
  for (const tokenAddress of tokenSet) {
    const identifier = await tezos.rpc.packData({
      data: { string: tokenAddress },
      type: { prim: "address" },
    });
    tokenSetObj.push({ bytes: identifier.packed });
  }

  // Sort the token set
  tokenSetObj.sort((a, b) => {
    if (new BigNumber(a.bytes, 16) < new BigNumber(b.bytes, 16)) return -1;
    else return 1;
  });

  return tokenSetObj;
};

export const deployContract = async (
  code: string,
  storage: object,
  tezos: TezosToolkit
): Promise<string | boolean> => {
  try {
    const originOp = await tezos.contract.originate({
      code: code,
      init: storage,
    });

    await originOp.confirmation(1);
    return originOp.contractAddress as string;
  } catch (err) {
    console.log(err);
    return false;
  }
};
