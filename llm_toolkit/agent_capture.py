"""
llm_toolkit/agent_capture.py — the LLMCapture seam (cassette / record-replay for model calls).

THE PROBLEM
  An LLM call is the single most non-deterministic step in any agent: temperature sampling, GPU
  floating-point reassociation across heterogeneous hardware, server-side model swaps, and variable
  latency all mean "run the same prompt twice, get different bytes." Naive replay of an agent therefore
  drifts and the audit is worthless.

THE SEAM (do NOT try to make the model deterministic — capture it)
  At LIVE time, every model call goes through LLMCapture.call(...). The seam executes the call once and
  records EVERYTHING needed to reproduce the decision downstream:
      prompt, system_instructions, model, seed, params, response_text, tokens, logprobs, fingerprint
  all canonicalized and stored under inputs["_llm"][label].
  At REPLAY/AUDIT time, LLMCapture.replay(inputs) returns those captured bytes for the same label and
  NEVER touches the live model or a GPU again -> bit-perfect execution on any host.

  Only the model boundary needs to be routed through the seam; the surrounding agent logic is untouched.

HONEST BOUNDARY
  Capturing the response proves WHAT the model returned and UNDER WHICH prompt/params — not that the
  answer was correct. Integrity is not truth.
"""
import time

import agent_core as core

_LLM_KEY = "_llm"


class CaptureError(Exception):
    pass


# --------------------------------------------------------------------------------------------------
# A fully isolated mock client. No SDK, no network. Deterministic-by-seed so the demo is repeatable,
# but it simulates real-world flight latency and exposes the same surface a thin openai/anthropic
# wrapper would (prompt in -> {text, tokens, logprobs, model, system_fingerprint} out).
class MockLLMClient:
    """Stand-in for a real provider client. Swap for a ~20-line wrapper around openai/anthropic that
    returns the same dict shape; the capture seam and audit court do not care which is underneath."""
    def __init__(self, model="mock-gpt-4o-2025-01", flight_ms=35.0):
        self.model = model
        self.flight_ms = flight_ms  # simulated network + inference latency

    def complete(self, prompt, system, seed, temperature=0.0, scripted=None):
        # Simulate the real cost the toolkit is measuring against (the "network flight time").
        time.sleep(self.flight_ms / 1000.0)
        if scripted is not None:
            text = scripted
        else:
            # Deterministic pseudo-generation: stable for a given (prompt, system, seed) triple.
            h = abs(hash((prompt, system, int(seed)))) % 1000
            text = "ACK[%03d]: %s" % (h, prompt[:48])
        tokens = text.split()
        # logprobs are exactly the kind of float that drifts across GPUs -> canonicalized on capture.
        logprobs = [round(-0.001 * (i + 1) - len(t) * 1e-4, 8) for i, t in enumerate(tokens)]
        return {
            "text": text,
            "tokens": tokens,
            "logprobs": logprobs,
            "model": self.model,
            "system_fingerprint": "fp_%s" % (abs(hash(self.model)) % 10**8),
        }


# --------------------------------------------------------------------------------------------------
class LLMCapture:
    """Record at live time; replay captured values at audit time. Captured payloads live under
    inputs["_llm"][label], canonicalized, so they are part of the content-addressed frame and the hash
    chain — tampering with a captured prompt, token, or logprob breaks the ledger at that exact step."""

    def __init__(self, client=None):
        self._mode = "record"
        self._client = client or MockLLMClient()
        self._cap = {}

    @classmethod
    def replay(cls, sealed_inputs):
        c = cls(client=None)
        c._mode = "replay"
        c._cap = dict(sealed_inputs.get(_LLM_KEY, {}))
        return c

    def call(self, label, prompt, system, seed, temperature=0.0, scripted=None):
        """The single funnel for every model interaction.
        LIVE   -> execute, canonicalize, and record the full payload under `label`.
        REPLAY -> return the previously recorded payload for `label`; never call the model."""
        if self._mode == "replay":
            if label not in self._cap:
                raise CaptureError(
                    "no captured LLM payload for %r (agent took an un-captured branch on replay)" % label)
            return self._cap[label]
        raw = self._client.complete(prompt, system, seed, temperature=temperature, scripted=scripted)
        record = core._canon({
            "prompt": prompt,
            "system": system,
            "model": raw["model"],
            "seed": seed,
            "params": {"temperature": temperature},
            "response_text": raw["text"],
            "tokens": raw["tokens"],
            "logprobs": raw["logprobs"],
            "system_fingerprint": raw["system_fingerprint"],
        })
        self._cap[label] = record
        return record

    def sealed_inputs(self, business_inputs):
        """Merge the agent's business inputs with every captured model payload into the frame's `inputs`."""
        out = dict(business_inputs)
        out[_LLM_KEY] = dict(self._cap)
        return out


def captured_payloads(sealed_inputs):
    """Read-only view of the captured LLM payloads (for audit display)."""
    return dict(sealed_inputs.get(_LLM_KEY, {}))


def verify_replay_determinism(transition_fn, sealed_inputs, n=3):
    """Leak detector: run transition_fn n times against the sealed inputs; if outputs differ, an LLM call
    or other nondeterministic read is NOT routed through the capture seam. Cheap CI guard before trusting
    a ledger for replay."""
    first = core.canonical_bytes(transition_fn(sealed_inputs))
    for i in range(1, n):
        if core.canonical_bytes(transition_fn(sealed_inputs)) != first:
            return False, "nondeterministic output on run %d/%d -- a model call is not behind LLMCapture" % (i + 1, n)
    return True, "deterministic across %d replays" % n
