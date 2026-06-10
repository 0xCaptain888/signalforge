# SignalForge v2.1 — System Architecture

## Overview

```
+--------------------------------------------------------------+
|  Callers (any agent: Claude / BNB Agent / LangChain / ...)    |
+---------------+----------------------+------------------------+
                | CMC Skills           | APEX on-chain jobs
                | find_skill()         | create_job -> fund -> execute
                v                      v
+--------------------------------------------------------------+
|  M-SKILL: FastAPI service (port 8000)                         |
|  POST /adjudicate  (x402 gate, $0.50 USDC)                    |
|  GET /.well-known/skill-card.json                             |
+---------------+----------------------+------------------------+
                |                      |
       +--------v---------+   +--------v----------------------+
       |  M-CORE engine    |   |  M-BNB (port 8001)            |
       |  scoring (6 rules)|   |  ERC-8004 identity            |
       |  leakage detection|   |  APEX/ERC-8183 escrow         |
       |  core.adjudicate  |   |  IPFS deliverable             |
       +--------+---------+   |  UMA OOv3 evaluation          |
                |             +-------------------------------+
                v
+--------------------------------------------------------------+
|  M-CMC: data layer                                            |
|  (1) REST  /v3/fear-and-greed/historical (proprietary)        |
|  (2) MCP   mcp.coinmarketcap.com/mcp (12 tools)               |
|  (3) x402  mcp.coinmarketcap.com/x402 ($0.01/call, Base)      |
|  provenance.py records 3-channel evidence                     |
+--------------------------------------------------------------+
```

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| Zero recompute (read outputs/*.json) | ms-level verdicts; v1 rigor fully preserved |
| edge_confidence baseline=59, 6 rules | v1 real data outputs exactly 12 |
| x402 gate $0.50 USDC/call | Application Value proof + CMC prize evidence |
| BSC Testnet only | SDK status quo; gas-free registration |
| IS-only calibration | prevents regime_weights data leakage |
| LeakageCheck keeps direction_flip fields | judges see the full leakage mechanism |

## Contracts (BSC Testnet, Chain ID 97)

```
ERC-8004 Identity:  0x8004A818BFB912233c491871b3d84c89A494BD9e
ERC-8183 Commerce:  0x3464e64dD53bC093c53050cE5114062765e9F1b6
UMA OOv3 Evaluator: 0x5f4976ACBCD2968D08273bA9f4a67FA43C4A3af3
U Token:            0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565
```

USDC on Base mainnet (x402): `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913`
