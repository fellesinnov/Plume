"""Discriminators for read-only cross-platform raw-reference identity checks."""

from __future__ import annotations

import unittest

from tools.reference_harness.worktree_identity import (
    ReferenceIdentityError, check_pinned_worktree, git_blob_sha,
)


class WorktreeReferenceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.canonical = b"first\nsecond\nthird\n"
        self.converted = self.canonical.replace(b"\n", b"\r\n")
        self.original_size = len(self.canonical)
        self.original_git_blob_sha = git_blob_sha(self.canonical)

    def verify(self, content, tolerate_windows_crlf=False):
        return check_pinned_worktree(
            content, size_bytes=self.original_size,
            git_sha=self.original_git_blob_sha,
            tolerate_windows_crlf=tolerate_windows_crlf,
        )

    def test_unconverted_worktree_is_byte_exact(self):
        self.assertTrue(self.verify(self.canonical))
        self.assertTrue(self.verify(self.canonical, tolerate_windows_crlf=True))

    def test_only_reversible_checkout_crlf_is_accepted_with_explicit_opt_in(self):
        self.assertEqual(len(self.converted) - self.original_size, 3)
        self.assertFalse(self.verify(self.converted, tolerate_windows_crlf=True))
        with self.assertRaisesRegex(ReferenceIdentityError, "checkout-only"):
            self.verify(self.converted)

    def test_semantic_change_fails_even_if_newline_conversion_is_present(self):
        altered = self.converted.replace(b"second", b"sEcond")
        with self.assertRaisesRegex(ReferenceIdentityError, "does not match pinned"):
            self.verify(altered, tolerate_windows_crlf=True)

    def test_extra_newline_or_different_size_fails(self):
        with self.assertRaises(ReferenceIdentityError):
            self.verify(self.converted + b"\r\n", tolerate_windows_crlf=True)

    def test_lone_cr_or_non_checkout_transform_fails(self):
        with self.assertRaises(ReferenceIdentityError):
            self.verify(self.canonical.replace(b"\n", b"\r"), tolerate_windows_crlf=True)

    def test_git_blob_id_includes_size(self):
        self.assertNotEqual(git_blob_sha(self.canonical), git_blob_sha(self.canonical + b"\n"))


if __name__ == "__main__":
    unittest.main()
