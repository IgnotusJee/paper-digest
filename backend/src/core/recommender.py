"""Three-mode personalized recommender with paper_id anchoring.

Modes:
  off      — positive samples < 1 → fixed 0.5
  centroid — 1 <= positive < 20   → TF-IDF centroid cosine similarity
  model    — positive >= 20 AND negative >= 20 → CalibratedClassifierCV(LR)
"""
import logging
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import APP_CONFIG
from ..models import Paper, Tag

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent.parent / "models"
_centroid_state: dict | None = None
_model_state: dict | None = None
_dirty = True


def _get_thresholds() -> dict:
    return APP_CONFIG.get("recommender", {})


async def _count_tags(db: AsyncSession) -> tuple[int, int]:
    pos_result = await db.execute(
        select(func.count(Tag.paper_id.distinct())).where(Tag.tag_type == "interested")
    )
    pos_count = pos_result.scalar_one()
    neg_result = await db.execute(
        select(func.count(Tag.paper_id.distinct())).where(Tag.tag_type == "not_interested")
    )
    neg_count = neg_result.scalar_one()
    return pos_count, neg_count


async def get_mode(db: AsyncSession) -> str:
    thresholds = _get_thresholds()
    min_pos_centroid = thresholds.get("min_pos_centroid", 1)
    min_pos_model = thresholds.get("min_pos_model", 20)
    min_neg_model = thresholds.get("min_neg_model", 20)

    pos_count, neg_count = await _count_tags(db)

    if pos_count >= min_pos_model and neg_count >= min_neg_model:
        return "model"
    if pos_count >= min_pos_centroid:
        return "centroid"
    return "off"


async def _get_labeled_papers(db: AsyncSession) -> tuple[list[Paper], list[Paper]]:
    pos_result = await db.execute(
        select(Paper).join(Tag, Tag.paper_id == Paper.id).where(Tag.tag_type == "interested").distinct()
    )
    pos_papers = list(pos_result.scalars().all())

    neg_result = await db.execute(
        select(Paper).join(Tag, Tag.paper_id == Paper.id).where(Tag.tag_type == "not_interested").distinct()
    )
    neg_papers = list(neg_result.scalars().all())

    return pos_papers, neg_papers


def _build_centroid(pos_papers: list[Paper]) -> tuple[TfidfVectorizer, csr_matrix | None]:
    texts = [(p.abstract_en or p.title or "") for p in pos_papers]
    if not texts:
        return TfidfVectorizer(), None
    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    tfidf = vectorizer.fit_transform(texts)
    centroid = tfidf.mean(axis=0)
    return vectorizer, csr_matrix(centroid)


def _train_model(pos_papers: list[Paper], neg_papers: list[Paper]) -> tuple[TfidfVectorizer, CalibratedClassifierCV]:
    pos_texts = [(p.abstract_en or p.title or "") for p in pos_papers]
    neg_texts = [(p.abstract_en or p.title or "") for p in neg_papers]
    texts = pos_texts + neg_texts
    labels = [1] * len(pos_texts) + [0] * len(neg_texts)

    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    X = vectorizer.fit_transform(texts)

    lr = LogisticRegression(max_iter=1000, C=1.0)
    calibrated = CalibratedClassifierCV(lr, cv=3)
    calibrated.fit(X, labels)

    return vectorizer, calibrated


def _score_centroid(paper: Paper, vectorizer: TfidfVectorizer, centroid: csr_matrix) -> float:
    text = (paper.abstract_en or paper.title or "")
    if not text or centroid is None:
        return 0.0
    vec = vectorizer.transform([text])
    sim = cosine_similarity(vec, centroid)[0][0]
    return float(max(0.0, min(1.0, sim)))


def _score_model(paper: Paper, vectorizer: TfidfVectorizer, model: CalibratedClassifierCV) -> float:
    text = (paper.abstract_en or paper.title or "")
    if not text:
        return 0.5
    vec = vectorizer.transform([text])
    prob = model.predict_proba(vec)[0][1]
    return float(prob)


def mark_dirty():
    global _dirty
    _dirty = True


async def retrain_if_dirty(db: AsyncSession):
    global _centroid_state, _model_state, _dirty

    if not _dirty:
        return

    mode = await get_mode(db)
    pos_papers, neg_papers = await _get_labeled_papers(db)

    if mode == "centroid" and pos_papers:
        vectorizer, centroid = _build_centroid(pos_papers)
        _centroid_state = {"vectorizer": vectorizer, "centroid": centroid}
        _model_state = None
        logger.info("Recommender retrained: centroid mode (%d positives)", len(pos_papers))
    elif mode == "model" and pos_papers and neg_papers:
        vectorizer, model = _train_model(pos_papers, neg_papers)
        _model_state = {"vectorizer": vectorizer, "model": model}
        _centroid_state = None
        logger.info("Recommender retrained: model mode (%d pos, %d neg)", len(pos_papers), len(neg_papers))
    else:
        _centroid_state = None
        _model_state = None

    _dirty = False


async def score(paper: Paper, db: AsyncSession) -> float:
    """Compute personalization score for a paper.

    Returns 0.5 in off mode, cosine similarity in centroid mode,
    calibrated probability in model mode.
    """
    global _centroid_state, _model_state

    await retrain_if_dirty(db)
    mode = await get_mode(db)

    if mode == "off":
        return 0.5

    if mode == "centroid":
        if _centroid_state and _centroid_state.get("centroid") is not None:
            return _score_centroid(paper, _centroid_state["vectorizer"], _centroid_state["centroid"])
        return 0.5

    if mode == "model":
        if _model_state:
            return _score_model(paper, _model_state["vectorizer"], _model_state["model"])
        return 0.5

    return 0.5
