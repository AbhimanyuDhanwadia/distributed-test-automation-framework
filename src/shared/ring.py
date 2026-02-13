"""
Consistent Hash Ring implementation for distributed task routing.
"""
import hashlib
import struct
import bisect
from typing import List, Dict, Optional


class ConsistentHashRing:
    """
    Consistent hashing ring for distributing tasks across worker nodes.
    
    Uses virtual nodes (replicas) to ensure better distribution and
    minimize redistribution when nodes are added or removed.
    """
    
    def __init__(self, nodes: Optional[List[str]] = None, replicas: int = 100):
        """
        Initialize the consistent hash ring.
        
        Args:
            nodes: Optional list of initial nodes to add to the ring
            replicas: Number of virtual nodes per physical node (default: 100)
        """
        self.replicas = replicas
        self.ring: Dict[int, str] = {}
        self.sorted_keys: List[int] = []
        
        if nodes:
            for node in nodes:
                self.add_node(node)
    
    def _hash(self, key: str) -> int:
        """
        Hash a key to a 32-bit unsigned integer using MD5.
        
        Args:
            key: String to hash
            
        Returns:
            32-bit unsigned integer hash value
        """
        md5_digest = hashlib.md5(key.encode('utf-8')).digest()
        # Extract first 4 bytes as big-endian unsigned 32-bit integer
        return struct.unpack('>I', md5_digest[:4])[0]
    
    def add_node(self, node: str) -> None:
        """
        Add a node to the hash ring with virtual replicas.
        
        Args:
            node: Node identifier to add
        """
        for i in range(self.replicas):
            virtual_key = f"{node}:{i}"
            hash_value = self._hash(virtual_key)
            self.ring[hash_value] = node
            self.sorted_keys.append(hash_value)
        
        # Keep sorted keys list sorted for binary search
        self.sorted_keys.sort()
    
    def remove_node(self, node: str) -> None:
        """
        Remove a node and all its virtual replicas from the ring.
        
        Args:
            node: Node identifier to remove
        """
        for i in range(self.replicas):
            virtual_key = f"{node}:{i}"
            hash_value = self._hash(virtual_key)
            
            if hash_value in self.ring:
                del self.ring[hash_value]
                self.sorted_keys.remove(hash_value)
    
    def get_node(self, key: str) -> str:
        """
        Get the node responsible for a given key.
        
        Uses binary search to find the next node clockwise on the ring.
        
        Args:
            key: Key to look up
            
        Returns:
            Node identifier responsible for this key
            
        Raises:
            ValueError: If the ring is empty
        """
        if not self.ring:
            raise ValueError("Hash ring is empty")
        
        hash_value = self._hash(key)
        
        # Find the first node with hash >= key's hash
        index = bisect.bisect(self.sorted_keys, hash_value)
        
        # Handle wrap-around: if we're past the end, use the first node
        if index == len(self.sorted_keys):
            index = 0
        
        return self.ring[self.sorted_keys[index]]
