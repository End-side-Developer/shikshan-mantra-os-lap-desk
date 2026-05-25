# MODEL_CARD.md — In-OS AI Assistant (optional)

This card documents AI models used **by the OS at runtime** (the optional learning assistant). It is **not** the card for AI agents developing the repo — that lives in [AGENT_CARD.md](../AGENT_CARD.md).

Format follows Mitchell et al. (2019) "Model Cards for Model Reporting", extended per EU AI Act Annex IV documentation requirements.

> **v1 default: in-OS AI assistant is OFF.** Schools opt in via the admin policy. This card describes what the assistant looks like when enabled.

---

## Model details

| Field | Value |
|---|---|
| Name | Shikshan Mantra Learning Assistant |
| Version | (deferred — first usable build in v1.1 per PLAN.md follow-ups) |
| Provider modes | `off` (default), `local-webgpu`, `server`, `cloud` |
| Local-WebGPU base | Browser-resident WebLLM with a small (≤3B) instruction-tuned model |
| Server base | Locally-hosted OpenAI-compatible endpoint (school-owned) |
| Cloud base | Any OpenAI-compatible API, declared in `policy.yml` |
| Date trained | n/a — we do not train; we ship references to external models |
| License | Per the chosen model; declared in `policy.yml` at deployment |

## Intended use

- **In scope:** answering learner questions about lesson content, suggesting next modules, explaining error messages in coding labs, translating UI strings between Hindi and English on demand.
- **Out of scope:** assessment, grading, behavioural prediction, personal recommendations beyond the catalog, mental-health responses, parental supervision substitution.

## Users

- Students (primary)
- Teachers and admins (configuration)

## Factors

- Hindi vs English performance — both languages must be supported; deployments choosing models with poor Hindi performance MUST disable the assistant for Hindi-only sessions.
- Age band — different prompts and content filters per 5-8, 9-12, 13-15, 16-18, 18+.
- Device class — local-WebGPU only viable on devices with GPU + ≥ 4 GB RAM. 2 GB-RAM target devices default to `off` or `server` mode.

## Metrics

When evaluating a candidate model for deployment:
- **Safety:** zero generations of self-harm, sexual content, hate, or violence on a 1000-prompt evaluation set covering ages 5-18.
- **Helpfulness:** ≥ 80% on a domain-specific Q&A set covering the lesson topics shipped in `modules/core/`.
- **Latency (local-WebGPU):** ≤ 5 seconds first-token on a 4 GB-RAM, integrated-GPU device.
- **Hindi quality:** independently evaluated by native speakers; threshold TBD per release.

## Training data

- We do not train.
- Deployments using `local-webgpu` or `server` must declare the model's training data lineage in `policy.yml` (`ai_provider_training_data_disclosure_url`).
- Deployments using `cloud` must disclose to users that prompts go to the cloud provider.

## Ethical considerations

- Privacy: by default, learner prompts do not leave the device. Admin policy must explicitly opt in to server/cloud modes.
- Surveillance risk: no logging of learner prompts to a central system without explicit per-user consent.
- Bias: models with documented biases on Hindi or on Indian socio-cultural contexts must be flagged in deployment.

## Caveats and limitations

- Hallucination: assistant may confidently state wrong facts. UI surfaces a "verify in the lesson" reminder on every answer.
- Refusals: safety filters may over-refuse benign questions; admins can tune per `policy.yml` `ai_refusal_strictness`.
- Offline degradation: when network is unavailable, `cloud` mode degrades to `off`; `server` mode degrades if the school server is unreachable.

## EU AI Act classification

- Likely classified as **high-risk** if used for any assessment, ranking, or evaluation of learners (Annex III, education).
- Our default scope (helper / tutor, no assessment) typically falls outside high-risk, but DEPLOYERS must classify per their jurisdiction.
- Annex IV documentation requirements are partially satisfied by this card + threat model + audit log; deployers complete the remainder for their context.

## Contact

- Questions about this card: open a Discussion in this repo.
- Vulnerabilities: SECURITY.md.
- The card is maintained by `@shikshan/safety` + `@shikshan/governance` per [CODEOWNERS](../.github/CODEOWNERS).
