# Issue 42: original English master cross-check (read-only)

For [issue 42](https://github.com/munument1/Morrowind-OpenMW-KR/issues/42), use only the published KR12.3.1 ZIP and the full reporter Gist JSON. No original commercial Morrowind master is included in this repository or CI.

## Windows PowerShell steps

1. Download the KR12.3.1 Full ZIP into C:\Temp\issue42\KR12.3.1.zip. Use exactly the release identified in the issue, not a later mod package.
2. Save the full Gist API JSON:

       Invoke-WebRequest 'https://api.github.com/gists/36892c800dad56c657b418d0b42956f2' -OutFile 'C:\Temp\issue42\reporter-gist.json'

3. Run the Korean-side read-only source indexer:

       python packaging/korean/tooling/audit_issue42_reported_candidates.py --zip 'C:\Temp\issue42\KR12.3.1.zip' --gist 'C:\Temp\issue42\reporter-gist.json' --output 'C:\Temp\issue42\korean-audit.json'

4. Compare with your own legally installed English ESMs, in actual load order, replacing the example Data Files path:

       python packaging/korean/tooling/audit_issue42_original_masters.py --zip 'C:\Temp\issue42\KR12.3.1.zip' --report 'C:\Temp\issue42\korean-audit.json' --original 'C:\Games\Morrowind\Data Files\Morrowind.esm' 'C:\Games\Morrowind\Data Files\Tribunal.esm' 'C:\Games\Morrowind\Data Files\Bloodmoon.esm' --output 'C:\Temp\issue42\original-English-crosscheck.json'

5. Run synthetic unit tests independently of any game files:

       python -m unittest discover -s packaging/korean/tooling -p 'test_issue42_original_masters.py' -v

## What the output does and does not establish

- Exact INFO ID joins and uniquely inferred Korean-to-English DIAL names are evidence of corresponding text records. English literal keyword presence does not prove that the OpenMW runtime would highlight or teach the topic.
- The original ESM's AddTopic text references reveal possible additional learning paths for the reported 51+20 topics. They do not prove the script executes in a reachable journal/actor state. References in unexecuted script branches or comments can be false leads.
- If original INFO IDs differ or a Korean topic maps to multiple English topics, no automatic semantic mapping is made.
- Source file hashes are recorded. Output is new-only. The installed ESMs, published ZIP, Korean ESP, sidecars and saves are not modified.
- Western encoding of the vanilla English ESMs is assumed. Non-English localized masters require separate evaluation.
- Do not upload proprietary master files to a repository or CI. Review selective evidence and SHA provenance without exposing commercial assets.

PR 44 must remain a draft and issue 42 must remain open until original ESM comparisons and actual gameplay verification are complete.
