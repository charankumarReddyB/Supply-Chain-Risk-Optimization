"""
ml/monte_carlo.py
Monte Carlo Simulation for Supply Chain Risk Analysis.
Runs 10,000 simulations to predict:
  - Delivery Delay Probability
  - Inventory Stockout Probability
  - Supplier Failure Probability
  - Transportation Delay Probability
Saves probability distribution graphs as PNG files and returns results.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from backend.models.database import execute_query
from backend.config import Config

logger = logging.getLogger(__name__)

NUM_SIMULATIONS = 10_000
GRAPHS_DIR = os.path.join(Config.BASE_DIR, "static", "monte_carlo_graphs")
RESULTS_PATH = os.path.join(Config.BASE_DIR, "ml", "monte_carlo_results.json")


def _ensure_dirs():
    os.makedirs(GRAPHS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)


def _save_graph_png(values: np.ndarray, title: str, xlabel: str, filename: str,
                    threshold: float = None, color: str = "#3182CE"):
    """
    Generates and saves a matplotlib histogram PNG for the simulation output.
    Falls back gracefully if matplotlib is not installed or display unavailable.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend (no display needed)
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist(values, bins=60, color=color, edgecolor="white", alpha=0.85)

        if threshold is not None:
            ax.axvline(x=threshold, color="#E53E3E", linestyle="--", linewidth=1.5,
                       label=f"Threshold = {threshold:.2f}")
            ax.legend(fontsize=9)

        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel("Frequency (out of 10,000 simulations)", fontsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", alpha=0.3)

        path = os.path.join(GRAPHS_DIR, filename)
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return path

    except Exception as e:
        logger.warning(f"Graph generation skipped ({filename}): {e}")
        return None


# ─── Simulation 1: Delivery Delay ────────────────────────────────────────────

def simulate_delivery_delay() -> dict:
    """
    Samples mean and std-dev of delivery delays from historical data.
    Models delay per order as Normal(mu, sigma). Outputs probability of delay > 0.
    """
    rows = execute_query(
        "SELECT AVG(Delivery_Delay) AS mu, STDDEV(Delivery_Delay) AS sigma FROM fact_order"
    )
    mu = float(rows[0]["mu"] or 1.5)
    sigma = float(rows[0]["sigma"] or 2.0)
    sigma = max(sigma, 0.1)

    np.random.seed(42)
    simulated_delays = np.random.normal(mu, sigma, NUM_SIMULATIONS)
    delay_prob = float(np.mean(simulated_delays > 0))
    avg_sim_delay = float(np.mean(simulated_delays))
    p95 = float(np.percentile(simulated_delays, 95))

    graph_path = _save_graph_png(
        simulated_delays,
        title="Monte Carlo: Delivery Delay Distribution (10,000 Simulations)",
        xlabel="Simulated Delivery Delay (Days)",
        filename="delivery_delay.png",
        threshold=0.0,
        color="#3182CE"
    )

    return {
        "simulation": "Delivery Delay",
        "num_simulations": NUM_SIMULATIONS,
        "historical_mean_delay_days": round(mu, 4),
        "historical_std_dev_days": round(sigma, 4),
        "delay_probability": round(delay_prob, 4),
        "delay_probability_percent": round(delay_prob * 100, 2),
        "average_simulated_delay_days": round(avg_sim_delay, 4),
        "p95_delay_days": round(p95, 4),
        "graph_url": f"/api/monte-carlo/graph/delivery_delay.png" if graph_path else None
    }


# ─── Simulation 2: Inventory Stockout ────────────────────────────────────────

def simulate_inventory_stockout() -> dict:
    """
    For each inventory item, samples daily demand from Poisson(avg_daily_demand).
    Calculates probability that demand over lead_time exceeds stock_level.
    """
    items = execute_query("""
        SELECT
            i.stock_level,
            i.lead_time_days,
            i.safety_stock,
            GREATEST(i.reorder_point / 30.0, 1) AS avg_daily_demand
        FROM inventory i
    """)

    if not items:
        return {"error": "No inventory data available", "simulation": "Inventory Stockout"}

    np.random.seed(42)
    stockout_flags = []
    for item in items:
        stock = float(item["stock_level"])
        lead = max(int(item["lead_time_days"]), 1)
        daily_demand = float(item["avg_daily_demand"])

        # Simulate total demand over lead time
        total_demand_sim = np.random.poisson(daily_demand * lead, NUM_SIMULATIONS)
        stockout_flags.extend((total_demand_sim > stock).tolist())

    stockout_array = np.array(stockout_flags, dtype=float)
    stockout_prob = float(np.mean(stockout_array))

    # For graph: simulate total demand for a representative average item
    avg_daily = float(np.mean([item["avg_daily_demand"] for item in items]))
    avg_lead = float(np.mean([item["lead_time_days"] for item in items]))
    avg_stock = float(np.mean([item["stock_level"] for item in items]))
    sim_demand = np.random.poisson(avg_daily * avg_lead, NUM_SIMULATIONS)

    graph_path = _save_graph_png(
        sim_demand,
        title="Monte Carlo: Demand During Lead Time (10,000 Simulations)",
        xlabel="Units Demanded During Lead Time",
        filename="inventory_stockout.png",
        threshold=avg_stock,
        color="#38A169"
    )

    return {
        "simulation": "Inventory Stockout",
        "num_simulations": NUM_SIMULATIONS,
        "stockout_probability": round(stockout_prob, 4),
        "stockout_probability_percent": round(stockout_prob * 100, 2),
        "average_daily_demand_used": round(avg_daily, 4),
        "average_lead_time_days": round(avg_lead, 2),
        "average_stock_level": round(avg_stock, 2),
        "graph_url": f"/api/monte-carlo/graph/inventory_stockout.png" if graph_path else None
    }


# ─── Simulation 3: Supplier Failure ──────────────────────────────────────────

def simulate_supplier_failure() -> dict:
    """
    Models each supplier's failure (inability to deliver on time) as a Bernoulli trial
    where probability = historical delay rate. Simulates supplier failure count per run.
    """
    suppliers = execute_query("""
        SELECT
            s.Supplier_ID,
            s.Supplier_Name,
            COUNT(f.Fact_ID)                                    AS total_orders,
            SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS delayed_orders
        FROM dim_supplier s
            JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
        GROUP BY s.Supplier_ID, s.Supplier_Name
    """)

    if not suppliers:
        return {"error": "No supplier data available", "simulation": "Supplier Failure"}

    np.random.seed(42)
    failure_probs = []
    supplier_results = []

    for sup in suppliers:
        total = max(int(sup["total_orders"]), 1)
        delayed = int(sup["delayed_orders"] or 0)
        p_fail = delayed / total

        # Simulate: does this supplier fail in a given period?
        sim_outcomes = np.random.binomial(1, p_fail, NUM_SIMULATIONS)
        individual_prob = float(np.mean(sim_outcomes))
        failure_probs.append(individual_prob)

        supplier_results.append({
            "supplier_name": sup["Supplier_Name"],
            "historical_delay_rate": round(p_fail, 4),
            "simulated_failure_probability": round(individual_prob, 4),
            "risk_category": (
                "High" if individual_prob >= 0.5 else
                "Medium" if individual_prob >= 0.25 else
                "Low"
            )
        })

    # Simulate number of suppliers failing per simulation run
    all_probs = np.array(failure_probs)
    sim_failure_counts = np.sum(
        np.random.binomial(1, all_probs[:, np.newaxis], (len(all_probs), NUM_SIMULATIONS)),
        axis=0
    )
    overall_failure_prob = float(np.mean(sim_failure_counts >= 1))

    graph_path = _save_graph_png(
        sim_failure_counts,
        title="Monte Carlo: Supplier Failure Count per Simulation (10,000 Runs)",
        xlabel="Number of Suppliers Failing per Simulation",
        filename="supplier_failure.png",
        threshold=1.0,
        color="#D69E2E"
    )

    return {
        "simulation": "Supplier Failure",
        "num_simulations": NUM_SIMULATIONS,
        "overall_at_least_one_supplier_failure_probability": round(overall_failure_prob, 4),
        "overall_probability_percent": round(overall_failure_prob * 100, 2),
        "average_suppliers_failing_per_run": round(float(np.mean(sim_failure_counts)), 4),
        "supplier_level_results": supplier_results,
        "graph_url": f"/api/monte-carlo/graph/supplier_failure.png" if graph_path else None
    }


# ─── Simulation 4: Transportation Delay ──────────────────────────────────────

def simulate_transportation_delay() -> dict:
    """
    Models transportation delay per shipping mode using historical rates.
    Simulates 10,000 shipments per mode via Binomial distribution.
    """
    modes = execute_query("""
        SELECT
            sh.Shipping_Mode,
            COUNT(f.Fact_ID)                                    AS total,
            SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS "delayed",
            ROUND(AVG(f.Delivery_Delay), 2)                     AS avg_delay
        FROM fact_order f
            JOIN dim_shipping sh ON f.Shipping_ID = sh.Shipping_ID
        GROUP BY sh.Shipping_Mode
    """)

    if not modes:
        return {"error": "No shipping data available", "simulation": "Transportation Delay"}

    np.random.seed(42)
    mode_results = []
    all_delay_samples = []

    for mode in modes:
        total = max(int(mode["total"]), 1)
        delayed = int(mode["delayed"] or 0)
        p_delay = delayed / total
        avg_delay = float(mode["avg_delay"] or 0)

        # Simulate delay count out of 10,000 shipments
        sim_delays = np.random.binomial(NUM_SIMULATIONS, p_delay, 200)
        sim_delay_probs = sim_delays / NUM_SIMULATIONS
        all_delay_samples.extend(sim_delay_probs.tolist())

        mode_results.append({
            "shipping_mode": mode["Shipping_Mode"],
            "historical_delay_rate": round(p_delay, 4),
            "simulated_delay_probability": round(float(np.mean(sim_delay_probs)), 4),
            "simulated_probability_percent": round(float(np.mean(sim_delay_probs)) * 100, 2),
            "historical_avg_delay_days": round(avg_delay, 2),
            "recommendation": (
                "High Risk – Avoid for time-sensitive orders" if p_delay > 0.6 else
                "Medium Risk – Use with buffer time" if p_delay > 0.4 else
                "Low Risk – Recommended"
            )
        })

    graph_path = _save_graph_png(
        np.array(all_delay_samples),
        title="Monte Carlo: Transportation Delay Probability by Shipping Mode",
        xlabel="Simulated Delay Probability",
        filename="transportation_delay.png",
        threshold=0.5,
        color="#9B2C2C"
    )

    return {
        "simulation": "Transportation Delay",
        "num_simulations": NUM_SIMULATIONS,
        "shipping_mode_results": mode_results,
        "graph_url": f"/api/monte-carlo/graph/transportation_delay.png" if graph_path else None
    }


# ─── Master Function ──────────────────────────────────────────────────────────

def run_all_simulations() -> dict:
    """
    Runs all four Monte Carlo simulations and returns consolidated results.
    Saves individual graphs to static/monte_carlo_graphs/.
    """
    _ensure_dirs()
    logger.info("Starting Monte Carlo simulations...")

    results = {
        "timestamp": datetime.now().isoformat(),
        "total_simulations_per_scenario": NUM_SIMULATIONS,
        "delivery_delay": simulate_delivery_delay(),
        "inventory_stockout": simulate_inventory_stockout(),
        "supplier_failure": simulate_supplier_failure(),
        "transportation_delay": simulate_transportation_delay()
    }

    # Persist results to JSON
    try:
        with open(RESULTS_PATH, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Monte Carlo results saved to {RESULTS_PATH}")
    except Exception as e:
        logger.error(f"Failed to save Monte Carlo results: {e}")

    return results


def load_cached_results() -> dict:
    """Returns the last saved Monte Carlo results, or None if not available."""
    if os.path.exists(RESULTS_PATH):
        try:
            with open(RESULTS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None
