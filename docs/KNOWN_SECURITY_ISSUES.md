# Known security issues

Accepted for development/alpha; hardening deferred.

Owner-authorized development/alpha risk acceptance supersedes earlier zero-HIGH/CRITICAL instructions. Do not restart remediation automatically. This is not production hardening, a clean scan, an exploitability determination, or maintainer approval to publish. Scanner execution, inventory, secret, build, runtime, migration and data-integrity failures still block.

Snapshot source: `5fb6f0a9d5c7fd89a406afb95f1ede05de1c6406`; scan: `2026-09-12T04:03:49.405735+00:00`. Historical evidence is not a newly scanned artifact. All severities are retained below. Repeated package matches and shared service images are not unique CVEs.

Raw evidence: [CI run 34671947014](https://github.com/BB-AI-Arena/MCP-Trust-Scoreboard/actions/runs/34671947014), artifact `container-security-34671947014-1` / ID `10291645171`; 41 checksums verified. Machine-readable companion: [known_security_issues.json](known_security_issues.json).

## Image identities

| Ref | Services | Image ID |
| --- | --- | --- |
| I1 | api-baseline | `sha256:2427560a14a49e5832c2589fa2a2853c66a369f4fe62466b8daff66f5b88ba32` |
| I2 | api-blast | `sha256:401a90734499573ea9b3f7babb438758964cd0d8dcad33ba2f88d2e61a8d9d22` |
| I3 | api-platform, worker-platform | `sha256:4ed27a16cef24eeef4249346db88714f36f3116daeba8bd6a4040d7b99bcaaea` |
| I4 | api-provenance | `sha256:a3a5976cfd2877453fdca4e459c041dd37bc231665703080fb60e008970d4275` |
| I5 | api-scorecard | `sha256:931c144bc07645886deddbe6618bebec7514a5730a27399fa9fb64a6b63cec54` |
| I6 | frontend-baseline | `sha256:60e71aacd30b35f37bd4ab0113e75cb30eeb8d2bddc07554ddb2792e3a0e268a` |
| I7 | frontend-blast | `sha256:297087f0d8e1d0e5d00930e533a6210c172d32e518f35c98b78abac7df9d1e15` |
| I8 | frontend-provenance | `sha256:6e0756516da8bc48eb959f116ca068e62cc9e625171a156413f79d0c8968ac31` |
| I9 | frontend-scorecard | `sha256:d82b68469958f18d504196c5dfd5befb0e792e5c90e5dedbd0f2f8c56cae38ca` |
| I10 | postgres | `sha256:51de0ac08e21eb3cac34973d0ff7c48143e8bd546a73f362358d15fc6592b5d9` |
| I11 | redis | `sha256:5509c0097c6064aa8a3b1df58f1d950e67090fffa6678ae8f3f1dc2385f12deb` |
| I12 | worker | `sha256:922057d97d46f9fc83c9f7508228494f32e5f40042ba84199415babee5b654fa` |

## Observed findings

Every row has status **"Accepted for development/alpha; hardening deferred."** Scan date is the snapshot timestamp above. Available fixes are scanner reports, not instructions to upgrade in this slice.

| Advisory | Package | Version | Severity | Images | Fix reported |
| --- | --- | --- | --- | --- | --- |
| CVE-2005-2541 | tar | 1.35+dfsg-3.1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2007-5686 | login.defs | 1:4.17.4-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2007-5686 | passwd | 1:4.17.4-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2010-4756 | libc-bin | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2010-4756 | libc6 | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2011-3374 | apt | 3.0.3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2011-3374 | libapt-pkg7.0 | 3.0.3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2011-4116 | perl-base | 5.40.1-6 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2013-4392 | libsystemd0 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2013-4392 | libudev1 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2017-18018 | coreutils | 9.7-3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2018-20796 | libc-bin | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2018-20796 | libc6 | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-1010022 | libc-bin | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-1010022 | libc6 | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-1010023 | libc-bin | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-1010023 | libc6 | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-1010024 | libc-bin | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-1010024 | libc6 | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-1010025 | libc-bin | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-1010025 | libc6 | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-9192 | libc-bin | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2019-9192 | libc6 | 2.41-12+deb13u3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2021-45346 | libsqlite3-0 | 3.46.1-7+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | bsdutils | 1:2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | libblkid1 | 2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | liblastlog2-2 | 2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | libmount1 | 2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | libsmartcols1 | 2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | libuuid1 | 2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | mount | 2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2022-0563 | util-linux | 2.41.5-0+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2023-31437 | libsystemd0 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2023-31437 | libudev1 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2023-31438 | libsystemd0 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2023-31438 | libudev1 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2023-31439 | libsystemd0 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2023-31439 | libudev1 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2024-56433 | login.defs | 1:4.17.4-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2024-56433 | passwd | 1:4.17.4-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-15649 | perl-base | 5.40.1-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-47273 | setuptools | 70.3.0 | HIGH | I1,I2,I3,I4,I5,I12 | 78.1.1 |
| CVE-2025-5278 | coreutils | 9.7-3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-6141 | libncursesw6 | 6.5+20250216-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-6141 | libtinfo6 | 6.5+20250216-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-6141 | ncurses-base | 6.5+20250216-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-6141 | ncurses-bin | 6.5+20250216-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-69720 | libncursesw6 | 6.5+20250216-2 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-69720 | libtinfo6 | 6.5+20250216-2 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-69720 | ncurses-base | 6.5+20250216-2 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-69720 | ncurses-bin | 6.5+20250216-2 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2025-70873 | libsqlite3-0 | 3.46.1-7+deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-11822 | libsqlite3-0 | 3.46.1-7+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-11824 | libsqlite3-0 | 3.46.1-7+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-12087 | perl-base | 5.40.1-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-13221 | perl-base | 5.40.1-6 | CRITICAL | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-15059 | libsystemd0 | 257.13-1~deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-15059 | libudev1 | 257.13-1~deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-15534 | perl-base | 5.40.1-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-16742 | libsystemd0 | 257.13-1~deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-16742 | libudev1 | 257.13-1~deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-18374 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-18374 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-18477 | tar | 1.35+dfsg-3.1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-18508 | tar | 1.35+dfsg-3.1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-19487 | perl-base | 5.40.1-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-19499 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-19499 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-19542 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-19542 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-27171 | zlib1g | 1:1.3.dfsg+really1.3.1-1+b1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | bsdutils | 1:2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | libblkid1 | 2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | liblastlog2-2 | 2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | libmount1 | 2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | libsmartcols1 | 2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | libuuid1 | 2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | mount | 2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-3184 | util-linux | 2.41.5-0+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-39113 | libsqlite3-0 | 3.46.1-7+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-40228 | libsystemd0 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-40228 | libudev1 | 257.13-1~deb13u1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-41991 | gzip | 1.13-1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-41992 | gzip | 1.13-1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-42250 | libbz2-1.0 | 1.0.8-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-42496 | perl-base | 5.40.1-6 | CRITICAL | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-42497 | perl-base | 5.40.1-6 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-48959 | perl-base | 5.40.1-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-48961 | perl-base | 5.40.1-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-48962 | perl-base | 5.40.1-6 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-50812 | libsqlite3-0 | 3.46.1-7+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-50813 | libsqlite3-0 | 3.46.1-7+deb13u1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-53910 | diffutils | 1:3.10-4 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-5435 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-5435 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-54369 | libacl1 | 2.3.2-2+b1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-54370 | libacl1 | 2.3.2-2+b1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-54371 | libattr1 | 1:2.5.2-3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-54411 | libpam-modules | 1.7.0-5 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-54411 | libpam-modules-bin | 1.7.0-5 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-54411 | libpam-runtime | 1.7.0-5 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-54411 | libpam0g | 1.7.0-5 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-5450 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-5450 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-56391 | coreutils | 9.7-3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-56392 | coreutils | 9.7-3 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-5704 | tar | 1.35+dfsg-3.1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-57432 | perl-base | 5.40.1-6 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-57433 | perl-base | 5.40.1-6 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-5928 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-5928 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-59890 | setuptools | 70.3.0 | MEDIUM | I1,I2,I3,I4,I5,I12 | 83.0.0 |
| CVE-2026-6238 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-6238 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-6368 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-6368 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-6791 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-6791 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-7010 | perl-base | 5.40.1-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-7017 | perl-base | 5.40.1-6 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | bsdutils | 1:2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | libblkid1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | liblastlog2-2 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | libmount1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | libsmartcols1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | libuuid1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | mount | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-76642 | util-linux | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-77117 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-77117 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | bsdutils | 1:2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | libblkid1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | liblastlog2-2 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | libmount1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | libsmartcols1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | libuuid1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | mount | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78408 | util-linux | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | bsdutils | 1:2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | libblkid1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | liblastlog2-2 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | libmount1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | libsmartcols1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | libuuid1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | mount | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78409 | util-linux | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | bsdutils | 1:2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | libblkid1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | liblastlog2-2 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | libmount1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | libsmartcols1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | libuuid1 | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | mount | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-78410 | util-linux | 2.41.5-0+deb13u1 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-80489 | libc-bin | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-80489 | libc6 | 2.41-12+deb13u3 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-8376 | perl-base | 5.40.1-6 | CRITICAL | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-85091 | zlib1g | 1:1.3.dfsg+really1.3.1-1+b1 | MEDIUM | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-86145 | libpcre2-8-0 | 10.46-1~deb13u1 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-89092 | libc-bin | 2.41-12+deb13u3 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-89092 | libc6 | 2.41-12+deb13u3 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-89156 | libpcre2-8-0 | 10.46-1~deb13u1 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-89157 | libpcre2-8-0 | 10.46-1~deb13u1 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-89158 | libpcre2-8-0 | 10.46-1~deb13u1 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-89160 | libpcre2-8-0 | 10.46-1~deb13u1 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-89161 | libpcre2-8-0 | 10.46-1~deb13u1 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-89162 | libpcre2-8-0 | 10.46-1~deb13u1 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
| CVE-2026-9538 | perl-base | 5.40.1-6 | HIGH | I1,I2,I3,I4,I5,I12 | not reported |
| GHSA-6v7p-g79w-8964 | msgpack | 1.1.2 | HIGH | I1,I2,I3,I4,I5,I12 | 1.2.1 |
| TEMP-0290435-0B57B5 | tar | 1.35+dfsg-3.1 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| TEMP-0517018-A83CE6 | sysvinit-utils | 3.14-4 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| TEMP-0628843-DBAD28 | login.defs | 1:4.17.4-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| TEMP-0628843-DBAD28 | passwd | 1:4.17.4-2 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| TEMP-0841856-B18BAF | bash | 5.2.37-2+b9 | LOW | I1,I2,I3,I4,I5,I12 | not reported |
| TEMP-1147318-639065 | liblzma5 | 5.8.1-1+deb13u1 | UNKNOWN | I1,I2,I3,I4,I5,I12 | not reported |
