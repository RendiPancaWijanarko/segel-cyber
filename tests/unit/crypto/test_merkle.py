"""
Merkle tree tests including hand-computed test vectors.

Per SEC-040: Tests MUST include a hand-computed Merkle tree.
"""

import pytest

from segel_core.crypto.hashing import (
    sha256,
    sha256_hex,
    merkle_leaf_hash,
    merkle_node_hash,
    MerkleTree,
    verify_inclusion,
    verify_consistency,
    verify_digest,
    _largest_power_of_2_less_than,
)
from segel_core.errors import ProofInvalidError, DigestMismatchError, CheckpointForkError


class TestHashing:
    """Test basic SHA-256 operations."""

    def test_sha256_known_vector(self):
        # SHA-256 of empty string
        result = sha256_hex(b"")
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_sha256_hello(self):
        result = sha256_hex(b"hello")
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_verify_digest_match(self):
        data = b"test data"
        digest = sha256_hex(data)
        verify_digest(data, digest)  # Should not raise

    def test_verify_digest_mismatch(self):
        with pytest.raises(DigestMismatchError):
            verify_digest(b"data", "0" * 64)


class TestMerkleLeafAndNode:
    """Test leaf and node hash domain separation."""

    def test_leaf_hash_has_0x00_prefix(self):
        data = b"leaf data"
        expected = sha256(b"\x00" + data)
        assert merkle_leaf_hash(data) == expected

    def test_node_hash_has_0x01_prefix(self):
        left = b"\x00" * 32
        right = b"\xff" * 32
        expected = sha256(b"\x01" + left + right)
        assert merkle_node_hash(left, right) == expected

    def test_leaf_and_node_are_different(self):
        """Domain separation: leaf hash != node hash for same input."""
        data = b"\x00" * 32
        leaf = merkle_leaf_hash(data)
        # Node with data as both children
        node = merkle_node_hash(data, data)
        assert leaf != node


class TestHandComputedMerkleTree:
    """Hand-computed Merkle tree test per SEC-040.

    Tree with 4 leaves: A, B, C, D

         root
        /    \\
      n01     n23
      / \\    / \\
    l0  l1  l2  l3
    A   B   C   D
    """

    def setup_method(self):
        self.data = [b"A", b"B", b"C", b"D"]
        self.leaf_hashes = [merkle_leaf_hash(d) for d in self.data]
        self.n01 = merkle_node_hash(self.leaf_hashes[0], self.leaf_hashes[1])
        self.n23 = merkle_node_hash(self.leaf_hashes[2], self.leaf_hashes[3])
        self.root = merkle_node_hash(self.n01, self.n23)

    def test_tree_root(self):
        tree = MerkleTree()
        for d in self.data:
            tree.append(d)
        assert tree.root_hash() == self.root

    def test_inclusion_proof_leaf_0(self):
        """Proof for leaf 0 (A): sibling is l1, then n23."""
        tree = MerkleTree()
        for d in self.data:
            tree.append(d)

        proof = tree.inclusion_proof(0, 4)
        assert len(proof) == 2
        assert proof[0] == self.leaf_hashes[1]  # sibling l1
        assert proof[1] == self.n23              # sibling subtree n23

        verify_inclusion(self.data[0], 0, 4, proof, self.root)

    def test_inclusion_proof_leaf_3(self):
        """Proof for leaf 3 (D): sibling is l2, then n01."""
        tree = MerkleTree()
        for d in self.data:
            tree.append(d)

        proof = tree.inclusion_proof(3, 4)
        assert len(proof) == 2
        assert proof[0] == self.leaf_hashes[2]  # sibling l2
        assert proof[1] == self.n01              # sibling subtree n01

        verify_inclusion(self.data[3], 3, 4, proof, self.root)

    def test_inclusion_proof_all_leaves(self):
        tree = MerkleTree()
        for d in self.data:
            tree.append(d)
        root = tree.root_hash()

        for i, d in enumerate(self.data):
            proof = tree.inclusion_proof(i, 4)
            verify_inclusion(d, i, 4, proof, root)

    def test_wrong_leaf_data_fails(self):
        """AT-021: Inclusion proof for wrong leaf fails."""
        tree = MerkleTree()
        for d in self.data:
            tree.append(d)

        proof = tree.inclusion_proof(0, 4)
        with pytest.raises(ProofInvalidError):
            verify_inclusion(b"WRONG", 0, 4, proof, self.root)

    def test_wrong_root_fails(self):
        tree = MerkleTree()
        for d in self.data:
            tree.append(d)

        proof = tree.inclusion_proof(0, 4)
        with pytest.raises(ProofInvalidError):
            verify_inclusion(self.data[0], 0, 4, proof, b"\x00" * 32)


class TestMerkleTreeGrowing:
    """Test tree growth and consistency proofs."""

    def test_single_leaf(self):
        tree = MerkleTree()
        tree.append(b"only")
        root = tree.root_hash()
        assert root == merkle_leaf_hash(b"only")

    def test_empty_tree(self):
        tree = MerkleTree()
        root = tree.root_hash()
        assert root == sha256(b"")

    def test_consistency_1_to_4(self):
        tree = MerkleTree()
        tree.append(b"A")
        root_1 = tree.root_hash(1)

        for d in [b"B", b"C", b"D"]:
            tree.append(d)
        root_4 = tree.root_hash(4)

        proof = tree.consistency_proof(1, 4)
        verify_consistency(1, 4, root_1, root_4, proof)

    def test_consistency_2_to_4(self):
        tree = MerkleTree()
        for d in [b"A", b"B"]:
            tree.append(d)
        root_2 = tree.root_hash(2)

        for d in [b"C", b"D"]:
            tree.append(d)
        root_4 = tree.root_hash(4)

        proof = tree.consistency_proof(2, 4)
        verify_consistency(2, 4, root_2, root_4, proof)

    def test_consistency_same_size(self):
        tree = MerkleTree()
        for d in [b"A", b"B"]:
            tree.append(d)
        root = tree.root_hash()

        proof = tree.consistency_proof(2, 2)
        assert proof == []
        verify_consistency(2, 2, root, root, proof)

    def test_consistency_empty_old(self):
        tree = MerkleTree()
        tree.append(b"A")
        proof = tree.consistency_proof(0, 1)
        assert proof == []

    def test_fork_detected(self):
        """AT-020: Non-extending checkpoint (fork) rejected."""
        tree = MerkleTree()
        for d in [b"A", b"B"]:
            tree.append(d)
        root_2 = tree.root_hash()

        # Same size but different root = fork
        with pytest.raises(CheckpointForkError):
            verify_consistency(2, 2, root_2, b"\x00" * 32, [])


class TestLargestPowerOf2:
    """Test the helper function."""

    def test_values(self):
        assert _largest_power_of_2_less_than(1) == 1
        assert _largest_power_of_2_less_than(2) == 1
        assert _largest_power_of_2_less_than(3) == 2
        assert _largest_power_of_2_less_than(4) == 2
        assert _largest_power_of_2_less_than(5) == 4
        assert _largest_power_of_2_less_than(8) == 4
        assert _largest_power_of_2_less_than(9) == 8


class TestInclusionWithVariousSizes:
    """Test inclusion proofs with different tree sizes."""

    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 7, 8, 10, 16, 17, 32])
    def test_all_leaves_verifiable(self, n):
        tree = MerkleTree()
        for i in range(n):
            tree.append(f"leaf-{i}".encode())

        root = tree.root_hash()
        for i in range(n):
            proof = tree.inclusion_proof(i, n)
            verify_inclusion(f"leaf-{i}".encode(), i, n, proof, root)

    def test_out_of_range_index(self):
        tree = MerkleTree()
        tree.append(b"A")
        with pytest.raises(ProofInvalidError, match="out of range"):
            tree.inclusion_proof(1, 1)

