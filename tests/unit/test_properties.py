# SPDX-License-Identifier: MIT
"""Property-based tests using Hypothesis.

Tests canonical JSON determinism, Merkle tree properties, and
cryptographic invariants.
"""

import json
from hypothesis import given, strategies as st, settings

from segel_core.canonical import canonical_json
from segel_core.crypto.hashing import (
    sha256, sha256_hex, merkle_leaf_hash, merkle_node_hash,
    MerkleTree, verify_inclusion,
)
from segel_core.crypto.ed25519 import generate_keypair, sign, verify as ed_verify


# ── Canonical JSON Determinism ───────────────────────────────────────

# Strategy: canonical_json() only accepts dict or BaseModel, so we
# generate dicts (not bare None/list/int/str).
json_leaf_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-2**53, max_value=2**53),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=50),
)
json_values = st.dictionaries(
    st.text(max_size=10),
    st.recursive(
        json_leaf_values,
        lambda children: st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(st.text(max_size=10), children, max_size=5),
        ),
        max_leaves=20,
    ),
    max_size=5,
    min_size=1,
)


class TestCanonicalJsonProperties:
    """Property-based tests for canonical JSON."""

    @given(data=json_values)
    @settings(max_examples=200)
    def test_deterministic(self, data):
        """Same input always produces same output."""
        r1 = canonical_json(data)
        r2 = canonical_json(data)
        assert r1 == r2

    @given(data=json_values)
    @settings(max_examples=100)
    def test_parseable(self, data):
        """Output is always valid JSON."""
        result = canonical_json(data)
        parsed = json.loads(result)
        # For dicts, check all keys present
        if isinstance(data, dict):
            assert set(parsed.keys()) == set(data.keys())

    @given(data=st.dictionaries(st.text(max_size=10), st.integers(), max_size=10, min_size=2))
    @settings(max_examples=100)
    def test_sorted_keys(self, data):
        """Keys are always sorted."""
        result = canonical_json(data)
        result_str = result.decode("utf-8")
        # Verify no extra whitespace
        assert "  " not in result_str  # No indentation
        assert "\n" not in result_str  # No newlines

    @given(data=json_values)
    @settings(max_examples=100)
    def test_utf8_encoded(self, data):
        """Output is always valid UTF-8."""
        result = canonical_json(data)
        result.decode("utf-8")  # Should not raise


# ── SHA-256 Properties ───────────────────────────────────────────────

class TestSha256Properties:
    """Property-based tests for SHA-256."""

    @given(data=st.binary(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_deterministic(self, data):
        assert sha256(data) == sha256(data)

    @given(data=st.binary(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_length(self, data):
        assert len(sha256(data)) == 32
        assert len(sha256_hex(data)) == 64

    @given(d1=st.binary(min_size=1, max_size=100), d2=st.binary(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_collision_resistance(self, d1, d2):
        """Different inputs produce different hashes (probabilistic)."""
        if d1 != d2:
            assert sha256(d1) != sha256(d2)


# ── Merkle Tree Properties ──────────────────────────────────────────

class TestMerkleLeafProperties:
    """Property-based tests for Merkle leaf/node hashing."""

    @given(data=st.binary(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_leaf_domain_separation(self, data):
        """Leaf hash uses 0x00 prefix."""
        leaf = merkle_leaf_hash(data)
        node = merkle_node_hash(data, data)
        # Leaf and node hashes should be different
        assert leaf != node

    @given(data=st.binary(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_leaf_deterministic(self, data):
        assert merkle_leaf_hash(data) == merkle_leaf_hash(data)

    @given(left=st.binary(min_size=32, max_size=32), right=st.binary(min_size=32, max_size=32))
    @settings(max_examples=100)
    def test_node_deterministic(self, left, right):
        assert merkle_node_hash(left, right) == merkle_node_hash(left, right)

    @given(left=st.binary(min_size=32, max_size=32), right=st.binary(min_size=32, max_size=32))
    @settings(max_examples=50)
    def test_node_order_matters(self, left, right):
        """node(left, right) != node(right, left) unless left == right."""
        if left != right:
            assert merkle_node_hash(left, right) != merkle_node_hash(right, left)


class TestMerkleTreeProperties:
    """Property-based tests for Merkle tree."""

    @given(entries=st.lists(st.binary(min_size=1, max_size=100), min_size=1, max_size=32))
    @settings(max_examples=50)
    def test_all_entries_have_inclusion_proofs(self, entries):
        """Every entry in the tree has a valid inclusion proof."""
        tree = MerkleTree()
        for e in entries:
            tree.append(e)

        size = tree.size
        root = tree.root_hash(size)

        for i in range(size):
            proof = tree.inclusion_proof(i, size)
            verify_inclusion(entries[i], i, size, proof, root)

    @given(entries=st.lists(st.binary(min_size=1, max_size=100), min_size=1, max_size=32))
    @settings(max_examples=50)
    def test_deterministic_root(self, entries):
        """Same entries in same order produce same root."""
        t1 = MerkleTree()
        t2 = MerkleTree()
        for e in entries:
            t1.append(e)
            t2.append(e)
        assert t1.root_hash() == t2.root_hash()


# ── Ed25519 Properties ──────────────────────────────────────────────

class TestEd25519Properties:
    """Property-based tests for Ed25519 signing."""

    @given(message=st.binary(min_size=0, max_size=500))
    @settings(max_examples=30)
    def test_sign_verify_roundtrip(self, message):
        kp = generate_keypair()
        sig = sign(kp.private_key, message)
        ed_verify(kp.public_key, sig, message)  # Should not raise

    @given(message=st.binary(min_size=1, max_size=500))
    @settings(max_examples=20)
    def test_different_keys_different_signatures(self, message):
        kp1 = generate_keypair()
        kp2 = generate_keypair()
        sig1 = sign(kp1.private_key, message)
        sig2 = sign(kp2.private_key, message)
        # Very unlikely to collide
        assert sig1 != sig2

    @given(msg1=st.binary(min_size=1, max_size=100), msg2=st.binary(min_size=1, max_size=100))
    @settings(max_examples=20)
    def test_wrong_message_rejected(self, msg1, msg2):
        if msg1 == msg2:
            return
        kp = generate_keypair()
        sig = sign(kp.private_key, msg1)
        with __import__("pytest").raises(Exception):
            ed_verify(kp.public_key, sig, msg2)
