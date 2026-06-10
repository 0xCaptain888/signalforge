# SignalForge — Demo Video Script (<= 3 minutes)

## Setup checklist (before recording)
- [ ] Service running: `python -m uvicorn service.app:app --port 8000`
- [ ] UI running: `cd ui && npm run dev` (http://localhost:3000)
- [ ] BscScan tabs ready: registration tx + settled job
- [ ] BaseScan tab ready: x402 payment tx
- [ ] IPFS gateway tab ready: verdict CID
- [ ] Terminal font >= 18px; notifications off
- [ ] 1080p; record browser/terminal area only

## Shot 0 — Title (0:00-0:05)
Black slate: "SignalForge — Signal Edge Adjudicator — BNB Hack 2026 Track 2"

## Shot 1 — Problem (0:05-0:30)
Run `python scripts/07_adjudicate_demo.py`.
VO: "In the agent era, trading signals are everywhere. But most backtests are
overfitted — or worse, leaking future data. Who validates the validators?"

## Shot 2 — Product (0:30-1:00)
Open UI. Click the red "Submit leaky signal" button.
VO: "SignalForge is the referee. Give it any signal; it tells you: real alpha,
noise, or leakage — with an Edge Confidence score from 0 to 100."

## Shot 3 — Highlight (1:00-1:40)
Show: LEAKAGE DETECTED badge, gauge at 12, the Sharpe comparison bars.
VO: "This is our own v1 strategy. Naive calibration showed a tempting +0.85
Sharpe. SignalForge enforced IS-only calibration and returned the honest
verdict: leakage detected — it was -0.99 all along. That negative number is
the product working."

## Shot 4 — CMC stack (1:40-2:10)
Scroll to evidence panel. Open /.well-known/skill-card.json. Show BaseScan tx.
VO: "CMC Agent Hub, all three paths: REST for history, Data MCP for live calls,
and x402 — pay-per-request USDC on Base. That's a real settlement. Listed on
the CMC Skills Marketplace under 'signal validation'."

## Shot 5 — BNB on-chain (2:10-2:35)
BscScan: registration tx, then the job: FUNDED -> SUBMITTED -> COMPLETED.
Open the IPFS verdict.
VO: "BNB AI Agent SDK: SignalForge is a registered on-chain agent. Clients pay
into escrow, the verdict lands on IPFS, UMA's oracle validates, payment
releases. Full trustless lifecycle."

## Shot 6 — Close (2:35-2:40)
UI header with three badges lit.
VO: "SignalForge — the signal adjudicator for the agent economy. Because real
alpha shouldn't be negotiable."
