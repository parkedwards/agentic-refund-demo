# Agentic refund demo

This project provides synthetic business systems for a Prefect refund remedy workflow.
The facts vary across cases, but each case stays stable across repeated tool calls.
This makes the workflow realistic, repeatable, and auditable.

## System shape

The active plan uses a three-by-two remedy matrix.
The graph enforces every dependency between agents.

```text
case_id
  └─ Resolve customer [AgentNode]
     └─ Identify purchase [AgentNode]
        └─ Gather refund facts [AgentNode]
           └─ Classify claim [AgentNode]
              ├─ Item issue
              │  └─ Choose item remedy [AgentNode]
              │     ├─ Original refund ────────────────┐
              │     └─ Replacement ─> Create replacement
              ├─ Delivery issue                        │
              │  └─ Choose delivery remedy             │
              │     ├─ Carrier review ─> Open carrier review
              │     └─ Exception refund                │
              │        └─ Manager approval ────────────┤
              └─ Preference issue                      │
                 └─ Choose preference remedy           │
                    ├─ Store credit ─> Issue store credit
                    └─ Denied ─> Explain denial        │
                                                       │
                              Issue refund <────────────┘
                                   └─ Payment Sandbox MCP

              Terminal result ─> Report outcome ─> case_result
```

The `issue_refund` agent is the only agent with access to the Payment Sandbox MCP server.
The graph starts this agent only after a policy-approved refund or an approved manager exception.
The Payment Sandbox validates the request and owns idempotency before it records an effect.

The replacement, store-credit, and carrier-review agents use the separate Remedy Sandbox MCP server.
Each write tool validates that its action matches the authoritative scenario and policy clauses.

## Scripted cases

- `CASE-1047` follows item issue to an automatic original-payment refund.
- `CASE-2083` follows delivery issue to manager approval and an exception refund.
- `CASE-3149` follows preference issue to a final-sale denial.
- `CASE-4772` stops for manual identity work because two customers match.
- `CASE-5226` follows item issue to an automatic replacement.
- `CASE-6814` follows preference issue to automatic store credit.
- `CASE-7352` follows delivery issue to an automatic carrier review.

Any other valid case ID selects one of these data shapes from a stable SHA-256 hash.
The generated customer, order, and payment IDs also come from that hash.

## MCP entrypoints

Connect the same GitHub repository to five separate Horizon projects.
Use `pyproject.toml` as the dependency path.

- Refund Identity uses `src/refund_demo/servers/identity.py:mcp`.
  It exposes `get_support_case`, `search_customers`, and `find_candidate_purchases`.
- Refund Facts uses `src/refund_demo/servers/facts.py:mcp`.
  It exposes the order, payment, history, risk, and remedy-option read tools.
- Refund Policy uses `src/refund_demo/servers/policy.py:mcp`.
  It exposes `get_active_refund_policy` and `get_policy_clause`.
- Payment Sandbox uses `src/refund_demo/servers/payment.py:mcp`.
  It exposes payment reads, `issue_refund`, and refund receipt reads.
- Remedy Sandbox uses `src/refund_demo/servers/remedies.py:mcp`.
  It exposes replacement, store-credit, carrier-review, and receipt tools.

The read tools return stable evidence IDs and source times.
No read tool returns a remedy decision.
The branch agents combine the facts with the active policy.

## Local setup

```bash
uv sync
uv run pytest
uv run ruff check .
```

Start one MCP server locally with its module path.

```bash
uv run python -m refund_demo.servers.remedies
```

## Hosted setup

Push the repository and build each MCP entrypoint in Horizon.
Each Horizon build resolves the selected branch or pull request to an exact Git commit.

Horizon protects hosted deployments by default.
The execution plan must use a Prefect block reference for each authorization header.
Do not put a Horizon API key in the plan document.

The versioned plan source is `plans/refund-remedy-matrix.json`.
Update its hosted URLs after the Payment Sandbox and Remedy Sandbox builds succeed.
Validate the plan before publication.

## Action boundaries

The payment agent calls `issue_refund` without an idempotency key.
The Payment Sandbox derives the key from the authoritative case and payment IDs.
It rejects identity changes, stale policy versions, invalid clauses, excessive amounts, unsettled payments, disputes, and final-sale requests.

The Remedy Sandbox derives one idempotency key for each case, order, and action.
It rejects the wrong action, unavailable replacements, unsupported store credit, unnecessary carrier reviews, stale policy versions, and high-risk requests.

The action ledgers use process memory.
They support idempotent retries in one running Horizon instance, but they are not durable across restarts or separate instances.
Do not present these ledgers as a production payment or commerce design.

## Demo validation

Test the automatic refund route with `CASE-1047`.
Confirm that the plan selects item issue, original refund, and `issue_refund`.
Confirm that the manager node and all non-payment action nodes are skipped.
Call `list_refunds` and verify one receipt with `effect_count: 1`.

Test the manager route with `CASE-2083`.
Confirm that no refund exists before approval.
Approve the request with a reviewer note.
Confirm that `issue_refund` starts only after approval and returns one receipt.

Test the other matrix routes with `CASE-5226`, `CASE-6814`, and `CASE-7352`.
Confirm that each run starts only its selected terminal action node.
Call `list_remedy_actions` and verify one matching receipt for each case.

Test the denial route with `CASE-3149`.
Confirm that all write agents are skipped and the final `case_result` has `effect_count: 0`.

## Legacy deployment example

The repository retains `flows/issue_refund.py` as an inactive alternative that runs the refund boundary through a Prefect deployment.
The remedy matrix plan does not contain a `DeploymentNode` and does not use that flow.
