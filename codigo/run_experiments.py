#!/usr/bin/env python3
"""
Execução dos Experimentos de Cache Multinível
Gera arquivos CSV e resumos estatísticos em results/
"""

import os
import csv
import json
from cache_simulator import MultilevelCacheHierarchy, Policy
from trace_generator import (
    generate_controlled_trace,
    generate_zipf_trace,
    generate_working_set_sweep_trace,
    generate_matrix_stride_trace,
)
from amat_calculator import (
    calculate_amat_two_level_local,
    calculate_amat_two_level_global,
    calculate_amat_three_level,
    calculate_amat_single_level,
)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def run_experiment_1_prompt_challenge():
    """
    Experimento 1: O Desafio Central do Enunciado
    'Simular L1 90 %, L2 99 % + calcular tempo médio'
    """
    print(">>> Executando Experimento 1: Desafio Central (L1 90% e L2 99%)...")
    total_accesses = 60000
    warmup_trace, measurement_trace = generate_controlled_trace(
        total_accesses=total_accesses,
        target_l1_hit_rate=0.90,
        target_l2_hit_rate=0.99,
        seed=42,
    )

    policies = [Policy.INCLUSIVE, Policy.EXCLUSIVE, Policy.NINE]
    results = []

    for pol in policies:
        # Hierarquia com parâmetros típicos
        sim = MultilevelCacheHierarchy(
            policy=pol,
            l1_size=32 * 1024,
            l2_size=512 * 1024,
            l3_size=8 * 1024 * 1024,
            l1_lat=4,
            l2_lat=12,
            l3_lat=40,
            ram_lat=200,
        )
        # 1. Warmup
        for addr in warmup_trace:
            sim.access(addr)

        # 2. Reseta contadores para medir estado estacionário
        sim.reset_stats()

        # 3. Medição
        for addr in measurement_trace:
            sim.access(addr)

        res = sim.summary()
        results.append(res)

    # Cálculos teóricos
    theo_local = calculate_amat_two_level_local(
        h1=0.90, h2_local=0.99, t1=4, t2=12, t_ram=200
    )
    theo_global = calculate_amat_two_level_global(
        h1=0.90, h_combined_global=0.99, t1=4, t2=12, t_ram=200
    )
    theo_3l = calculate_amat_three_level(
        h1=0.90, h2_local=0.99, h3_local=0.95, t1=4, t2=12, t3=40, t_ram=200
    )
    theo_1l = calculate_amat_single_level(h1=0.90, t1=4, t_ram=200)

    # Salva em JSON e CSV
    exp1_file = os.path.join(RESULTS_DIR, "exp1_desafio_central.json")
    payload = {
        "theoretical": {
            "single_level_l1_90": theo_1l,
            "two_level_local": theo_local,
            "two_level_global": theo_global,
            "three_level": theo_3l,
        },
        "simulated": results,
    }
    with open(exp1_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    csv_file = os.path.join(RESULTS_DIR, "exp1_desafio_central.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Politica",
                "Acessos",
                "Hits_L1",
                "Taxa_L1(%)",
                "Hits_L2",
                "Taxa_L2_Local(%)",
                "Hits_L3",
                "Taxa_L3_Local(%)",
                "Acessos_RAM",
                "Back_Invalidations",
                "Swaps",
                "AMAT_Medido(ciclos)",
                "AMAT_Teorico(ciclos)",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r["policy"],
                    r["total_accesses"],
                    r["l1_hits"],
                    f"{r['l1_hit_rate'] * 100:.2f}",
                    r["l2_hits"],
                    f"{r['l2_hit_rate_local'] * 100:.2f}",
                    r["l3_hits"],
                    f"{r['l3_hit_rate_local'] * 100:.2f}",
                    r["ram_accesses"],
                    r["back_invalidations"],
                    r["swaps"],
                    f"{r['measured_amat']:.3f}",
                    f"{r['theoretical_amat']:.3f}",
                ]
            )
    print(f"    Experimento 1 concluído. Resultados salvos em {csv_file}")


def run_experiment_2_working_set_sweep():
    """
    Experimento 2: Variação do Tamanho do Conjunto de Trabalho (Working Set)
    Compara Inclusiva vs Exclusiva vs NINE sob pressão de capacidade.
    Configuração:
      L1: 16 KB
      L2: 64 KB
      L3: 256 KB
      Capacidade Inclusiva Efetiva: 256 KB
      Capacidade Exclusiva Efetiva: 16 + 64 + 256 = 336 KB (+31%)
    """
    print(
        ">>> Executando Experimento 2: Varredura de Working Set (Inclusiva vs Exclusiva)..."
    )
    working_sets_kb = [16, 32, 64, 128, 192, 256, 300, 336, 400, 512]
    policies = [Policy.INCLUSIVE, Policy.EXCLUSIVE, Policy.NINE]

    rows = []
    for ws_kb in working_sets_kb:
        ws_bytes = ws_kb * 1024
        trace = generate_working_set_sweep_trace(
            working_set_bytes=ws_bytes, total_accesses=25000, seed=42 + ws_kb
        )
        for pol in policies:
            sim = MultilevelCacheHierarchy(
                policy=pol,
                l1_size=16 * 1024,
                l2_size=64 * 1024,
                l3_size=256 * 1024,
                block_size=64,
                l1_assoc=4,
                l2_assoc=8,
                l3_assoc=16,
                l1_lat=4,
                l2_lat=12,
                l3_lat=35,
                ram_lat=200,
            )
            for addr in trace:
                sim.access(addr)

            s = sim.summary()
            rows.append(
                {
                    "working_set_kb": ws_kb,
                    "policy": pol.value,
                    "l1_hit_rate": s["l1_hit_rate"],
                    "l2_hit_rate_local": s["l2_hit_rate_local"],
                    "l3_hit_rate_local": s["l3_hit_rate_local"],
                    "global_ram_miss_rate": s["global_ram"],
                    "back_invalidations": s["back_invalidations"],
                    "swaps": s["swaps"],
                    "amat": s["measured_amat"],
                }
            )

    csv_file = os.path.join(RESULTS_DIR, "exp2_working_set_sweep.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"    Experimento 2 concluído. Resultados salvos em {csv_file}")


def run_experiment_3_ram_latency_sensitivity():
    """
    Experimento 3: Sensibilidade do AMAT à Latência da RAM (Muro da Memória)
    Varia a latência da RAM de 50 a 350 ciclos.
    """
    print(
        ">>> Executando Experimento 3: Sensibilidade ao Muro da Memória (Latência da RAM)..."
    )
    ram_latencies = [50, 100, 150, 200, 250, 300, 350, 400]
    trace = generate_zipf_trace(
        total_accesses=30000, num_unique_blocks=8000, alpha=1.1, seed=123
    )

    rows = []
    for ram_lat in ram_latencies:
        for pol in [Policy.INCLUSIVE, Policy.EXCLUSIVE]:
            sim = MultilevelCacheHierarchy(
                policy=pol,
                l1_size=32 * 1024,
                l2_size=256 * 1024,
                l3_size=2 * 1024 * 1024,
                l1_lat=4,
                l2_lat=12,
                l3_lat=35,
                ram_lat=ram_lat,
            )
            for addr in trace:
                sim.access(addr)
            s = sim.summary()
            rows.append(
                {
                    "ram_latency": ram_lat,
                    "policy": pol.value,
                    "amat": s["measured_amat"],
                    "ram_accesses": s["ram_accesses"],
                }
            )

    csv_file = os.path.join(RESULTS_DIR, "exp3_ram_sensitivity.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["ram_latency", "policy", "amat", "ram_accesses"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"    Experimento 3 concluído. Resultados salvos em {csv_file}")


def run_experiment_4_matrix_multiplication():
    """
    Experimento 4: Benchmark de Algoritmo Real (Multiplicação de Matrizes N x N)
    """
    print(
        ">>> Executando Experimento 4: Benchmark de Multiplicação de Matrizes (N=48)..."
    )
    trace = generate_matrix_stride_trace(n=48)  # ~331.776 acessos à memória

    rows = []
    for pol in [Policy.INCLUSIVE, Policy.EXCLUSIVE, Policy.NINE]:
        sim = MultilevelCacheHierarchy(
            policy=pol,
            l1_size=32 * 1024,
            l2_size=256 * 1024,
            l3_size=2 * 1024 * 1024,
            l1_lat=4,
            l2_lat=12,
            l3_lat=35,
            ram_lat=200,
        )
        for addr in trace:
            sim.access(addr)
        s = sim.summary()
        rows.append(
            {
                "workload": "Matrix Mult 48x48",
                "policy": pol.value,
                "total_accesses": s["total_accesses"],
                "l1_hits": s["l1_hits"],
                "l1_hit_rate": s["l1_hit_rate"],
                "l2_hits": s["l2_hits"],
                "l2_hit_rate_local": s["l2_hit_rate_local"],
                "l3_hits": s["l3_hits"],
                "ram_accesses": s["ram_accesses"],
                "back_invalidations": s["back_invalidations"],
                "swaps": s["swaps"],
                "amat": s["measured_amat"],
            }
        )

    csv_file = os.path.join(RESULTS_DIR, "exp4_matrix_benchmark.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"    Experimento 4 concluído. Resultados salvos em {csv_file}")


if __name__ == "__main__":
    run_experiment_1_prompt_challenge()
    run_experiment_2_working_set_sweep()
    run_experiment_3_ram_latency_sensitivity()
    run_experiment_4_matrix_multiplication()
    print("\nTodos os experimentos foram executados com sucesso!")
