# Wellworks — permanent Chapter 1 milestones

21 October 2026 · Unity 2022.3.62f3 · live HomeLevelFlow and durable local profile

The owner approved Wellworks as the next component after Daily Gift, including this provisional configurable schedule:

| Completed levels | Reward |
| --- | --- |
| 10 | 100 coins |
| 20 | One Rocket and one Bomb |
| 30 | 150 coins and one Hammer |
| 40 | One Orb |
| 50 | 250 coins and one Golden Seeker |

Progress comes from saved Chapter 1 first clears. Replays, failures and interruptions do not advance it. Story stars are neither consumed nor granted by Wellworks. It has no countdown, daily reset or competition. Any reached, unclaimed milestone can be claimed; earlier claims are not a prerequisite. Each stage retains its original receipt across quantity revisions. Milestone identities are their Chapter 1 level thresholds; preserve those identities when editing quantities.

`WellworksService` checks eligibility and commits the receipt plus wallet/inventory in one profile transaction. Its keys omit configuration versions so quantity changes cannot reopen a claimed threshold. The existing profile schema and reward journal require no migration. Overflow or failure before replacement cannot partially credit a reward. Failure after replacement is reconciled by reading the existing receipt; retry cannot credit twice. Animations are cosmetic and issue no rewards.

`PlayerProfileHost` attaches the service and page and replaces the old fixed `12/20` Home badge with saved progress, Ready or a completion check mark. `WellworksPage` uses the approved existing assets, safe areas, scrolling, button feedback, Back/close and five supported languages. Daily Gift and Wellworks hide each other when changing routes. No artwork, GUIDs, level masks, gameplay rules or SDK versions change.

The schedule lives in `Unity/Assets/HeartOfTheRain/App/Profile/Resources/HOTR_Wellworks/Schedule.json`. Rewards are a labelled development preview using the existing development profile; release claiming is disabled. A production authority/account service remains necessary before shipping. Local checksums and receipts do not provide anti-cheat protection.

## Verification

Evidence is under `Verification/Evidence/Wellworks`. `Verification_Summary.json` and `Comparison.html` record the final APK, explicit native visual review and installation scope when complete. Earlier Daily Gift evidence retains its preceding APK identity.

- 11,046 native Unity transaction, configuration, asset, layout, font and glyph checks pass. They include 50 simulated first clears, replay protection, all approved quantities, unchanged stars/lives, quantity revisions, production-disabled claims, overflow and pre/post-commit file failures.
- 13 connected native Play Mode checks pass: saved Home badge, disabled locked milestones, retry, lost save confirmation, shared inventories, permanent completion, Daily Gift routing and unavailable-read recovery.
- Fresh compatibility checks pass: 10,099 profile/Daily Gift assertions, 51 connected Daily Gift/gameplay checks and 530 general checks. Historical source-branch reports are restored after copying fresh results into this branch.
- Device fixtures use explicitly opt-in isolated file profiles. Their first clears are simulated through the real attempt service; they are not a natural-play campaign pass. Android taps, process restarts and rendering are recorded separately.

The final development APK is **207,591,938 bytes**, SHA-256 `5279eef53f461ef62171575461a49bd05360011fc4ceb870baff94594b1556c5`. All 4,304 non-Editor Unity inputs are frozen and revalidated against it. Two existing player files change (`PlayerProfileHost.cs`, `DailyGiftPage.cs`); eleven player files/metadata are added for the three Wellworks runtime files, configuration and opt-in probe. Existing assets, metadata, level data and gameplay code match the preceding Daily Gift build. Clean packaging preserves all 647 non-signature entry payloads and the signer; signature, alignment, ELF, seven power-up textures and portrait manifest audits pass.

The final APK passes three targeted Android cases with **21 checks and three actual taps**, plus four restart assertions at each of **320×568** and **768×1024**. Claims survive force-stop/relaunch; duplicates, early claims, precommit failure, lost commit confirmation and unavailable reads preserve the expected state. All five approved milestone quantities reach shared stock. Sixteen targeted captures, six additional portrait-size captures and both ordinary Home captures were explicitly inspected and hash-frozen: **24 images** total. The first candidate's dark footer was corrected to white and the final APK retested. Short-phone content scrolls to all five stages and the preview footer; actual Back returns Home. A tablet drag correctly leaves a fully visible panel stationary.

Both LDPlayer instances run the final APK after replacement installs without data clear. Ordinary profile and preference hashes match before/after installation and fixture runs. Display overrides change only the three documented Unity resolution keys while active; restoring 900×1600 restores the full preference hash. Ordinary profiles remain at level one, 1,250 coins, five lives and Wellworks `0/10`; synthetic test rewards did not enter them. The QA VM needed a restart before its final installation, and the main app needed a final relaunch. Their earlier exits have no established cause. `Final_Runtime_Status.json` records both final APK processes present; this is not long-session stability certification.

Repeat native verification with `powershell -NoProfile -ExecutionPolicy Bypass -File Verification/Run-Wellworks.ps1`. Targeted Android tools are `Verification/Tools/check_wellworks_device.py` and `check_wellworks_profiles.py`; they require the matching development APK and an explicit serial. `collect_wellworks_results.py` validates the frozen inputs, reports, visual hashes and installations before generating the review gallery. Rendering evidence comes from Unity/Android, not source checks.

## Remaining boundaries

The development economy is provisional. Production authentication, authoritative rewards, cloud recovery, life regeneration, exact board resume, journal archival and Rain Cup remain open. Physical-device performance, native-language editorial approval and long-session stability remain unverified. This component does not close the earlier cold heavy-power frame spikes or unexplained emulator exits. No new full Android campaign regression or reference-app gameplay parity is claimed for this UI/service change.
