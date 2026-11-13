"""Deterministic CPU-only ART smoke test; uses a generated two-feature dataset."""

from __future__ import annotations

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression

import art
from art.attacks.evasion import FastGradientMethod, ProjectedGradientDescent
from art.estimators.classification.scikitlearn import ScikitlearnClassifier, SklearnClassifier


EPS = 0.15
CLIP_MIN = 0.0
CLIP_MAX = 1.0


def make_split(seed: int, count: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.uniform(0.05, 0.95, size=(count, 2)).astype(np.float32)
    y = (x[:, 0] + x[:, 1] >= 1.0).astype(np.int64)
    return x, y


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_adversarial(
    name: str,
    x_clean: np.ndarray,
    x_adv: np.ndarray,
    estimator: ScikitlearnClassifier,
    eps: float,
) -> tuple[np.ndarray, float]:
    require(x_adv.shape == x_clean.shape, f"{name}: output shape changed")
    require(np.isfinite(x_clean).all(), f"{name}: clean inputs are not finite")
    require(
        np.all(x_clean >= CLIP_MIN - 1e-6) and np.all(x_clean <= CLIP_MAX + 1e-6),
        f"{name}: clean inputs exceed declared clip bounds",
    )
    require(np.isfinite(x_adv).all(), f"{name}: adversarial values are not finite")
    require(
        np.all(x_adv >= CLIP_MIN - 1e-6) and np.all(x_adv <= CLIP_MAX + 1e-6),
        f"{name}: output exceeds declared clip bounds",
    )
    max_linf = float(np.max(np.abs(x_adv - x_clean)))
    require(max_linf <= eps + 1e-6, f"{name}: L-infinity budget exceeded ({max_linf} > {eps})")
    scores = estimator.predict(x_adv)
    require(scores.shape == (len(x_adv), 2), f"{name}: unexpected prediction shape {scores.shape}")
    require(np.isfinite(scores).all(), f"{name}: predictions are not finite")
    return np.argmax(scores, axis=1), max_linf


def main() -> None:
    if art.__version__ != "1.20.1":
        raise RuntimeError(f"Expected ART 1.20.1, found {art.__version__}")

    x_train, y_train = make_split(seed=1201, count=1200)
    x_test, y_test = make_split(seed=1202, count=500)
    model = LogisticRegression(C=100.0, max_iter=1000, random_state=1201)
    estimator = SklearnClassifier(
        model=model,
        clip_values=(CLIP_MIN, CLIP_MAX),
        preprocessing=(0.0, 1.0),
    )
    y_train_one_hot = np.eye(2, dtype=np.float32)[y_train]
    require(isinstance(estimator, ScikitlearnClassifier), "SklearnClassifier factory returned an unexpected type")
    estimator.fit(x_train, y_train_one_hot)

    clean_scores = estimator.predict(x_test)
    require(clean_scores.shape == (len(x_test), 2), "unexpected clean prediction shape")
    require(np.isfinite(clean_scores).all(), "clean predictions are not finite")
    clean_predictions = np.argmax(clean_scores, axis=1)
    clean_correct = clean_predictions == y_test
    clean_count = int(clean_correct.sum())
    require(clean_count > 0, "no clean-correct test samples; conditional denominator is empty")

    # Restrict all attack metrics and generations to clean-correct hold-out examples.
    x_eval = x_test[clean_correct].copy()
    y_eval = y_test[clean_correct]
    y_eval_one_hot = np.eye(2, dtype=np.float32)[y_eval]
    require(np.all(np.argmax(estimator.predict(x_eval), axis=1) == y_eval), "clean-correct filter is inconsistent")

    fgm = FastGradientMethod(
        estimator=estimator,
        norm=np.inf,
        eps=EPS,
        eps_step=EPS,
        targeted=False,
        batch_size=64,
    )
    x_fgm = fgm.generate(x=x_eval, y=y_eval_one_hot)
    fgm_predictions, fgm_linf = check_adversarial("FGM untargeted", x_eval, x_fgm, estimator, EPS)
    fgm_success = int(np.count_nonzero(fgm_predictions != y_eval))
    require(fgm_success > 0, "FGM produced no untargeted successes on the synthetic fixture")

    pgd = ProjectedGradientDescent(
        estimator=estimator,
        norm=np.inf,
        eps=EPS,
        eps_step=0.03,
        max_iter=10,
        num_random_init=0,
        targeted=False,
        batch_size=64,
        verbose=False,
    )
    x_pgd = pgd.generate(x=x_eval, y=y_eval_one_hot)
    pgd_predictions, pgd_linf = check_adversarial("PGD untargeted", x_eval, x_pgd, estimator, EPS)
    pgd_success = int(np.count_nonzero(pgd_predictions != y_eval))
    require(pgd_success > 0, "PGD produced no untargeted successes on the synthetic fixture")

    # Deliberately assign some true-class targets to exercise their exclusion.
    y_target = 1 - y_eval
    already_target = np.arange(len(y_eval)) % 4 == 0
    y_target[already_target] = y_eval[already_target]
    targeted_eligible = y_target != y_eval
    eligible_count = int(targeted_eligible.sum())
    expected_count = len(y_eval) - int(already_target.sum())
    require(0 < eligible_count < len(y_eval), "targeted fixture must include eligible and excluded samples")
    require(eligible_count == expected_count, "targeted denominator did not exclude true-class targets")
    x_target_eval = x_eval[targeted_eligible]
    y_target_eval = y_target[targeted_eligible]
    y_target_one_hot = np.eye(2, dtype=np.float32)[y_target_eval]
    targeted_fgm = FastGradientMethod(
        estimator=estimator,
        norm=np.inf,
        eps=EPS,
        eps_step=EPS,
        targeted=True,
        batch_size=64,
    )
    x_target_adv = targeted_fgm.generate(x=x_target_eval, y=y_target_one_hot)
    targeted_predictions, target_linf = check_adversarial(
        "FGM targeted", x_target_eval, x_target_adv, estimator, EPS
    )
    targeted_success = int(np.count_nonzero(targeted_predictions == y_target_eval))
    require(targeted_success > 0, "FGM produced no targeted successes on the synthetic fixture")

    print(f"Python runtime: {__import__('sys').version.split()[0]}")
    print(f"ART={art.__version__} NumPy={np.__version__} scikit-learn={sklearn.__version__}")
    print(f"estimator wrapper={type(estimator).__name__}")
    print(f"synthetic test samples={len(x_test)} clean-correct denominator={clean_count}")
    print(f"FGM untargeted success={fgm_success}/{clean_count} max_Linf={fgm_linf:.6f} eps={EPS}")
    print(f"PGD untargeted success={pgd_success}/{clean_count} max_Linf={pgd_linf:.6f} eps={EPS} max_iter=10")
    print(f"FGM targeted success={targeted_success}/{eligible_count} max_Linf={target_linf:.6f} eps={EPS}")
    print("PASS: API, finite values, clip bounds, L-infinity budgets, and metric denominators checked")


if __name__ == "__main__":
    main()
