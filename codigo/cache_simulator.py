#!/usr/bin/env python3
"""
Simulador de Hierarquia de Memória Cache Multinível (L1, L2, L3 + RAM)
"""

from enum import Enum
import math
from typing import Optional, Tuple, Dict, Any, List


class Policy(Enum):
    INCLUSIVE = "Inclusiva"
    EXCLUSIVE = "Exclusiva"
    NINE = "NINE (Não-Inclusiva / Não-Exclusiva)"


class Block:
    """Representa um bloco (linha) na memória cache."""

    def __init__(self, tag: int, block_addr: int):
        self.tag: int = tag
        self.block_addr: int = block_addr
        self.valid: bool = True
        self.dirty: bool = False
        self.last_access: int = 0


class CacheSet:
    """Representa um conjunto de linhas na cache com política de substituição LRU."""

    def __init__(self, associativity: int):
        self.associativity: int = associativity
        self.blocks: List[Block] = []

    def find_block(self, tag: int) -> Optional[Block]:
        for b in self.blocks:
            if b.valid and b.tag == tag:
                return b
        return None

    def access(self, tag: int, current_cycle: int) -> bool:
        block = self.find_block(tag)
        if block:
            block.last_access = current_cycle
            return True
        return False

    def insert(
        self, tag: int, block_addr: int, current_cycle: int
    ) -> Tuple[Optional[Block], Block]:
        """
        Insere um bloco no conjunto.
        Retorna (bloco_desalojado_ou_None, novo_bloco).
        """
        # Se já existe (ex: revalidação)
        existing = self.find_block(tag)
        if existing:
            existing.last_access = current_cycle
            existing.block_addr = block_addr
            return None, existing

        # Se há espaço disponível (blocos inválidos ou tamanho < associatividade)
        if len(self.blocks) < self.associativity:
            new_block = Block(tag, block_addr)
            new_block.last_access = current_cycle
            self.blocks.append(new_block)
            return None, new_block

        # Procura primeiro algum bloco inválido
        for i, b in enumerate(self.blocks):
            if not b.valid:
                new_block = Block(tag, block_addr)
                new_block.last_access = current_cycle
                self.blocks[i] = new_block
                return None, new_block

        # Caso contrário, substituição LRU (menor last_access)
        lru_index = min(
            range(len(self.blocks)), key=lambda i: self.blocks[i].last_access
        )
        evicted = self.blocks[lru_index]
        new_block = Block(tag, block_addr)
        new_block.last_access = current_cycle
        self.blocks[lru_index] = new_block
        return evicted, new_block

    def invalidate(self, tag: int) -> bool:
        """Invalida o bloco com a tag especificada. Retorna True se encontrado."""
        for b in self.blocks:
            if b.valid and b.tag == tag:
                b.valid = False
                return True
        return False

    def remove(self, tag: int) -> Optional[Block]:
        """Remove fisicamente o bloco do conjunto (usado na política exclusiva)."""
        for i, b in enumerate(self.blocks):
            if b.valid and b.tag == tag:
                return self.blocks.pop(i)
        return None


class CacheLevel:
    """Representa um nível individual de cache (L1, L2 ou L3)."""

    def __init__(
        self,
        name: str,
        size_bytes: int,
        block_size_bytes: int,
        associativity: int,
        hit_latency: int,
    ):
        self.name: str = name
        self.size_bytes: int = size_bytes
        self.block_size: int = block_size_bytes
        self.associativity: int = associativity
        self.hit_latency: int = hit_latency

        self.num_blocks: int = size_bytes // block_size_bytes
        self.num_sets: int = self.num_blocks // associativity

        if self.num_sets == 0:
            raise ValueError(f"Configuração inválida para {name}: num_sets = 0")

        self.offset_bits: int = int(math.log2(self.block_size))
        self.index_bits: int = int(math.log2(self.num_sets))
        self.tag_bits: int = 64 - self.offset_bits - self.index_bits

        self.sets: List[CacheSet] = [
            CacheSet(associativity) for _ in range(self.num_sets)
        ]

        # Métricas
        self.hits: int = 0
        self.misses: int = 0
        self.evictions: int = 0

    def decode_address(self, byte_addr: int) -> Tuple[int, int, int, int]:
        """Retorna (block_addr, tag, index, offset)."""
        block_addr = byte_addr >> self.offset_bits
        offset = byte_addr & ((1 << self.offset_bits) - 1)
        index = block_addr & ((1 << self.index_bits) - 1)
        tag = block_addr >> self.index_bits
        return block_addr, tag, index, offset

    def contains(self, byte_addr: int) -> bool:
        _, tag, index, _ = self.decode_address(byte_addr)
        return self.sets[index].find_block(tag) is not None

    def probe(self, byte_addr: int, current_cycle: int) -> bool:
        """Verifica acerto e atualiza timestamp LRU em caso de hit."""
        _, tag, index, _ = self.decode_address(byte_addr)
        is_hit = self.sets[index].access(tag, current_cycle)
        if is_hit:
            self.hits += 1
        else:
            self.misses += 1
        return is_hit

    def insert(self, byte_addr: int, current_cycle: int) -> Optional[int]:
        """
        Insere o bloco na cache. Retorna o byte_addr base do bloco desalojado (se houver).
        """
        block_addr, tag, index, _ = self.decode_address(byte_addr)
        evicted, _ = self.sets[index].insert(tag, block_addr, current_cycle)
        if evicted:
            self.evictions += 1
            evicted_byte_addr = evicted.block_addr << self.offset_bits
            return evicted_byte_addr
        return None

    def invalidate(self, byte_addr: int) -> bool:
        """Invalida o bloco se presente. Retorna True se foi invalidado."""
        _, tag, index, _ = self.decode_address(byte_addr)
        return self.sets[index].invalidate(tag)

    def remove(self, byte_addr: int) -> Optional[int]:
        """Remove o bloco da cache. Retorna o byte_addr se removido."""
        block_addr, tag, index, _ = self.decode_address(byte_addr)
        removed = self.sets[index].remove(tag)
        if removed:
            return removed.block_addr << self.offset_bits
        return None

    def get_hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0

    def get_miss_rate(self) -> float:
        return 1.0 - self.get_hit_rate()

    def reset_stats(self, clear_blocks: bool = False):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        if clear_blocks:
            self.sets = [CacheSet(self.associativity) for _ in range(self.num_sets)]


class MultilevelCacheHierarchy:
    """
    Controlador da hierarquia de 3 níveis de cache (L1, L2, L3) + RAM.
    Suporta políticas INCLUSIVE, EXCLUSIVE e NINE.
    """

    def __init__(
        self,
        policy: Policy = Policy.INCLUSIVE,
        l1_size: int = 32 * 1024,  # 32 KB
        l2_size: int = 512 * 1024,  # 512 KB
        l3_size: int = 16 * 1024 * 1024,  # 16 MB
        block_size: int = 64,  # 64 bytes
        l1_assoc: int = 8,
        l2_assoc: int = 8,
        l3_assoc: int = 16,
        l1_lat: int = 4,  # 4 ciclos
        l2_lat: int = 12,  # 12 ciclos
        l3_lat: int = 40,  # 40 ciclos
        ram_lat: int = 200,  # 200 ciclos
    ):
        self.policy: Policy = policy
        self.l1: CacheLevel = CacheLevel("L1", l1_size, block_size, l1_assoc, l1_lat)
        self.l2: CacheLevel = CacheLevel("L2", l2_size, block_size, l2_assoc, l2_lat)
        self.l3: CacheLevel = CacheLevel("L3", l3_size, block_size, l3_assoc, l3_lat)
        self.ram_lat: int = ram_lat

        self.current_cycle: int = 0
        self.total_accesses: int = 0
        self.ram_accesses: int = 0
        self.total_stall_cycles: int = 0
        self.back_invalidations: int = (
            0  # Invalidações forçadas da L1 por desalojamento na L2/L3 (Inclusive)
        )
        self.swaps: int = 0  # Movimentações/trocas de blocos (Exclusive)

    def reset_stats(self, clear_blocks: bool = False):
        """Zera os contadores de medição após a fase de warmup."""
        self.l1.reset_stats(clear_blocks=clear_blocks)
        self.l2.reset_stats(clear_blocks=clear_blocks)
        self.l3.reset_stats(clear_blocks=clear_blocks)
        self.total_accesses = 0
        self.ram_accesses = 0
        self.total_stall_cycles = 0
        self.back_invalidations = 0
        self.swaps = 0

    def access(self, byte_addr: int) -> Dict[str, Any]:
        """
        Executa um acesso à memória para o endereço especificado.
        Retorna dicionário com o resultado do ciclo.
        """
        self.total_accesses += 1
        self.current_cycle += 1

        cycles = self.l1.hit_latency

        # 1. Tenta L1
        l1_hit = self.l1.probe(byte_addr, self.current_cycle)
        if l1_hit:
            self.total_stall_cycles += cycles
            return {"hit_level": "L1", "cycles": cycles}

        # Miss em L1 -> Acessa L2
        cycles += self.l2.hit_latency
        l2_hit = self.l2.probe(byte_addr, self.current_cycle)

        if l2_hit:
            self._handle_l2_hit(byte_addr)
            self.total_stall_cycles += cycles
            return {"hit_level": "L2", "cycles": cycles}

        # Miss em L2 -> Acessa L3
        cycles += self.l3.hit_latency
        l3_hit = self.l3.probe(byte_addr, self.current_cycle)

        if l3_hit:
            self._handle_l3_hit(byte_addr)
            self.total_stall_cycles += cycles
            return {"hit_level": "L3", "cycles": cycles}

        # Miss em L3 -> Acessa RAM
        self.ram_accesses += 1
        cycles += self.ram_lat
        self._handle_ram_hit(byte_addr)
        self.total_stall_cycles += cycles
        return {"hit_level": "RAM", "cycles": cycles}

    # -------------------------------------------------------------
    # Tratamentos específicos de cada política
    # -------------------------------------------------------------
    def _handle_l2_hit(self, byte_addr: int):
        if self.policy == Policy.INCLUSIVE:
            # Na Inclusiva: o bloco já reside em L2 (e L3). Aloca em L1.
            self.l1.insert(byte_addr, self.current_cycle)

        elif self.policy == Policy.EXCLUSIVE:
            # Na Exclusiva: o bloco estava em L2, mas agora deve ir para L1 e ser REMOVIDO de L2!
            self.l2.remove(byte_addr)
            # Ao inserir em L1, o bloco despejado (victim) vai para L2 (swap)
            evicted_l1 = self.l1.insert(byte_addr, self.current_cycle)
            self.swaps += 1
            if evicted_l1 is not None:
                evicted_l2 = self.l2.insert(evicted_l1, self.current_cycle)
                if evicted_l2 is not None:
                    self.l3.insert(evicted_l2, self.current_cycle)

        elif self.policy == Policy.NINE:
            # Não-inclusiva, não-exclusiva: copia para L1 sem afetar L2
            self.l1.insert(byte_addr, self.current_cycle)

    def _handle_l3_hit(self, byte_addr: int):
        if self.policy == Policy.INCLUSIVE:
            # Insere em L2 e L1
            evicted_l2 = self.l2.insert(byte_addr, self.current_cycle)
            if evicted_l2 is not None:
                # Se desalojou de L2, deve invalidar em L1 se estiver lá (Back-invalidation)
                if self.l1.invalidate(evicted_l2):
                    self.back_invalidations += 1
            self.l1.insert(byte_addr, self.current_cycle)

        elif self.policy == Policy.EXCLUSIVE:
            # O bloco sai de L3 e vai para L1
            self.l3.remove(byte_addr)
            evicted_l1 = self.l1.insert(byte_addr, self.current_cycle)
            self.swaps += 1
            if evicted_l1 is not None:
                evicted_l2 = self.l2.insert(evicted_l1, self.current_cycle)
                if evicted_l2 is not None:
                    self.l3.insert(evicted_l2, self.current_cycle)

        elif self.policy == Policy.NINE:
            self.l2.insert(byte_addr, self.current_cycle)
            self.l1.insert(byte_addr, self.current_cycle)

    def _handle_ram_hit(self, byte_addr: int):
        if self.policy == Policy.INCLUSIVE:
            # Insere em todos os níveis: L3 -> L2 -> L1
            evicted_l3 = self.l3.insert(byte_addr, self.current_cycle)
            if evicted_l3 is not None:
                # Back-invalidation: remove de L2 e L1
                if self.l2.invalidate(evicted_l3):
                    self.back_invalidations += 1
                if self.l1.invalidate(evicted_l3):
                    self.back_invalidations += 1

            evicted_l2 = self.l2.insert(byte_addr, self.current_cycle)
            if evicted_l2 is not None:
                if self.l1.invalidate(evicted_l2):
                    self.back_invalidations += 1

            self.l1.insert(byte_addr, self.current_cycle)

        elif self.policy == Policy.EXCLUSIVE:
            # Na exclusiva pura: aloca apenas na L1!
            evicted_l1 = self.l1.insert(byte_addr, self.current_cycle)
            if evicted_l1 is not None:
                evicted_l2 = self.l2.insert(evicted_l1, self.current_cycle)
                if evicted_l2 is not None:
                    self.l3.insert(evicted_l2, self.current_cycle)

        elif self.policy == Policy.NINE:
            self.l3.insert(byte_addr, self.current_cycle)
            self.l2.insert(byte_addr, self.current_cycle)
            self.l1.insert(byte_addr, self.current_cycle)

    def get_amat(self) -> float:
        """Retorna o Tempo Médio de Acesso à Memória (AMAT / TMAM) medido experimentalmente."""
        if self.total_accesses == 0:
            return 0.0
        return self.total_stall_cycles / self.total_accesses

    def get_effective_capacity_bytes(self) -> int:
        """Calcula a capacidade útil total da hierarquia sob a política atual."""
        if self.policy == Policy.INCLUSIVE:
            # Inclusiva: limitada ao maior nível (L3 engloba L2 e L1)
            return self.l3.size_bytes
        elif self.policy == Policy.EXCLUSIVE:
            # Exclusiva: soma perfeita dos níveis
            return self.l1.size_bytes + self.l2.size_bytes + self.l3.size_bytes
        else:  # NINE
            # Intermediária (entre L3 e a soma)
            return int(
                self.l3.size_bytes + 0.8 * self.l2.size_bytes + 0.9 * self.l1.size_bytes
            )

    def summary(self) -> Dict[str, Any]:
        """Gera um sumário completo de métricas."""
        h1 = self.l1.get_hit_rate()
        m1 = self.l1.get_miss_rate()
        h2_local = self.l2.get_hit_rate()
        m2_local = self.l2.get_miss_rate()
        h3_local = self.l3.get_hit_rate()
        m3_local = self.l3.get_miss_rate()

        # Taxas globais
        h1_glob = self.l1.hits / self.total_accesses if self.total_accesses else 0
        h2_glob = self.l2.hits / self.total_accesses if self.total_accesses else 0
        h3_glob = self.l3.hits / self.total_accesses if self.total_accesses else 0
        ram_glob = self.ram_accesses / self.total_accesses if self.total_accesses else 0

        # AMAT Teórico
        # AMAT = t1 + m1 * (t2 + m2_local * (t3 + m3_local * t_ram))
        amat_theo = self.l1.hit_latency + m1 * (
            self.l2.hit_latency
            + m2_local * (self.l3.hit_latency + m3_local * self.ram_lat)
        )

        return {
            "policy": self.policy.value,
            "total_accesses": self.total_accesses,
            "l1_hits": self.l1.hits,
            "l1_misses": self.l1.misses,
            "l1_hit_rate": h1,
            "l2_hits": self.l2.hits,
            "l2_misses": self.l2.misses,
            "l2_hit_rate_local": h2_local,
            "l3_hits": self.l3.hits,
            "l3_misses": self.l3.misses,
            "l3_hit_rate_local": h3_local,
            "ram_accesses": self.ram_accesses,
            "global_hit_l1": h1_glob,
            "global_hit_l2": h2_glob,
            "global_hit_l3": h3_glob,
            "global_ram": ram_glob,
            "back_invalidations": self.back_invalidations,
            "swaps": self.swaps,
            "measured_amat": self.get_amat(),
            "theoretical_amat": amat_theo,
            "effective_capacity_kb": self.get_effective_capacity_bytes() / 1024,
        }
