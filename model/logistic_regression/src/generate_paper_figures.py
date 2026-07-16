from __future__ import annotations

import os
import sys
import shutil
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, precision_recall_curve, brier_score_loss, roc_auc_score, average_precision_score
from sklearn.calibration import calibration_curve

# Suppress warnings
warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "model" / "logistic_regression" / "outputs"
IMAGE_DIR = PROJECT_ROOT / "image"

# Define Unified Model Display Names mapping
MODEL_DISPLAY_NAMES = {
    "row_channel": "Row-Level Channel Presence",
    "user_any_channel": "Channel Presence Only",
    "journey_length_only": "Journey Length Only",
    "channel_plus_length": "Channel Presence + Length",
    "enhanced_journey_logistic": "Enhanced Journey Logistic",
    "enhanced_journey_logistic_balanced": "Enhanced Journey Logistic (Balanced)",
    "random_forest": "Random Forest Benchmark",
    "extra_trees": "Extra Trees Benchmark",
    "gradient_boosting": "HistGradientBoosting Benchmark"
}

# Unified Feature Set Names mapping for ablation
ABLATION_SET_DISPLAY_NAMES = {
    "channel_presence_only": "Channel Presence Only",
    "journey_length_only": "Journey Length Only",
    "channel_presence_plus_length": "Channel Presence + Length",
    "channel_counts_only": "Channel Counts Only",
    "channel_proportions_only": "Channel Proportions Only",
    "channel_counts_plus_proportions": "Channel Counts + Proportions",
    "journey_structure_only": "Journey Structure Only",
    "journey_position_only": "Journey Position Only",
    "sequence_summary_only": "Sequence Summary Only",
    "full_enhanced_features": "Full Enhanced Features"
}

def configure_publication_style():
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 13,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight"
    })

def validate_metrics_consistency():
    print("Validating metrics consistency across CSV files...")
    cv_metrics = pd.read_csv(OUTPUT_DIR / "repeated_cv_metrics.csv")
    ablation = pd.read_csv(OUTPUT_DIR / "feature_ablation_results.csv")
    comparisons = pd.read_csv(OUTPUT_DIR / "statistical_model_comparisons.csv")
    
    # 1. Check journey_length_only AUC matches
    auc_cv_len = cv_metrics[cv_metrics["model"] == "journey_length_only"]["mean_roc_auc"].values[0]
    auc_abl_len = ablation[ablation["feature_set"] == "journey_length_only"]["mean_cv_roc_auc"].values[0]
    assert abs(auc_cv_len - auc_abl_len) < 1e-5, f"Mismatch in journey_length_only AUC: CV={auc_cv_len}, Ablation={auc_abl_len}"
    
    # 2. Check channel_plus_length AUC matches
    auc_cv_plus = cv_metrics[cv_metrics["model"] == "channel_plus_length"]["mean_roc_auc"].values[0]
    auc_abl_plus = ablation[ablation["feature_set"] == "channel_presence_plus_length"]["mean_cv_roc_auc"].values[0]
    assert abs(auc_cv_plus - auc_abl_plus) < 1e-5, f"Mismatch in channel_plus_length AUC: CV={auc_cv_plus}, Ablation={auc_abl_plus}"
    
    # 3. Check enhanced model AUC matches
    auc_cv_enh = cv_metrics[cv_metrics["model"] == "enhanced_journey_logistic"]["mean_roc_auc"].values[0]
    auc_abl_enh = ablation[ablation["feature_set"] == "full_enhanced_features"]["mean_cv_roc_auc"].values[0]
    assert abs(auc_cv_enh - auc_abl_enh) < 1e-5, f"Mismatch in enhanced model AUC: CV={auc_cv_enh}, Ablation={auc_abl_enh}"
    
    # 4. Check statistical comparisons difference matches ablation incremental AUC
    diff_stat_plus = comparisons[comparisons["comparison"] == "channel_plus_length_vs_journey_length_only"]["mean_difference"].values[0]
    diff_calc_plus = ablation[ablation["feature_set"] == "channel_presence_plus_length"]["incremental_auc_over_length_only"].values[0]
    assert abs(diff_stat_plus - diff_calc_plus) < 1e-5, f"Mismatch in statistical comparison difference for plus: stat={diff_stat_plus}, calc={diff_calc_plus}"
    
    # 5. Check CI consistency for incremental AUC in ablation results
    ci_lower_inc_plus = ablation[ablation["feature_set"] == "channel_presence_plus_length"]["ci_lower_incremental_auc"].values[0]
    ci_lower_stat_plus = comparisons[comparisons["comparison"] == "channel_plus_length_vs_journey_length_only"]["ci_lower_95"].values[0]
    assert abs(ci_lower_inc_plus - ci_lower_stat_plus) < 1e-5, f"Mismatch in incremental AUC CI lower: ablation={ci_lower_inc_plus}, stat={ci_lower_stat_plus}"
    
    print("All consistency checks passed successfully.")

# --- 01. Journey Length Distribution ---
def plot_journey_length_distribution():
    users = pd.read_csv(OUTPUT_DIR / "rq2_logistic_user_model_matrix.csv")
    
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.kdeplot(
        data=users, x="n_touchpoints", hue="converted_any_yes", 
        fill=True, alpha=0.3, common_norm=False, palette={0: "#d95f02", 1: "#1f77b4"}, ax=ax
    )
    ax.set_xlabel("Journey Length (Number of Touchpoints)")
    ax.set_ylabel("Density")
    ax.set_title("Journey Length Distribution by Conversion Status")
    ax.legend(["Converted (Yes)", "Not Converted (No)"], loc="upper right")
    
    plt.savefig(IMAGE_DIR / "01_journey_length_distribution.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

# --- 02. Holdout ROC Curves ---
def plot_holdout_roc_curves():
    preds = pd.read_csv(OUTPUT_DIR / "holdout_predictions.csv")
    key_models = ["user_any_channel", "journey_length_only", "channel_plus_length", "enhanced_journey_logistic", "gradient_boosting"]
    
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", label="Random Guess (AUC = 0.50)")
    
    colors = {"user_any_channel": "#a6cee3", "journey_length_only": "#1f78b4", "channel_plus_length": "#b2df8a", "enhanced_journey_logistic": "#33a02c", "gradient_boosting": "#fb9a99"}
    
    for m in key_models:
        sub = preds[preds["model"] == m]
        fpr, tpr, _ = roc_curve(sub["y_true"], sub["y_probability"])
        auc = roc_auc_score(sub["y_true"], sub["y_probability"])
        disp_name = MODEL_DISPLAY_NAMES.get(m, m)
        ax.plot(fpr, tpr, label=f"{disp_name} (AUC = {auc:.4f})", color=colors.get(m, "#33a02c"), linewidth=1.5)
        
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("Holdout Test Set ROC Curves")
    ax.legend(loc="lower right")
    
    plt.savefig(IMAGE_DIR / "02_holdout_roc_curves.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

# --- 03. Holdout PR Curves ---
def plot_holdout_pr_curves():
    preds = pd.read_csv(OUTPUT_DIR / "holdout_predictions.csv")
    key_models = ["user_any_channel", "journey_length_only", "channel_plus_length", "enhanced_journey_logistic", "gradient_boosting"]
    
    # Calculate baseline from holdout y_true
    baseline = preds[preds["model"] == "journey_length_only"]["y_true"].mean()
    
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.axhline(baseline, color="gray", linestyle="--", label=f"Positive Prevalence Baseline (Prevalence = {baseline:.4f})")
    
    colors = {"user_any_channel": "#a6cee3", "journey_length_only": "#1f78b4", "channel_plus_length": "#b2df8a", "enhanced_journey_logistic": "#33a02c", "gradient_boosting": "#fb9a99"}
    
    for m in key_models:
        sub = preds[preds["model"] == m]
        prec, rec, _ = precision_recall_curve(sub["y_true"], sub["y_probability"])
        pr_auc = average_precision_score(sub["y_true"], sub["y_probability"])
        disp_name = MODEL_DISPLAY_NAMES.get(m, m)
        ax.plot(rec, prec, label=f"{disp_name} (PR-AUC = {pr_auc:.4f})", color=colors.get(m, "#33a02c"), linewidth=1.5)
        
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Holdout Test Set Precision-Recall Curves")
    ax.legend(loc="lower left")
    
    plt.savefig(IMAGE_DIR / "03_holdout_pr_curves.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

# --- 04. CV Performance Forest Plot ---
def plot_cv_performance_forest():
    metrics = pd.read_csv(OUTPUT_DIR / "repeated_cv_metrics.csv")
    
    # Filter out row_channel
    metrics = metrics[metrics["model"] != "row_channel"]
    
    # Rearrange models order for plotting
    order = [
        "user_any_channel", "journey_length_only", "channel_plus_length",
        "enhanced_journey_logistic", "enhanced_journey_logistic_balanced",
        "random_forest", "extra_trees", "gradient_boosting"
    ]
    metrics = metrics.set_index("model").loc[order].reset_index()
    
    fig, ax = plt.subplots(figsize=(7, 4.5))
    y_pos = np.arange(len(metrics))
    
    # Calculate error bars
    err_low = metrics["mean_roc_auc"] - metrics["ci_lower_95"]
    err_high = metrics["ci_upper_95"] - metrics["mean_roc_auc"]
    
    ax.errorbar(
        metrics["mean_roc_auc"], y_pos, xerr=[err_low, err_high], 
        fmt='o', color='#1f77b4', elinewidth=1.5, capsize=3, label="Mean CV ROC-AUC"
    )
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels([MODEL_DISPLAY_NAMES.get(m, m) for m in metrics["model"]])
    ax.set_xlabel("Repeated CV ROC-AUC")
    ax.set_title("Model Comparison: 5-Fold Repeated CV (50 Folds)")
    
    # Draw vertical line representing the journey length baseline
    base_auc = metrics[metrics["model"] == "journey_length_only"]["mean_roc_auc"].values[0]
    ax.axvline(base_auc, color='gray', linestyle='--', alpha=0.7, label="Journey Length Baseline")
    ax.legend(loc="lower left")
    
    plt.savefig(IMAGE_DIR / "04_cv_performance_forest.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

# --- 05. Feature Ablation Study ---
def plot_feature_ablation():
    ablation = pd.read_csv(OUTPUT_DIR / "feature_ablation_results.csv")
    
    # Filter to the 6 primary groups
    keep_sets = [
        "channel_presence_only", "journey_length_only", "channel_presence_plus_length",
        "channel_counts_only", "journey_structure_only", "full_enhanced_features"
    ]
    ablation = ablation.set_index("feature_set").loc[keep_sets].reset_index()
    ablation = ablation.sort_values(by="mean_cv_roc_auc")
    
    fig, ax = plt.subplots(figsize=(7.5, 4))
    y_pos = np.arange(len(ablation))
    
    err_low = ablation["mean_cv_roc_auc"] - ablation["ci_lower_95"]
    err_high = ablation["ci_upper_95"] - ablation["mean_cv_roc_auc"]
    
    ax.errorbar(
        ablation["mean_cv_roc_auc"], y_pos, xerr=[err_low, err_high], 
        fmt='o', color='#2ca02c', elinewidth=1.5, capsize=3
    )
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels([ABLATION_SET_DISPLAY_NAMES.get(s, s) for s in ablation["feature_set"]])
    ax.set_xlabel("Mean CV ROC-AUC")
    ax.set_title("Feature Ablation Study (50 Folds)")
    
    # Draw reference line at journey length only
    len_auc = ablation[ablation["feature_set"] == "journey_length_only"]["mean_cv_roc_auc"].values[0]
    ax.axvline(len_auc, color='red', linestyle='--', alpha=0.6, label="Journey Length Only")
    ax.legend(loc="lower right")
    
    plt.savefig(IMAGE_DIR / "05_feature_ablation.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

# --- 06. Incremental AUC over Journey Length ---
def plot_incremental_auc():
    ablation = pd.read_csv(OUTPUT_DIR / "feature_ablation_results.csv")
    comparisons = pd.read_csv(OUTPUT_DIR / "statistical_model_comparisons.csv")
    
    # Keep the groups except journey_length_only itself
    keep_sets = [
        "channel_presence_only", "channel_presence_plus_length",
        "channel_counts_only", "journey_structure_only", "full_enhanced_features"
    ]
    ablation = ablation.set_index("feature_set").loc[keep_sets].reset_index()
    ablation = ablation.sort_values(by="incremental_auc_over_length_only")
    
    fig, ax = plt.subplots(figsize=(8, 4))
    y_pos = np.arange(len(ablation))
    
    # Plotted error bars are computed from the paired user-level bootstrap
    err_low = ablation["incremental_auc_over_length_only"] - ablation["ci_lower_incremental_auc"]
    err_high = ablation["ci_upper_incremental_auc"] - ablation["incremental_auc_over_length_only"]
    
    ax.errorbar(
        ablation["incremental_auc_over_length_only"], y_pos, xerr=[err_low, err_high], 
        fmt='o', color='#C94C4C', elinewidth=1.5, capsize=3
    )
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels([ABLATION_SET_DISPLAY_NAMES.get(s, s) for s in ablation["feature_set"]])
    ax.set_xlabel("Incremental ROC-AUC (Model - Journey Length Only)")
    ax.set_title("Incremental Predictive Value over Journey Length Only")
    ax.axvline(0.0, color='gray', linestyle='--')
    
    # Annotate that the improvement is statistically detectable but practically negligible
    ax.text(
        0.005, len(ablation) - 1.2, 
        "Statistically detectable but\npractically negligible improvement\n(Max delta ≈ 0.0037 ROC-AUC)", 
        fontsize=9, color="#555555", style="italic", bbox=dict(facecolor='white', alpha=0.8, edgecolor='none')
    )
    
    # Double check plotted CI values match comparisons CSV for channel_presence_plus_length
    ci_stat_low = comparisons[comparisons["comparison"] == "channel_plus_length_vs_journey_length_only"]["ci_lower_95"].values[0]
    ci_stat_high = comparisons[comparisons["comparison"] == "channel_plus_length_vs_journey_length_only"]["ci_upper_95"].values[0]
    ci_plot_low = ablation[ablation["feature_set"] == "channel_presence_plus_length"]["ci_lower_incremental_auc"].values[0]
    ci_plot_high = ablation[ablation["feature_set"] == "channel_presence_plus_length"]["ci_upper_incremental_auc"].values[0]
    
    assert abs(ci_stat_low - ci_plot_low) < 1e-5, f"CI Lower Mismatch: stat={ci_stat_low}, plot={ci_plot_low}"
    assert abs(ci_stat_high - ci_plot_high) < 1e-5, f"CI Upper Mismatch: stat={ci_stat_high}, plot={ci_plot_high}"
    
    plt.savefig(IMAGE_DIR / "06_incremental_auc.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

# --- 07. Calibration Curves ---
def plot_calibration_curves():
    preds = pd.read_csv(OUTPUT_DIR / "holdout_predictions.csv")
    key_models = ["journey_length_only", "channel_plus_length", "enhanced_journey_logistic"]
    
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", label="Perfect Calibration")
    
    colors = {"journey_length_only": "#1f78b4", "channel_plus_length": "#b2df8a", "enhanced_journey_logistic": "#33a02c"}
    
    for m in key_models:
        sub = preds[preds["model"] == m]
        true_prob, pred_prob = calibration_curve(sub["y_true"], sub["y_probability"], n_bins=10, strategy="uniform")
        brier = brier_score_loss(sub["y_true"], sub["y_probability"])
        disp_name = MODEL_DISPLAY_NAMES.get(m, m)
        ax.plot(pred_prob, true_prob, marker='o', label=f"{disp_name} (Brier = {brier:.4f})", color=colors.get(m, "#33a02c"), linewidth=1.5)
        
    ax.set_xlabel("Mean Predicted Probability")
    ax.set_ylabel("Fraction of Positives")
    ax.set_title("Calibration Curves (Reliability Diagrams)")
    ax.legend(loc="upper left")
    
    plt.savefig(IMAGE_DIR / "07_calibration_curves.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

# --- 08. Logistic Odds Ratios ---
def plot_logistic_odds_ratios():
    odds_ratios = pd.read_csv(OUTPUT_DIR / "enhanced_logistic_odds_ratios.csv")
    
    # Exclude intercept
    odds_ratios = odds_ratios[odds_ratios["term"] != "intercept"]
    
    # Sort and take top 12 most significant features by absolute z score or effect size
    # Let's sort by odds_ratio distance from 1.0 (effect size)
    odds_ratios["effect_size"] = np.abs(odds_ratios["coef"])
    odds_ratios = odds_ratios.sort_values(by="effect_size", ascending=False).head(12)
    odds_ratios = odds_ratios.sort_values(by="odds_ratio")
    
    fig, ax = plt.subplots(figsize=(8, 4.5))
    y_pos = np.arange(len(odds_ratios))
    
    # Calculate Odds Ratio CIs
    err_low = odds_ratios["odds_ratio"] - odds_ratios["or_ci_lower"]
    err_high = odds_ratios["or_ci_upper"] - odds_ratios["odds_ratio"]
    
    ax.errorbar(
        odds_ratios["odds_ratio"], y_pos, xerr=[err_low, err_high], 
        fmt='o', color='#7f7f7f', elinewidth=1.5, capsize=3
    )
    
    # Style features names nicely
    clean_terms = []
    for t in odds_ratios["term"]:
        # Strip OHE suffixes
        clean_t = t.replace("num__", "").replace("cat__", "")
        clean_terms.append(clean_t)
        
    ax.set_yticks(y_pos)
    ax.set_yticklabels(clean_terms)
    ax.set_xlabel("Odds Ratio (95% CI)")
    ax.set_title("Top 12 Features by Logistic Odds Ratio (Log Scale)")
    ax.axvline(1.0, color='red', linestyle='--')
    ax.set_xscale("log")
    
    plt.savefig(IMAGE_DIR / "08_logistic_odds_ratios.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close()

def clean_obsolete_images():
    print("Cleaning obsolete outputs and figures...")
    
    # 1. Clean outputs/figures folder in case it exists
    fig_dir = OUTPUT_DIR / "figures"
    if fig_dir.exists():
        shutil.rmtree(fig_dir)
        print("Deleted legacy folder: model/logistic_regression/outputs/figures")
        
    # 2. Clean paper/images folder generated in previous stages
    paper_img_dir = PROJECT_ROOT / "paper" / "images"
    if paper_img_dir.exists():
        # Only remove files that we generated
        for f in paper_img_dir.glob("figure_*.png"):
            f.unlink()
        print("Deleted legacy figures in paper/images")
        
    # 3. Clean root outputs folder
    legacy_root_outputs = [
        "figure_manifest.csv", "figure_quality_check.csv", "paper_figure_recommendations.md",
        "enhanced_logistic_coefficients.csv", "nonlinear_permutation_importance.csv",
        "model_auc_comparison.csv", "model_pr_auc_comparison.csv", "calibration_metrics.csv",
        "threshold_analysis.csv", "auc_difference_bootstrap.csv", "enhanced_feature_dictionary.csv",
        "feature_distribution_summary.csv", "split_summary.csv", "logistic_regression_metrics.csv",
        "hyperparameter_tuning_results.csv", "best_hyperparameters.csv", "nonlinear_benchmark_metrics.csv"
    ]
    for filename in legacy_root_outputs:
        p = OUTPUT_DIR / filename
        if p.exists():
            p.unlink()
            print(f"Deleted obsolete CSV file: {p.name}")
            
    # Also clean any tuning PNGs in outputs
    for f in OUTPUT_DIR.glob("*.png"):
        f.unlink()
        print(f"Deleted legacy PNG: {f.name}")

def main():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    configure_publication_style()
    validate_metrics_consistency()
    
    print("Generating Figure 1: 01_journey_length_distribution.png...")
    plot_journey_length_distribution()
    
    print("Generating Figure 2: 02_holdout_roc_curves.png...")
    plot_holdout_roc_curves()
    
    print("Generating Figure 3: 03_holdout_pr_curves.png...")
    plot_holdout_pr_curves()
    
    print("Generating Figure 4: 04_cv_performance_forest.png...")
    plot_cv_performance_forest()
    
    print("Generating Figure 5: 05_feature_ablation.png...")
    plot_feature_ablation()
    
    print("Generating Figure 6: 06_incremental_auc.png...")
    plot_incremental_auc()
    
    print("Generating Figure 7: 07_calibration_curves.png...")
    plot_calibration_curves()
    
    print("Generating Figure 8: 08_logistic_odds_ratios.png...")
    plot_logistic_odds_ratios()
    
    clean_obsolete_images()
    print("Figure generation complete. All 8 figures successfully written in root 'image/' directory.")

if __name__ == "__main__":
    main()
