# Pinned gameplay verifier and backend settlement

This checkpoint verifies the actual game model as a bounded server worker and its authenticated settlement broker. Ordinary app integration is a separate workstream in progress; the installed ordinary QA2 APK remains81. It does not certify a live payment, hosted release or all connected pages.

The worker uses the existing eleven live M46/M48 model dependencies and all fifty approved level definitions. No game engine source, level mask, artwork, rocket/bomb rule or cascade timing changes are included. A SHA256 manifest pins the model, worker and level inputs. Pins digest: `f3603ca53ebe070610473bd18524cc4765a85b368dfeb2f8518d987ec933d70f`.

## Model and authority boundaries

The server owns the player, attempt, seed, level/configuration, starting-item receipt and paid tool/continue receipts. The public request can append only ordered, bounded swap/tap actions and request a specific tool or continuation. It cannot supply a win, board checkpoint, seed, reward, paid receipt or private verifier credential.

The broker replays the complete accepted history outside SQLite write transactions, then checks the current account, attempt, configuration, action prefix, wallet and worker lease before committing. A tool is debited only with its verified action prefix; a continuation requires a verified zero-move state and atomically deducts900 coins/adds5 moves. First-clear rewards and progression commit once. Lost responses reuse the same operation; ordinary infrastructure failures remain pending. No-legal-moves acknowledgement preserves the existing loss flow.

The approved Windows bundle has176 hashed files. Its wrapper verifies the complete bundle, uses a suspended process assigned to a Windows Job Object before execution, enforces time/memory/process limits, scrubs inherited environment and captures no worker logs. A named mutex also caps actual cross-process worker concurrency independently of host-clock lease changes. The database lease and result fencing separately protect credits. The current wrapper fails closed on unsupported operating systems; the backend API is portable, but this verified native worker deployment currently needs Windows. A Linux worker would require its own build and parity evidence.

A narrowly bound response from the approved executable can identify a trusted model fault. That releases the attempt without a life loss and refunds reserved starting items. Previously committed tools/continues stay spent; a prospective uncommitted tool stays uncharged. A client error, timeout, arbitrary process failure or forged fault cannot request that refund. The positive fault controls are synthetic process/orchestration controls; no naturally occurring fault on the real Unity binary has been demonstrated.

Technical resource bounds currently allow128 appended actions per request and1,000 actions per attempt history. Capacity is checked before a paid debit. These bounds are explicit integration limits, not an approved new price table or a silently charged continuation.

## Actual evidence

| Execution | Verified result |
| --- | --- |
| Pinned Unity2022.3.62f3 native corpus | 3,937 checks,371 cases,50 levels,397 actions,20 tools,one continuation,200 starting-item placements;397 full-checkpoint comparisons and397 checkpoint roundtrips; six negative controls. |
| Actual standalone Windows Mono worker | All371 cases pass as separate bounded processes against native full-checkpoint fixtures. Successful model outcomes and exact result hashes are retained. |
| Actual Android release IL2CPP ARM64 fixture | All371 cases pass against the same native fixtures on QA2/5558, using a separate fixed package. Ordinary game preferences and profile hashes are unchanged. APK SHA256 `4c640378544383aa39ce8db5e5f528fec2a7beebe297e347f7055526d4c31526`. This is a model parity fixture, not normal game UI or physical-device testing. |
| Expanded backend suite | All304 service/ASGI/SQLite tests pass with unchanged before/after hashes for71 exact archived inputs. The opt-in integration uses the actual approved Unity worker: authenticated out-of-moves verification →900-coin/+5 continuation →Won →50 coins/one star, with one progression/reward receipt after a duplicate completion. Test progression/seed are explicit trusted fixture setup; there is no public override endpoint. |

The full standalone corpus used the original sealed wrapper, retained with its report. Later fault/mutex hardening is covered by the expanded backend tests and real broker integration; the model bundle/pins remain identical. Wrapper tests using small Python processes are labelled separately from real Unity execution.

Failed attempts are preserved. The first worker build produced a binary but failed while restoring an invalid empty Editor scene setup; the corrected builder records recovery and produces a fresh success report. The first Android fixture build lacked the built-in Android JNI module needed for explicit intent scope; only the isolated fixture manifest was corrected before the successful build. Neither fix changes ordinary game assets or the model.

## App acceptance still required

Checkpoint-only restoration sorts piece identities and can change dictionary insertion order. The native corpus proves checkpoint roundtrips, not all future restored commands. Separate connected-client work tests future command parity and Continue/Shop restoration before accepting it. App-side identity/wallet selection, tools, terminal flow, repeated continuation, social pages, reward claims and Android restart behavior need their own connected evidence. No local wallet is silently uploaded or merged.

Production hosting/TLS, Console application/products, durable release signing, Russian legal/support/retention configuration, staffed moderation and actual RuStore sandbox/banking-return/upgrade tests remain required. Earlier dense-effect stalls and physical-device performance limitations are unchanged.

Evidence: `Verification/Evidence/ServerReplay83/Comparison.html`; reproducible validation: `Verification/Tools/collect_server_replay83.py`. The collector validates frozen inputs and reports rather than labelling later untested edits as this checkpoint.
