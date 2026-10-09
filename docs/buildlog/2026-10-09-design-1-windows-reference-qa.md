# DESIGN-1-WIN-REFQA — Cross-platform reference checkout evidence — 2026-10-09

## Sprint contract

- **Start branch:** `design-1-live-studio` at verified remote `cac24881a621ae1e2fd3841c70e238ddca2c4d23`; draft PR #10. Writer: ChatGPT/GitHub only; no Actions or merge authority.
- **Observation:** user reports `python -m pytest -q` **80 passed, 1 failed** on an older Windows working tree after live Streamlit/GSW Design Studio smoke. Sole failing `CheckedInReferenceTests` compares file length **6890** vs pinned **6746** for EPA `Example_project.prj`. The authoritative Git blob has **144 LF and 0 CR**, exactly explaining the +144 checkout CRLF bytes. Local `git rev-parse HEAD` still not supplied.
- **Scope:** make the reference harness test the exact pinned **committed Git object** with explicit read-only handling of *verified* Windows worktree EOL conversion, not penalize an otherwise valid legacy checkout. Preserve strict raw executable checks. No modifications to `References/`, no replacement manifest digests, no physical-model changes.
- **Reasoning level:** High — source-of-truth versus worktree byte identity, exact SHA-1 Git blob framing, zero-mutation guarantee, false-positive discriminators.
- **Retires when:** bounded identity tests prove exact byte/sha match, CRLF-only recovery and altered-byte rejection; Windows full checkout test reports zero failing tests with warnings disclosed; source identity and no reference mutation verified.

## Mechanism / actual source changes

`tests/reference_harness/test_checked_in_examples.py` previously asserted the **worktree** `stat().st_size` and blob hash exactly matched the manifest's **committed Git blob**, silently assuming Git never transforms checkout text. That assumption fails on a Windows clone that predates root `.gitattributes` `References/** -text`. Files in `References/` have never been altered in Git.

- New stdlib-only `tools/reference_harness/worktree_identity.py` first verifies exact raw worktree `size_bytes` **and** Git SHA-1 blob ID (including the `blob <len>\\0` header). Returns byte-exact status.
- Only for explicitly permitted **known text** reference fixtures (`.prj`, `.csv`, `.dat`) on Windows, if the raw worktree fails, reconstruct `CRLF -> LF` **in memory only** and require the reconstructed data to match the **exact original manifest length AND original Git blob SHA-1**. The on-disk source is never opened for writing, regenerated, fixed, or normalized in place. Any other modification still raises `ReferenceIdentityError`.
- The full-checkout test emits a visible `RuntimeWarning` when one or more text worktree files were line-ending transformed, stating the working copies are **not byte-exact** even though the committed Git source content matches. This must **not** be reported as proof that the local worktree holds raw original bytes.
- Existing pinned executable size, Git blob SHA and optional SHA-256 checks remain **strict on actual worktree bytes**. Existing executable-derived reference comparison stays unchanged. Root `.gitattributes` remains recommended for byte-faithful new clones.
- Six focused independent regression discriminators in `tests/reference_harness/test_worktree_identity.py`: exact raw checkout, permitted reversible EOL conversion, unpermitted conversion rejection, actual content mutation rejection, extra-line rejection, bare-CR rejection and blob framing. No fixture moved into `References/`.

## Bounded sandbox verification

- Exact new source blobs prepared against isolated Python code: `tools/reference_harness/worktree_identity.py` = `7c47472fd0670d9d4d2d7b3b48be9b2245ae2dc7`; `tests/reference_harness/test_worktree_identity.py` = `fa5e4a3664b6f9940b866e8a6afe30bfd0af715e`; revised full-suite test `tests/reference_harness/test_checked_in_examples.py` = `3d99fd5b1458842f804fae80a7fcf71495363b05`. Each remote Git blob was checked against the exact sandbox file SHA.
- `python -m unittest discover -s ... -p test_worktree_identity.py -v`: **6 tests PASS, zero failures** on the isolated new helper; `python -m compileall -q`: **PASS** for all three new/revised Python files in the isolated harness.
- Exact-sized synthetic reproduction: 144 LF lines, original 6746 B, Windows CRLF worktree 6890 B, verify original `size_bytes` and Git blob SHA in memory: **PASS**. This does not run the full Plume repository suite nor access the user's travel-PC bytes; the original Git object identity was previously independently verified from GitHub.
- Executed the **actual revised full-checkout unittest method** against an isolated synthetic manifest/fixture with Windows `sys.platform` patched, a 6746-byte LF original and 6890-byte CRLF worktree. It **PASSed** with exactly one visible worktree-fidelity warning and no writes. Deliberately mutating a non-EOL byte then correctly **FAILed** the exact SHA/size check. This integration harness used stubs only for existing manifest/parser dependencies; it is not a complete Plume checkout.

## Remaining gate / handoff

**HOLD** until the user pulls the exact updated branch SHA in VS Code and runs `python -m pytest -q` with GSW installed. A visible warning for checkout-only CRLF is acceptable for **committed blob identity evidence** but it is **not a byte-exact worktree claim**. For physical/raw-reference comparisons or strict exported files, use original bytes from Git instead of CRLF-expanded local text. Capture full test total, warnings, final remote/local HEAD identity and refreshed Streamlit narrow-viewport snapshot. Keep model/field physical qualification gates open. No Actions, no `main` merge, no `References/` edits.
