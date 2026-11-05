"""
SHA-256 hashing and RFC 6962 Merkle tree implementation.

Per SEC-031:
- SHA-256 for all digests
- Merkle leaf hash: SHA-256(0x00 || data)
- Merkle node hash: SHA-256(0x01 || left || right)

Reference: RFC 6962 Section 2.1 and RFC 9162.
"""

import hashlib

from segel_core.errors import DigestMismatchError, ProofInvalidError


def sha256(data: bytes) -> bytes:
    """Compute SHA-256 digest."""
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    """Compute hex-encoded SHA-256 digest."""
    return hashlib.sha256(data).hexdigest()


def merkle_leaf_hash(data: bytes) -> bytes:
    """Compute Merkle leaf hash per RFC 6962: SHA-256(0x00 || data)."""
    return sha256(b"\x00" + data)


def merkle_node_hash(left: bytes, right: bytes) -> bytes:
    """Compute Merkle internal node hash per RFC 6962: SHA-256(0x01 || left || right)."""
    return sha256(b"\x01" + left + right)


def _largest_power_of_2_less_than(n: int) -> int:
    """Return the largest power of 2 strictly less than n.

    For n=1, returns 1 (special case per RFC 6962).
    """
    if n <= 1:
        return 1
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def _compute_subtree_hash(hashes: list[bytes]) -> bytes:
    """Recursively compute the Merkle root from a list of leaf hashes.

    Per RFC 6962 Section 2.1:
    - MTH({}) = SHA-256("")
    - MTH({d(0)}) = leaf_hash(d(0))  [already computed]
    - MTH(D) = SHA-256(0x01 || MTH(D[0:k]) || MTH(D[k:n]))
      where k is the largest power of 2 less than n
    """
    n = len(hashes)
    if n == 0:
        return sha256(b"")
    if n == 1:
        return hashes[0]
    k = _largest_power_of_2_less_than(n)
    left = _compute_subtree_hash(hashes[:k])
    right = _compute_subtree_hash(hashes[k:])
    return merkle_node_hash(left, right)


class MerkleTree:
    """A Merkle tree implementation per RFC 6962.

    Supports append, root hash, inclusion proofs, and consistency proofs.
    """

    def __init__(self) -> None:
        self._leaves: list[bytes] = []  # leaf hashes
        self._leaf_data: list[bytes] = []  # original data

    @property
    def size(self) -> int:
        return len(self._leaves)

    def append(self, data: bytes) -> int:
        """Append a leaf and return its index."""
        leaf_hash = merkle_leaf_hash(data)
        self._leaves.append(leaf_hash)
        self._leaf_data.append(data)
        return len(self._leaves) - 1

    def root_hash(self, size: int | None = None) -> bytes:
        """Compute the Merkle root hash for tree of given size."""
        if size is None:
            size = len(self._leaves)
        return _compute_subtree_hash(self._leaves[:size])

    def inclusion_proof(self, index: int, size: int | None = None) -> list[bytes]:
        """Generate an inclusion proof (audit path) for a leaf.

        Per RFC 6962 Section 2.1.1.
        """
        if size is None:
            size = len(self._leaves)
        if index < 0 or index >= size:
            raise ProofInvalidError(
                f"Leaf index {index} is out of range for tree of size {size}",
            )
        return self._path(index, self._leaves[:size])

    def _path(self, index: int, hashes: list[bytes]) -> list[bytes]:
        """Recursively build the inclusion proof path."""
        n = len(hashes)
        if n <= 1:
            return []
        k = _largest_power_of_2_less_than(n)
        if index < k:
            path = self._path(index, hashes[:k])
            path.append(_compute_subtree_hash(hashes[k:]))
            return path
        path = self._path(index - k, hashes[k:])
        path.append(_compute_subtree_hash(hashes[:k]))
        return path

    def consistency_proof(self, old_size: int, new_size: int | None = None) -> list[bytes]:
        """Generate a consistency proof between two tree sizes.

        Per RFC 6962 Section 2.1.2.
        """
        if new_size is None:
            new_size = len(self._leaves)
        if old_size > new_size:
            raise ProofInvalidError(f"Old size {old_size} exceeds new size {new_size}")
        if old_size == 0 or old_size == new_size:
            return []
        return self._subproof(old_size, self._leaves[:new_size], True)

    def _subproof(self, m: int, hashes: list[bytes], start_from_old: bool) -> list[bytes]:
        """RFC 6962 Section 2.1.2 SUBPROOF algorithm."""
        n = len(hashes)
        if m == n:
            if start_from_old:
                return []
            return [_compute_subtree_hash(hashes)]
        k = _largest_power_of_2_less_than(n)
        if m <= k:
            proof = self._subproof(m, hashes[:k], start_from_old)
            proof.append(_compute_subtree_hash(hashes[k:]))
            return proof
        proof = self._subproof(m - k, hashes[k:], False)
        proof.append(_compute_subtree_hash(hashes[:k]))
        return proof


def verify_inclusion(
    leaf_data: bytes,
    index: int,
    size: int,
    proof: list[bytes],
    expected_root: bytes,
) -> None:
    """Verify a Merkle inclusion proof.

    Per RFC 6962 Section 2.1.1.

    Raises:
        ProofInvalidError: If the proof does not verify.
    """
    if size == 0:
        raise ProofInvalidError("Cannot verify inclusion in an empty tree")
    if index < 0 or index >= size:
        raise ProofInvalidError(f"Index {index} out of range for size {size}")

    node = merkle_leaf_hash(leaf_data)
    node = _root_from_inclusion_proof(node, index, size, list(proof))

    if node != expected_root:
        raise ProofInvalidError(
            "Inclusion proof verification failed: computed root does not match",
            {"computed": node.hex(), "expected": expected_root.hex()},
        )


def verify_inclusion_from_hash(
    leaf_hash: bytes,
    index: int,
    size: int,
    proof: list[bytes],
    expected_root: bytes,
) -> None:
    """Verify a Merkle inclusion proof starting from a leaf hash.

    Unlike verify_inclusion, this takes the already-computed leaf hash
    (output of merkle_leaf_hash) rather than the raw data.

    Raises:
        ProofInvalidError: If the proof does not verify.
    """
    if size == 0:
        raise ProofInvalidError("Cannot verify inclusion in an empty tree")
    if index < 0 or index >= size:
        raise ProofInvalidError(f"Index {index} out of range for size {size}")

    node = _root_from_inclusion_proof(leaf_hash, index, size, list(proof))

    if node != expected_root:
        raise ProofInvalidError(
            "Inclusion proof verification failed: computed root does not match",
            {"computed": node.hex(), "expected": expected_root.hex()},
        )


def _root_from_inclusion_proof(
    leaf_hash: bytes, index: int, size: int, proof: list[bytes]
) -> bytes:
    """Recompute root from an inclusion proof by walking the tree structure."""
    if size == 1:
        if proof:
            raise ProofInvalidError("Non-empty proof for single-leaf tree")
        return leaf_hash

    k = _largest_power_of_2_less_than(size)
    if index < k:
        # Leaf is in the left subtree
        if not proof:
            raise ProofInvalidError("Proof exhausted before reaching root")
        right_sibling = proof.pop()
        left = _root_from_inclusion_proof(leaf_hash, index, k, proof)
        return merkle_node_hash(left, right_sibling)
    # Leaf is in the right subtree
    if not proof:
        raise ProofInvalidError("Proof exhausted before reaching root")
    left_sibling = proof.pop()
    right = _root_from_inclusion_proof(leaf_hash, index - k, size - k, proof)
    return merkle_node_hash(left_sibling, right)


def verify_consistency(
    old_size: int,
    new_size: int,
    old_root: bytes,
    new_root: bytes,
    proof: list[bytes],
) -> None:
    """Verify a Merkle consistency proof.

    Implements the verification algorithm from RFC 9162 Section 2.1.4.2,
    matching the SUBPROOF generation in RFC 6962 Section 2.1.2.

    Raises:
        ProofInvalidError: If the proof does not verify.
        CheckpointForkError: If trees are inconsistent (fork detected).
    """
    from segel_core.errors import CheckpointForkError

    if old_size == 0:
        return  # Empty tree is consistent with anything
    if old_size == new_size:
        if old_root != new_root:
            raise CheckpointForkError(
                "Same size but different roots: log fork detected",
                {"old_root": old_root.hex(), "new_root": new_root.hex()},
            )
        if proof:
            raise ProofInvalidError("Non-empty proof for same-size trees")
        return
    if old_size > new_size:
        raise ProofInvalidError(f"Old size {old_size} exceeds new size {new_size}")
    if not proof:
        raise ProofInvalidError("Empty consistency proof for different-sized trees")

    # RFC 9162 Section 2.1.4.2 verification algorithm.
    #
    # The SUBPROOF generation (RFC 6962 Section 2.1.2) works as follows:
    # - SUBPROOF(m, D[0:n], true):
    #   - If m == n: return empty (old root = subtree hash, skip it)
    #   - If m == n and not start_from_old: return [MTH(D[0:n])]
    #   - If m <= k (k = largest power of 2 < n):
    #       return SUBPROOF(m, D[0:k], start_from_old) || MTH(D[k:n])
    #   - Else:
    #       return SUBPROOF(m-k, D[k:n], false) || MTH(D[0:k])
    #
    # Verification must mirror this structure:
    # Walk proof nodes from front to back, reconstructing both old and new roots.

    proof_list = list(proof)
    idx = 0  # index into proof_list

    # Determine if old_size is a power of 2.
    # When start_from_old=True and m==k at some level, SUBPROOF skips the
    # subtree hash (returns empty). If old_size is a power of 2, the very
    # first SUBPROOF call hits m==n immediately, so no seed node is emitted.
    # We must use old_root as the starting seed.
    # When old_size is NOT a power of 2, the recursion eventually hits the
    # m==n case with start_from_old=False, emitting MTH(D[0:n]) as the first
    # proof element. That becomes our seed.

    if _is_power_of_2(old_size):
        # The seed is the old tree root itself (not in the proof)
        old_hash = old_root
        new_hash = old_root
    else:
        # The first proof node is the seed from the deepest SUBPROOF(m==n, false)
        if idx >= len(proof_list):
            raise ProofInvalidError("Proof too short")
        old_hash = proof_list[idx]
        new_hash = proof_list[idx]
        idx += 1

    # Now replay the SUBPROOF recursion to consume remaining proof nodes.
    # We trace the path that SUBPROOF took by simulating the recursion.
    # At each level, we need to know: m (old_size in subtree), n (new_size
    # in subtree), and whether we went left (m <= k) or right (m > k).
    #
    # Build the path from bottom to top first, then consume proof nodes.

    # Collect the decomposition path
    m = old_size
    n = new_size
    start_from_old = True
    path = []  # list of (direction, m_at_level, n_at_level)

    while True:
        if m == n:
            break
        k = _largest_power_of_2_less_than(n)
        if m <= k:
            path.append(("left", m, n, k, start_from_old))
            n = k
            # start_from_old stays the same
        else:
            path.append(("right", m, n, k, start_from_old))
            m = m - k
            n = n - k
            start_from_old = False

    # Now consume proof nodes in order, applying them from deepest to shallowest.
    # The proof was built by appending siblings AFTER the recursive call,
    # so the order is: [seed_if_any, deepest_sibling, ..., shallowest_sibling]

    for direction, _m_level, _n_level, _k_level, _sfo in reversed(path):
        if idx >= len(proof_list):
            raise ProofInvalidError("Proof too short during verification")
        sibling = proof_list[idx]
        idx += 1

        if direction == "left":
            # SUBPROOF went into left subtree D[0:k], sibling is MTH(D[k:n])
            # new_hash is hash of left part, sibling is right part
            new_hash = merkle_node_hash(new_hash, sibling)
            # For old_hash: if the old tree is entirely within the left subtree
            # (m <= k), then old_hash should also combine with sibling only if
            # the old tree root needs this node. Actually, when we go left,
            # old_hash is being built up from the left. If start_from_old was
            # True at the level where m==n was reached (which means old_hash
            # started as old_root), we DON'T combine old_hash with right siblings
            # because those siblings are beyond the old tree. But wait—the old
            # tree of size m is entirely within D[0:k], so the right subtree
            # D[k:n_level] is NOT part of the old tree. So old_hash should NOT
            # include this sibling.
            # old_hash stays the same
        else:
            # SUBPROOF went into right subtree D[k:n], sibling is MTH(D[0:k])
            # sibling is the LEFT subtree hash
            new_hash = merkle_node_hash(sibling, new_hash)
            old_hash = merkle_node_hash(sibling, old_hash)

    if idx != len(proof_list):
        raise ProofInvalidError(
            f"Proof has {len(proof_list) - idx} unconsumed nodes"
        )

    if old_hash != old_root:
        raise CheckpointForkError(
            "Consistency proof failed: old root mismatch (possible fork)",
            {"computed_old": old_hash.hex(), "expected_old": old_root.hex()},
        )
    if new_hash != new_root:
        raise ProofInvalidError(
            "Consistency proof failed: new root mismatch",
            {"computed_new": new_hash.hex(), "expected_new": new_root.hex()},
        )


def _is_power_of_2(n: int) -> bool:
    """Check if n is a power of 2."""
    return n > 0 and (n & (n - 1)) == 0


def verify_digest(data: bytes, expected_hex: str) -> None:
    """Verify that data matches an expected SHA-256 hex digest."""
    computed = sha256_hex(data)
    if computed != expected_hex:
        raise DigestMismatchError(
            "SHA-256 digest mismatch",
            {"computed": computed, "expected": expected_hex},
        )
