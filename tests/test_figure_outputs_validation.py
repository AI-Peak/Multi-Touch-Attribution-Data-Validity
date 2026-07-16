import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = PROJECT_ROOT / "image"
PAPER_DIR = PROJECT_ROOT / "paper"
LOGIT_OUT = PROJECT_ROOT / "model" / "logistic_regression" / "outputs"

def test_figure_outputs():
    # Verify exactly 9 PNG files exist in root image/ directory
    assert IMAGE_DIR.exists(), f"Image directory does not exist: {IMAGE_DIR}"
    
    png_files = list(IMAGE_DIR.glob("*.png"))
    png_names = {f.name for f in png_files}
    
    expected_pngs = {
        "01_journey_length_distribution.png",
        "02_holdout_roc_curves.png",
        "03_holdout_pr_curves.png",
        "04_cv_performance_forest.png",
        "05_feature_ablation.png",
        "06_incremental_auc.png",
        "07_calibration_curves.png",
        "08_logistic_odds_ratios.png",
        "09_markov_removal_effects.png"
    }
    
    assert png_names == expected_pngs, f"Figure mismatch in {IMAGE_DIR}. Found: {png_names}"
    
    # Verify no figure folders or pngs exist in outputs
    stale_fig_dir = LOGIT_OUT / "figures"
    assert not stale_fig_dir.exists(), "stale outputs/figures folder should not exist!"
    
    logit_pngs = list(LOGIT_OUT.glob("*.png"))
    assert len(logit_pngs) == 0, f"Obsolete PNG files found in logistic regression outputs: {logit_pngs}"
    
    # Verify no paper subdirectories like images/ or figures/ exist or were modified
    paper_images = PAPER_DIR / "images"
    assert not paper_images.exists() or len(list(paper_images.glob("figure_*.png"))) == 0, "paper/images folder should not contain generated figure_*.png files!"
