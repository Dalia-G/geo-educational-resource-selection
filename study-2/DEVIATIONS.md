# Study 2: Deviations and Execution Events

No deviation from the frozen protocol (`protocol_study2.md`, manifest timestamp 2026-10-29T07:08:19.724708Z) affected the inputs, the schedule, the scoring, or the analysis. The prespecified analysis script was run unchanged on the complete set of 1296 results.

## Execution events (reported for transparency; handled as the protocol specifies)

1. **Transport retries.** HTTP 429/5xx responses and timeouts were retried with the identical request body (at most three retries; back-off 15/30/60 s). Successful attempt numbers: attempt 1, 972; attempt 2, 231; attempt 3, 74; attempt 4, 17 (`analysis/replay_check.json`).
2. **Two transport-exhausted requests.** `M1__Q012_T__rep2__baseline` and `M2__Q010_T__rep2__faq_geo` (2026-10-29, 08:45–09:02 UTC) exhausted all four attempts: the credential session of the HTTPS proxy expired while a request was pending, and the retries failed with proxy connection errors. As prespecified, both count as failures on every endpoint. A descriptive sensitivity analysis that drops the two affected blocks is reported in the manuscript; it does not change any conclusion.
3. **Credential-service interruption.** Between 10:07 and 10:26 UTC the credential service refused to start runner sessions (`credential resolution denied`), so no requests were sent in that interval. The wrapper script `scripts/drive.sh` (an operational loop, not part of the frozen manifest) was then edited to wait 60 s after a refused session before trying again. The runner, its inputs, and the frozen files were not changed, and the runner re-verified the frozen manifest at every start.
4. **Model identity.** The returned model identifier never changed (M1: nvidia/nemotron-3-ultra-550b-a55b; M2: minimaxai/minimax-m3.1-flash).
