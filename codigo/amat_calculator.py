#!/usr/bin/env python3
"""
Cálculos Analíticos do Tempo Médio de Acesso à Memória (AMAT / TMAM)
"""

from typing import Dict, Any


def calculate_amat_single_level(
    h1: float, t1: float = 4.0, t_ram: float = 200.0
) -> float:
    """Cálculo do AMAT para sistema de apenas 1 nível (L1 + RAM)."""
    m1 = 1.0 - h1
    return t1 + m1 * t_ram


def calculate_amat_two_level_local(
    h1: float = 0.90,
    h2_local: float = 0.99,
    t1: float = 4.0,
    t2: float = 12.0,
    t_ram: float = 200.0,
) -> Dict[str, Any]:
    """
    Cálculo do AMAT para 2 níveis com H2 interpretado como Taxa de Acerto Local.
    H1 = 90% (M1 = 10%)
    H2_local = 99% (M2_local = 1%)
    """
    m1 = 1.0 - h1
    m2_local = 1.0 - h2_local
    m2_global = m1 * m2_local

    l1_miss_penalty = t2 + m2_local * t_ram
    amat = t1 + m1 * l1_miss_penalty

    return {
        "interpretation": "H2 Local (99% de acerto nas falhas da L1)",
        "h1": h1,
        "m1": m1,
        "h2_local": h2_local,
        "m2_local": m2_local,
        "m2_global": m2_global,
        "l1_miss_penalty": l1_miss_penalty,
        "amat": amat,
        "t1": t1,
        "t2": t2,
        "t_ram": t_ram,
    }


def calculate_amat_two_level_global(
    h1: float = 0.90,
    h_combined_global: float = 0.99,
    t1: float = 4.0,
    t2: float = 12.0,
    t_ram: float = 200.0,
) -> Dict[str, Any]:
    """
    Cálculo do AMAT para 2 níveis com H2 interpretado como Taxa de Acerto Global Acumulada.
    L1+L2 atendem 99% das requisições totais (apenas 1% vai para RAM).
    Portanto, M2_local = 0.01 / 0.10 = 10% (H2_local = 90%).
    """
    m1 = 1.0 - h1
    m_global = 1.0 - h_combined_global
    m2_local = m_global / m1 if m1 > 0 else 0.0
    h2_local = 1.0 - m2_local

    l1_miss_penalty = t2 + m2_local * t_ram
    amat = t1 + m1 * l1_miss_penalty

    return {
        "interpretation": "H2 Global Acumulado (99% das requisições totais resolvidas em cache)",
        "h1": h1,
        "m1": m1,
        "h_combined_global": h_combined_global,
        "m2_local": m2_local,
        "h2_local": h2_local,
        "m2_global": m_global,
        "l1_miss_penalty": l1_miss_penalty,
        "amat": amat,
        "t1": t1,
        "t2": t2,
        "t_ram": t_ram,
    }


def calculate_amat_three_level(
    h1: float = 0.90,
    h2_local: float = 0.99,
    h3_local: float = 0.95,
    t1: float = 4.0,
    t2: float = 12.0,
    t3: float = 40.0,
    t_ram: float = 200.0,
) -> Dict[str, Any]:
    """
    Cálculo do AMAT para a hierarquia completa de 3 níveis (L1 + L2 + L3 + RAM).
    AMAT = t1 + M1 * [ t2 + M2_local * ( t3 + M3_local * t_RAM ) ]
    """
    m1 = 1.0 - h1
    m2_local = 1.0 - h2_local
    m3_local = 1.0 - h3_local

    l2_miss_penalty = t3 + m3_local * t_ram
    l1_miss_penalty = t2 + m2_local * l2_miss_penalty
    amat = t1 + m1 * l1_miss_penalty

    return {
        "interpretation": "Hierarquia Completa 3 Níveis (L1 + L2 + L3 + RAM)",
        "h1": h1,
        "m1": m1,
        "h2_local": h2_local,
        "m2_local": m2_local,
        "h3_local": h3_local,
        "m3_local": m3_local,
        "l2_miss_penalty": l2_miss_penalty,
        "l1_miss_penalty": l1_miss_penalty,
        "amat": amat,
        "global_miss_to_ram": m1 * m2_local * m3_local,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "t_ram": t_ram,
    }


if __name__ == "__main__":
    print("=" * 70)
    print(" ANÁLISE MATEMÁTICA ANALÍTICA DO AMAT (GRUPO 7)")
    print("=" * 70)

    # 1 Nível
    amat_1l = calculate_amat_single_level(0.90)
    print(f"\n1) Apenas L1 (90% hit): AMAT = {amat_1l:.2f} ciclos")

    # 2 Níveis - Local
    r_local = calculate_amat_two_level_local()
    print(f"\n2) L1 (90%) + L2 (99% local):")
    print(f"   - Penalidade de Falha da L1: {r_local['l1_miss_penalty']:.2f} ciclos")
    print(f"   - AMAT = {r_local['amat']:.2f} ciclos")
    print(
        f"   - Redução em relação a L1 pura: {(1 - r_local['amat'] / amat_1l) * 100:.1f}%"
    )

    # 2 Níveis - Global
    r_global = calculate_amat_two_level_global()
    print(f"\n3) L1 (90%) + L2 (99% global acumulado):")
    print(f"   - Taxa Local da L2 equivalente: {r_global['h2_local'] * 100:.1f}%")
    print(f"   - Penalidade de Falha da L1: {r_global['l1_miss_penalty']:.2f} ciclos")
    print(f"   - AMAT = {r_global['amat']:.2f} ciclos")

    # 3 Níveis
    r_3l = calculate_amat_three_level()
    print(f"\n4) Hierarquia Completa L1 (90%) + L2 (99% local) + L3 (95% local):")
    print(f"   - Penalidade de Falha da L2: {r_3l['l2_miss_penalty']:.2f} ciclos")
    print(f"   - Penalidade de Falha da L1: {r_3l['l1_miss_penalty']:.2f} ciclos")
    print(f"   - AMAT = {r_3l['amat']:.2f} ciclos")
    print(
        f"   - Acessos que chegam à RAM: {r_3l['global_miss_to_ram'] * 100:.4f}% das requisições"
    )
    print("=" * 70)
