export default function AgentGovernanceBeforeMicrosoft() {
  return (
    <>
      <p>
        In February 2026, I shipped a <strong>Dharma rules engine</strong>, a{" "}
        <strong>Karma audit ledger</strong>, and an{" "}
        <strong>8-stage middleware pipeline</strong> as part of WhiteMagic's
        tool dispatch system. Two months later, Microsoft announced the Agent
        Governance Toolkit. The overlap is instructive — and the differences
        matter.
      </p>

      <h2>What We Both Built</h2>
      <p>
        Both systems share a core insight: <strong>agents need runtime
        governance, not just policy documents</strong>. When an agent can call
        tools, access memory, and execute code, governance can't be a design
        document reviewed once a quarter. It has to execute on every tool call.
      </p>
      <p>
        WhiteMagic's approach predates Microsoft's public release by several
        months, but the architectural convergence suggests the problem space
        is well-defined:
      </p>
      <ol>
        <li>
          <strong>Tool-level gating</strong>: Every tool invocation passes
          through a middleware chain that can reject, modify, or audit the
          call.
        </li>
        <li>
          <strong>Ethical ledger</strong>: A persistent, append-only log of
          claims and verdicts — not just for debugging, but for
          accountability.
        </li>
        <li>
          <strong>Voice audit</strong>: Scanning agent outputs for boundary
          violations — false claims, scope creep, unauthorized disclosures.
        </li>
      </ol>

      <h2>Where We Differ</h2>
      <p>
        Microsoft's toolkit is designed for enterprise integration —
        Azure-native, Entra ID-backed, and policy-as-code. WhiteMagic's
        governance is <strong>local-first</strong>, Python-native, and
        designed for researchers and small teams who can't or won't deploy to
        Azure.
      </p>
      <p>This matters because the governance surface is different:</p>
      <table>
        <thead>
          <tr>
            <th>Concern</th>
            <th>Microsoft AGT</th>
            <th>WhiteMagic Dharma</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Deployment model</td>
            <td>Azure cloud</td>
            <td>Local / on-prem</td>
          </tr>
          <tr>
            <td>Policy language</td>
            <td>YAML + Azure Policy</td>
            <td>Python rules + PRAT Gana</td>
          </tr>
          <tr>
            <td>Audit trail</td>
            <td>Azure Monitor</td>
            <td>Karma Ledger (SQLite/PostgreSQL)</td>
          </tr>
          <tr>
            <td>Ethical framework</td>
            <td>Compliance rules</td>
            <td>Dharma ethics + 28 Gana system</td>
          </tr>
        </tbody>
      </table>

      <h2>What I'd Do Differently</h2>
      <p>
        The biggest lesson: <strong>governance should be observable before
        it's enforceable</strong>. In the first iteration, the Dharma engine
        rejected tool calls silently. This made debugging impossible — agents
        couldn't tell why they were being blocked. The fix was adding
        structured error envelopes with <code>error_code</code>,{" "}
        <code>details</code>, and <code>retryable</code> flags on every
        rejection.
      </p>
      <p>
        The second lesson: <strong>epistemic tagging should be a first-class
        primitive</strong>. Agents confidently assert falsehoods because we
        haven't taught them to label uncertainty. Every claim from an agent
        should carry a [Proven], [Promising], [Contested], [Speculative], or
        [Mythopoetic] tag. This is now part of the WhiteMagic stable envelope
        contract.
      </p>

      <h2>The Bottom Line</h2>
      <p>
        The convergence with Microsoft validates the problem space. The
        divergence in deployment model and ethical framework is WhiteMagic's
        differentiator. If you're building agents that need runtime governance
        and can't ship your data to Azure, the architecture is ready to be
        adapted.
      </p>
    </>
  );
}
