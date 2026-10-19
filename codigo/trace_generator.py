#!/usr/bin/env python3
"""
Gerador de Traces de Memória para Simulação de Cache Multinível
"""

import random
from typing import List


def generate_controlled_trace(
    total_accesses: int = 50000,
    target_l1_hit_rate: float = 0.90,
    target_l2_hit_rate: float = 0.99,
    block_size: int = 64,
    seed: int = 42,
) -> List[int]:
    """
    Gera um trace sintético calibrado para atingir aproximadamente as taxas solicitadas:
    - 90% de acertos na L1
    - 99% de acertos na L2 (para as requisições que chegam à L2)
    """
    random.seed(seed)
    # L1: 32 KB (512 blocos de 64B)
    # L2: 512 KB (8192 blocos de 64B)
    # L3: 8 MB (131072 blocos de 64B)

    # 1. Hot set para L1 (32 blocos). Sempre cabe e permanece na L1.
    l1_hot = [i * block_size for i in range(32)]

    # 2. Working set para L2 (1000 blocos = 64 KB).
    # 1000 > 512 (capacidade da L1) -> Miss garantido na L1 por capacidade
    # 1000 < 8192 (capacidade da L2) -> Hit garantido na L2
    l2_working_set = [10000 * block_size + i * block_size for i in range(1000)]

    # 3. Working set para L3 (10000 blocos = 640 KB).
    # 10000 > 8192 (capacidade da L2) -> Miss na L2
    # 10000 < 131072 (capacidade da L3) -> Hit na L3
    l3_working_set = [100000 * block_size + i * block_size for i in range(10000)]

    # 4. RAM
    ram_blocks = [5000000 * block_size + i * block_size for i in range(2000)]

    # Warmup trace: inicializa os blocos na cache
    warmup_trace = l1_hot + l2_working_set + l3_working_set[:500]

    # Measurement trace
    measurement_trace = []
    l2_idx = 0
    l3_idx = 0
    ram_idx = 0

    for _ in range(total_accesses):
        r = random.random()
        if r < target_l1_hit_rate:
            measurement_trace.append(random.choice(l1_hot))
        else:
            r2 = random.random()
            if r2 < target_l2_hit_rate:
                measurement_trace.append(l2_working_set[l2_idx % len(l2_working_set)])
                l2_idx += 1
            else:
                if random.random() < 0.90:
                    measurement_trace.append(
                        l3_working_set[l3_idx % len(l3_working_set)]
                    )
                    l3_idx += 1
                else:
                    measurement_trace.append(ram_blocks[ram_idx % len(ram_blocks)])
                    ram_idx += 1

    return warmup_trace, measurement_trace


def generate_zipf_trace(
    total_accesses: int = 50000,
    num_unique_blocks: int = 10000,
    alpha: float = 1.2,
    block_size: int = 64,
    seed: int = 42,
) -> List[int]:
    """
    Gera acessos segundo uma distribuição Zipfiana (Lei de Potência),
    representativa de padrões reais de execução com forte localidade temporal.
    """
    random.seed(seed)
    # Gera probabilidades normalizadas de Zipf
    weights = [1.0 / (i**alpha) for i in range(1, num_unique_blocks + 1)]
    sum_w = sum(weights)
    norm_weights = [w / sum_w for w in weights]

    # Amostragem usando random.choices
    blocks = list(range(num_unique_blocks))
    chosen_blocks = random.choices(blocks, weights=norm_weights, k=total_accesses)

    return [b * block_size for b in chosen_blocks]


def generate_working_set_sweep_trace(
    working_set_bytes: int,
    total_accesses: int = 30000,
    block_size: int = 64,
    temporal_locality_factor: float = 0.8,
    seed: int = 42,
) -> List[int]:
    """
    Gera um trace com um tamanho de working set controlado em bytes.
    Permite varrer o tamanho do conjunto de trabalho para comparar
    o comportamento das políticas Inclusiva vs Exclusiva.
    """
    random.seed(seed)
    num_blocks = max(1, working_set_bytes // block_size)
    blocks = [i * block_size for i in range(num_blocks)]

    trace = []
    # Cria uma lista com alta repetição no conjunto
    for _ in range(total_accesses):
        if random.random() < temporal_locality_factor and num_blocks > 10:
            # Acessa os 20% mais frequentes dentro do working set
            hot_range = max(1, int(num_blocks * 0.2))
            trace.append(blocks[random.randint(0, hot_range - 1)])
        else:
            trace.append(random.choice(blocks))

    return trace


def generate_matrix_stride_trace(n: int = 128, block_size: int = 64) -> List[int]:
    """
    Gera o trace de acessos de uma multiplicação ingênua de matrizes C = A x B de tamanho N x N.
    Cada elemento é um double (8 bytes). Exibe stride de coluna na matriz B!
    """
    elem_size = 8
    matrix_bytes = n * n * elem_size
    base_a = 0
    base_b = matrix_bytes
    base_c = 2 * matrix_bytes

    trace = []
    for i in range(n):
        for j in range(n):
            for k in range(n):
                addr_a = base_a + (i * n + k) * elem_size
                addr_b = base_b + (k * n + j) * elem_size
                addr_c = base_c + (i * n + j) * elem_size
                trace.append(addr_a)
                trace.append(addr_b)
                trace.append(addr_c)
    return trace
