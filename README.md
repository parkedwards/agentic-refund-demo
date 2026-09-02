# Agentic refund demo

This project provides synthetic business systems for a Prefect agentic refund workflow.
The facts vary across cases, but each case stays stable across repeated tool calls.
This makes the workflow realistic, repeatable, and auditable.

## System shape

```text
Execution plan
├─ Identify purchase [AgentNode]
│  └─ Refund Identity MCP
├─ Adjudicate refund [AgentNode]
│  ├─ Refund Facts MCP
│  └─ Refund Policy MCP
├─ Manager approval [HumanInputNode]
├─ Issue policy refund [DeploymentNode]
│  └─ issue-refund-sandbox flow
│     └─ Payment Sandbox MCP
└─ Issue approved exception [DeploymentNode]
   └─ issue-refund-sandbox flow
      └─ Payment Sandbox MCP
```

Do not attach the Payment Sandbox MCP server to an `AgentNode`.
The deterministic child flow is the only intended caller of `issue_refund`.

## Scripted cases

| Case ID | Expected outcome | Important facts |
| --- | --- | --- |
| `CASE-1047` | Automatic approval | A low-value damaged item, low risk, and a settled payment |
| `CASE-2083` | Manager review | A USD 189 delivery claim with conflicting carrier evidence |
| `CASE-3149` | Denial | A delivered final-sale item |
| `CASE-4772` | Manual identity work | Two customers use the same email and partial order hint |

Any other valid case ID selects one of these data shapes from a stable SHA-256 hash.
The generated customer, order, and payment IDs also come from that hash.

## MCP entrypoints

Connect the same GitHub repository to four separate Horizon projects.
Select a different entrypoint for each project.

| Hosted server | Entrypoint | Tools |
| --- | --- | --- |
| Refund Identity | `src/refund_demo/servers/identity.py:mcp` | `get_support_case`, `search_customers`, `find_candidate_purchases` |
| Refund Facts | `src/refund_demo/servers/facts.py:mcp` | `get_order_facts`, `get_payment_facts`, `get_refund_history`, `get_risk_signals` |
| Refund Policy | `src/refund_demo/servers/policy.py:mcp` | `get_active_refund_policy`, `get_policy_clause` |
| Payment Sandbox | `src/refund_demo/servers/payment.py:mcp` | `get_authoritative_payment`, `issue_refund`, `get_refund_receipt`, `list_refunds` |

The read tools return evidence IDs and source times.
No read tool returns a refund decision.
The adjudication agent must combine the facts with the policy.

## Local setup

```bash
uv sync
uv run pytest
uv run ruff check .
```

Inspect a hosted server locally with an in-memory FastMCP client through the tests.
You can also start one entrypoint with its module path.

```bash
uv run python -m refund_demo.servers.identity
```

## Deploy from GitHub

Push this project to a GitHub repository and connect that repository to Horizon.
Create four Horizon projects from the same repository.
Use `pyproject.toml` as the dependency path and use the entrypoint from the table above.
Each Horizon build resolves the selected branch or pull request to an exact Git commit.
Deploy each successful build to get the four MCP URLs for the execution plan and child flow.

Horizon protects hosted deployments by default.
The execution plan must use a Prefect block reference for an authorization header.
Do not put a Horizon API key in the plan document.

## Deterministic refund flow

The example child flow is `flows/issue_refund.py:issue_refund`.
Install its optional dependency before you deploy or serve it.

```bash
uv sync --extra flow
```

Set these environment variables for the child flow runtime:

```text
PAYMENT_SANDBOX_MCP_URL=https://<payment-server-slug>.fastmcp.app/mcp
HORIZON_API_KEY=<service-account-key>
```

The child flow performs these steps:

1. It reads the authoritative payment from the Payment Sandbox MCP server.
2. It checks the payment ID, currency, settlement state, dispute state, and refundable balance.
3. It calls `issue_refund` with a stable idempotency key.
4. It creates a Prefect Markdown artifact with the receipt and decision evidence.

Use the resulting Prefect deployment UUID in both refund `DeploymentNode` entries.
The reviewed node must also require the `manager_approval.approved` output as a separate input.
That input is a graph gate and is not a child flow parameter.

## Demo validation

Run the manager-review case first.

1. Start the execution plan with `CASE-2083`.
2. Confirm that the graph pauses at manager approval.
3. Call `list_refunds(case_id="CASE-2083")` and confirm that it returns zero receipts.
4. Approve the request.
5. Confirm that one refund child flow starts.
6. Open the child flow artifact and record its refund ID.
7. Call `list_refunds(case_id="CASE-2083")` and confirm that it returns one receipt with `effect_count: 1`.

Then run the denial case.

1. Start the execution plan with `CASE-3149`.
2. Confirm that the adjudication node selects `denied`.
3. Confirm that both refund deployment nodes are skipped.
4. Call `list_refunds(case_id="CASE-3149")` and confirm that it returns zero receipts.

## Demo-only limit

The Payment Sandbox ledger uses process memory.
It supports idempotent retries in one running Horizon instance, but it is not durable across restarts or separate instances.
Use the Prefect child flow and receipt artifact as the durable record for the design-partner demo.
Do not present the in-memory ledger as a production payment design.
