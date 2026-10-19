#!/usr/bin/env python3
"""
Geração de Gráficos de Alta Resolução para o Relatório e Slides
"""

import os
import csv
import json
import matplotlib.pyplot as plt
import numpy as np

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "figures")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
os.makedirs(FIGURES_DIR, exist_ok=True)

# Configuração de estilo para publicação acadêmica
plt.rcParams.update(
    {
        "font.size": 11,
        "font.family": "serif",
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "lines.linewidth": 2,
        "grid.alpha": 0.4,
        "grid.linestyle": "--",
    }
)


def plot_experiment_1():
    """Gráfico 1: Comparativo de AMAT no Desafio Central (L1 90% e L2 99%)."""
    json_path = os.path.join(RESULTS_DIR, "exp1_desafio_central.json")
    if not os.path.exists(json_path):
        print("Arquivo exp1_desafio_central.json não encontrado.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    theo = data["theoretical"]
    sim = data["simulated"]

    categories = [
        "L1 Única\n(90% hit)",
        "Teórico 2 Nív.\n(H2 Local 99%)",
        "Teórico 2 Nív.\n(H2 Glob. 99%)",
        "Simulado\nInclusiva",
        "Simulado\nExclusiva",
        "Simulado\nNINE",
    ]

    values = [
        theo["single_level_l1_90"],
        theo["two_level_local"]["amat"],
        theo["two_level_global"]["amat"],
        sim[0]["measured_amat"],
        sim[1]["measured_amat"],
        sim[2]["measured_amat"],
    ]

    colors = ["#d9534f", "#f0ad4e", "#0275d8", "#5bc0de", "#5cb85c", "#6f42c1"]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars = ax.bar(
        categories, values, color=colors, width=0.55, edgecolor="black", linewidth=1.2
    )

    for bar in bars:
        h = bar.get_height()
        ax.annotate(
            f"{h:.2f} c",
            xy=(bar.get_x() + bar.get_width() / 2, h),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    ax.set_ylabel("AMAT - Tempo Médio de Acesso (Ciclos de Clock)")
    ax.set_title(
        "Comparação de AMAT: Impacto da Cache L2 e Políticas Multinível\n(Desafio: L1 = 90% e L2 = 99%)",
        pad=15,
    )
    ax.set_ylim(0, max(values) * 1.15)
    ax.grid(axis="y")

    # Linha de destaque mostrando o benefício de ter L2
    ax.annotate(
        f"Redução de {(1 - values[1] / values[0]) * 100:.1f}% no tempo médio\ncom a adição da L2!",
        xy=(1, values[1]),
        xytext=(1.8, 16),
        arrowprops=dict(arrowstyle="->", color="black", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="black", lw=1),
    )

    plt.tight_layout()
    out_file = os.path.join(FIGURES_DIR, "fig1_amat_desafio_90_99.png")
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Salvo: {out_file}")


def plot_experiment_2():
    """Gráfico 2 e 3: Varredura de Working Set (Inclusiva vs Exclusiva)."""
    csv_path = os.path.join(RESULTS_DIR, "exp2_working_set_sweep.csv")
    if not os.path.exists(csv_path):
        return

    data = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pol = row["policy"]
            if pol not in data:
                data[pol] = {"ws": [], "amat": [], "ram_miss": [], "back_inv": []}
            data[pol]["ws"].append(float(row["working_set_kb"]))
            data[pol]["amat"].append(float(row["amat"]))
            data[pol]["ram_miss"].append(float(row["global_ram_miss_rate"]) * 100)
            data[pol]["back_inv"].append(int(row["back_invalidations"]))

    # Gráfico 2A: AMAT vs Working Set
    fig, ax = plt.subplots(figsize=(8.5, 5))
    markers = {
        "Inclusiva": "o-",
        "Exclusiva": "s--",
        "NINE (Não-Inclusiva / Não-Exclusiva)": "^-.",
    }
    colors = {
        "Inclusiva": "#d9534f",
        "Exclusiva": "#5cb85c",
        "NINE (Não-Inclusiva / Não-Exclusiva)": "#0275d8",
    }

    for pol, vals in data.items():
        label_name = (
            "Inclusiva"
            if "Inclusiva" in pol and "Não" not in pol
            else ("Exclusiva" if "Exclusiva" in pol and "Não" not in pol else "NINE")
        )
        ax.plot(
            vals["ws"],
            vals["amat"],
            markers.get(pol, "o-"),
            label=label_name,
            color=colors.get(pol, "black"),
        )

    # Linhas verticais indicando as capacidades da hierarquia
    ax.axvline(
        256, color="red", linestyle=":", label="Capacidade Inclusiva (L3 = 256 KB)"
    )
    ax.axvline(
        336,
        color="green",
        linestyle=":",
        label="Capacidade Exclusiva (L1+L2+L3 = 336 KB)",
    )

    ax.set_xlabel("Tamanho do Working Set (KB)")
    ax.set_ylabel("AMAT Medido (Ciclos)")
    ax.set_title(
        "Sensibilidade do AMAT ao Tamanho do Working Set\n(Inclusiva vs Exclusiva vs NINE)",
        pad=15,
    )
    ax.legend(loc="upper left")
    ax.grid(True)

    plt.tight_layout()
    out_file1 = os.path.join(FIGURES_DIR, "fig2_working_set_amat.png")
    plt.savefig(out_file1, dpi=300)
    plt.close()
    print(f"Salvo: {out_file1}")

    # Gráfico 2B: Falhas que vão para RAM (%)
    fig, ax = plt.subplots(figsize=(8.5, 5))
    for pol, vals in data.items():
        label_name = (
            "Inclusiva"
            if "Inclusiva" in pol and "Não" not in pol
            else ("Exclusiva" if "Exclusiva" in pol and "Não" not in pol else "NINE")
        )
        ax.plot(
            vals["ws"],
            vals["ram_miss"],
            markers.get(pol, "o-"),
            label=label_name,
            color=colors.get(pol, "black"),
        )

    ax.axvline(256, color="red", linestyle=":")
    ax.axvline(336, color="green", linestyle=":")
    ax.set_xlabel("Tamanho do Working Set (KB)")
    ax.set_ylabel("Acessos à Memória RAM (%)")
    ax.set_title(
        "Taxa de Acessos à RAM sob Pressão de Capacidade\n(Vantagem de Capacidade Útil da Política Exclusiva)",
        pad=15,
    )
    ax.legend(loc="upper left")
    ax.grid(True)

    plt.tight_layout()
    out_file2 = os.path.join(FIGURES_DIR, "fig3_working_set_ram_misses.png")
    plt.savefig(out_file2, dpi=300)
    plt.close()
    print(f"Salvo: {out_file2}")

    # Gráfico 2C: Invalidações Reversas (Back-Invalidations) na Inclusiva
    fig, ax = plt.subplots(figsize=(8, 4.5))
    inc_data = None
    for pol, vals in data.items():
        if "Inclusiva" in pol and "Não" not in pol:
            inc_data = vals
            break
    if inc_data:
        ax.bar(
            [str(int(w)) for w in inc_data["ws"]],
            inc_data["back_inv"],
            color="#e74c3c",
            edgecolor="black",
            width=0.6,
        )
        ax.set_xlabel("Tamanho do Working Set (KB)")
        ax.set_ylabel("Quantidade de Back-Invalidations na L1")
        ax.set_title(
            "Penalidade da Política Inclusiva: Invalidações Reversas Forçadas na L1",
            pad=15,
        )
        ax.grid(axis="y")
        plt.tight_layout()
        out_file3 = os.path.join(FIGURES_DIR, "fig4_back_invalidations.png")
        plt.savefig(out_file3, dpi=300)
        plt.close()
        print(f"Salvo: {out_file3}")


def plot_experiment_3():
    """Gráfico 4: Sensibilidade ao Muro da Memória (Latência da RAM)."""
    csv_path = os.path.join(RESULTS_DIR, "exp3_ram_sensitivity.csv")
    if not os.path.exists(csv_path):
        return

    data = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pol = row["policy"]
            if pol not in data:
                data[pol] = {"ram_lat": [], "amat": []}
            data[pol]["ram_lat"].append(float(row["ram_latency"]))
            data[pol]["amat"].append(float(row["amat"]))

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"Inclusiva": "#c0392b", "Exclusiva": "#27ae60"}
    for pol, vals in data.items():
        name = "Inclusiva" if "Inclusiva" in pol else "Exclusiva"
        ax.plot(
            vals["ram_lat"],
            vals["amat"],
            "o-",
            label=f"Política {name}",
            color=colors.get(name, "black"),
            lw=2.2,
        )

    ax.set_xlabel("Latência de Acesso à RAM (Ciclos de Clock)")
    ax.set_ylabel("AMAT (Ciclos de Clock)")
    ax.set_title("Efeito do 'Muro da Memória' (Memory Wall) no AMAT", pad=15)
    ax.grid(True)
    ax.legend(loc="upper left")

    plt.tight_layout()
    out_file = os.path.join(FIGURES_DIR, "fig5_memory_wall_sensitivity.png")
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Salvo: {out_file}")


def plot_intel_amd_diagram():
    """Gera um diagrama ilustrativo comparando as hierarquias Intel e AMD modernas."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 6))

    # Painel 1: Intel Core i9 (Raptor Lake / Core Ultra)
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 12)
    ax1.axis("off")
    ax1.set_title(
        "Arquitetura Intel (Core i9 / Raptor Lake)\nPolítica: Híbrida / Não-Inclusiva (L3 Smart Cache)",
        fontsize=11,
        fontweight="bold",
    )

    # Cores
    ax1.add_patch(
        plt.Rectangle(
            (0.8, 8.5),
            3.8,
            2.5,
            facecolor="#e8f4f8",
            edgecolor="#0275d8",
            lw=2,
            linestyle="--",
        )
    )
    ax1.text(
        2.7, 10.3, "Núcleo 0 (P-Core)", ha="center", fontweight="bold", color="#0275d8"
    )
    ax1.add_patch(
        plt.Rectangle(
            (1.2, 8.8), 3.0, 1.0, facecolor="#b3d7ff", edgecolor="#004085", lw=1.5
        )
    )
    ax1.text(
        2.7, 9.3, "L1 I/D: 80 KB (Privada)\n~4-5 ciclos", ha="center", fontsize=8.5
    )

    ax1.add_patch(
        plt.Rectangle(
            (5.4, 8.5),
            3.8,
            2.5,
            facecolor="#e8f4f8",
            edgecolor="#0275d8",
            lw=2,
            linestyle="--",
        )
    )
    ax1.text(
        7.3, 10.3, "Núcleo 1 (P-Core)", ha="center", fontweight="bold", color="#0275d8"
    )
    ax1.add_patch(
        plt.Rectangle(
            (5.8, 8.8), 3.0, 1.0, facecolor="#b3d7ff", edgecolor="#004085", lw=1.5
        )
    )
    ax1.text(
        7.3, 9.3, "L1 I/D: 80 KB (Privada)\n~4-5 ciclos", ha="center", fontsize=8.5
    )

    # L2 caches
    ax1.add_patch(
        plt.Rectangle(
            (1.2, 5.8), 3.0, 1.8, facecolor="#99c2ff", edgecolor="#003366", lw=1.5
        )
    )
    ax1.text(
        2.7,
        6.7,
        "L2: 2 MB (Privada)\n~16 ciclos\n(Não-Inclusiva)",
        ha="center",
        fontsize=8.5,
    )

    ax1.add_patch(
        plt.Rectangle(
            (5.8, 5.8), 3.0, 1.8, facecolor="#99c2ff", edgecolor="#003366", lw=1.5
        )
    )
    ax1.text(
        7.3,
        6.7,
        "L2: 2 MB (Privada)\n~16 ciclos\n(Não-Inclusiva)",
        ha="center",
        fontsize=8.5,
    )

    # L3 Compartilhada
    ax1.add_patch(
        plt.Rectangle(
            (0.8, 2.0), 8.4, 2.5, facecolor="#66a3ff", edgecolor="#002244", lw=2
        )
    )
    ax1.text(
        5.0,
        3.25,
        "L3 (LLC): 36 MB Compartilhada (Smart Cache / Ring Bus)\nLatência: ~45-55 ciclos | Política NINE / Inclusiva p/ snoop filter",
        ha="center",
        color="white",
        fontweight="bold",
        fontsize=9,
    )

    # Conexões
    for x in [2.7, 7.3]:
        ax1.annotate(
            "", xy=(x, 5.8), xytext=(x, 8.8), arrowprops=dict(arrowstyle="<->", lw=1.5)
        )
        ax1.annotate(
            "", xy=(x, 4.5), xytext=(x, 5.8), arrowprops=dict(arrowstyle="<->", lw=1.5)
        )

    # RAM
    ax1.add_patch(
        plt.Rectangle(
            (1.5, 0.2), 7.0, 1.0, facecolor="#cccccc", edgecolor="black", lw=1.5
        )
    )
    ax1.text(
        5.0,
        0.7,
        "Memória Principal (DDR5) ~180-220 ciclos",
        ha="center",
        fontsize=9,
        fontweight="bold",
    )
    ax1.annotate(
        "", xy=(5.0, 1.2), xytext=(5.0, 2.0), arrowprops=dict(arrowstyle="<->", lw=1.5)
    )

    # Painel 2: AMD Ryzen (Zen 4 / Zen 5 + 3D V-Cache)
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 12)
    ax2.axis("off")
    ax2.set_title(
        "Arquitetura AMD (Ryzen 9 / Zen 4 & 5)\nPolítica: Exclusiva / Victim Cache (L3 Monolítica CCX)",
        fontsize=11,
        fontweight="bold",
    )

    # Cores
    ax2.add_patch(
        plt.Rectangle(
            (0.8, 8.5),
            3.8,
            2.5,
            facecolor="#fde8e8",
            edgecolor="#d9534f",
            lw=2,
            linestyle="--",
        )
    )
    ax2.text(
        2.7, 10.3, "Núcleo Zen Core 0", ha="center", fontweight="bold", color="#d9534f"
    )
    ax2.add_patch(
        plt.Rectangle(
            (1.2, 8.8), 3.0, 1.0, facecolor="#f8b4b4", edgecolor="#721c24", lw=1.5
        )
    )
    ax2.text(
        2.7, 9.3, "L1 I/D: 64 KB (Privada)\n~4-5 ciclos", ha="center", fontsize=8.5
    )

    ax2.add_patch(
        plt.Rectangle(
            (5.4, 8.5),
            3.8,
            2.5,
            facecolor="#fde8e8",
            edgecolor="#d9534f",
            lw=2,
            linestyle="--",
        )
    )
    ax2.text(
        7.3, 10.3, "Núcleo Zen Core 1", ha="center", fontweight="bold", color="#d9534f"
    )
    ax2.add_patch(
        plt.Rectangle(
            (5.8, 8.8), 3.0, 1.0, facecolor="#f8b4b4", edgecolor="#721c24", lw=1.5
        )
    )
    ax2.text(
        7.3, 9.3, "L1 I/D: 64 KB (Privada)\n~4-5 ciclos", ha="center", fontsize=8.5
    )

    # L2 caches
    ax2.add_patch(
        plt.Rectangle(
            (1.2, 5.8), 3.0, 1.8, facecolor="#f08080", edgecolor="#491217", lw=1.5
        )
    )
    ax2.text(
        2.7,
        6.7,
        "L2: 1 MB (Privada)\n~14 ciclos\n(Exclusiva / Victim)",
        ha="center",
        fontsize=8.5,
    )

    ax2.add_patch(
        plt.Rectangle(
            (5.8, 5.8), 3.0, 1.8, facecolor="#f08080", edgecolor="#491217", lw=1.5
        )
    )
    ax2.text(
        7.3,
        6.7,
        "L2: 1 MB (Privada)\n~14 ciclos\n(Exclusiva / Victim)",
        ha="center",
        fontsize=8.5,
    )

    # L3 Compartilhada (CCX / 3D V-Cache)
    ax2.add_patch(
        plt.Rectangle(
            (0.8, 2.0), 8.4, 2.5, facecolor="#c9302c", edgecolor="#300000", lw=2
        )
    )
    ax2.text(
        5.0,
        3.25,
        "L3: 32 MB (+64 MB 3D V-Cache = 96 MB por CCD)\nLatência: ~40-48 ciclos | Victim Cache Exclusiva\n(Maximiza a capacidade agregada)",
        ha="center",
        color="white",
        fontweight="bold",
        fontsize=8.8,
    )

    # Conexões
    for x in [2.7, 7.3]:
        ax2.annotate(
            "", xy=(x, 5.8), xytext=(x, 8.8), arrowprops=dict(arrowstyle="<->", lw=1.5)
        )
        ax2.annotate(
            "", xy=(x, 4.5), xytext=(x, 5.8), arrowprops=dict(arrowstyle="<->", lw=1.5)
        )

    # RAM
    ax2.add_patch(
        plt.Rectangle(
            (1.5, 0.2), 7.0, 1.0, facecolor="#cccccc", edgecolor="black", lw=1.5
        )
    )
    ax2.text(
        5.0,
        0.7,
        "Memória Principal (DDR5 via IOD) ~190-240 ciclos",
        ha="center",
        fontsize=9,
        fontweight="bold",
    )
    ax2.annotate(
        "", xy=(5.0, 1.2), xytext=(5.0, 2.0), arrowprops=dict(arrowstyle="<->", lw=1.5)
    )

    plt.tight_layout()
    out_file = os.path.join(FIGURES_DIR, "fig6_intel_vs_amd_diagram.png")
    plt.savefig(out_file, dpi=300)
    plt.close()
    print(f"Salvo: {out_file}")


if __name__ == "__main__":
    plot_experiment_1()
    plot_experiment_2()
    plot_experiment_3()
    plot_intel_amd_diagram()
    print("Todos os gráficos foram gerados com sucesso!")
