"""한국어 문서 검색: 문자 2-gram TF-IDF + 코사인 유사도.

형태소 분석기 없이도 조사·어미 변화에 강하고, 외부 서비스 없이 사내망에서 동작한다.
코퍼스 규모(조문 수백 건, 사례 수천 건, 사례집 조각 수만 건)에서 충분히 빠르다.
"""
import math
import re
from collections import Counter

_CLEAN = re.compile(r"[^0-9A-Za-z가-힣]+")
STOP_BIGRAMS = {"하여", "여야", "한다", "있다", "하는", "에게", "에서", "으로", "니한", "아니", "에는", "같다", "한다", "경우"}


def bigrams(text: str) -> Counter:
    grams: Counter = Counter()
    for token in _CLEAN.split(text.lower()):
        if not token:
            continue
        if len(token) == 1:
            grams[token] += 1
            continue
        for i in range(len(token) - 1):
            g = token[i:i + 2]
            if g not in STOP_BIGRAMS:
                grams[g] += 1
    return grams


class Index:
    def __init__(self, docs: list[tuple[object, str]]):
        self.ids = [d[0] for d in docs]
        tfs = [bigrams(d[1]) for d in docs]
        df: Counter = Counter()
        for tf in tfs:
            df.update(tf.keys())
        n = max(1, len(docs))
        self.idf = {g: math.log((n + 1) / (c + 0.5)) for g, c in df.items()}
        self.vecs = []
        for tf in tfs:
            vec = {g: (1 + math.log(c)) * self.idf[g] for g, c in tf.items()}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self.vecs.append({g: v / norm for g, v in vec.items()})

    def query(self, text: str, top_k: int = 10, min_score: float = 0.02) -> list[tuple[object, float, list[str]]]:
        tf = bigrams(text)
        q = {g: (1 + math.log(c)) * self.idf.get(g, 0.0) for g, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in q.values())) or 1.0
        q = {g: v / norm for g, v in q.items() if v > 0}
        if not q:
            return []
        scored = []
        for doc_id, vec in zip(self.ids, self.vecs):
            s = 0.0
            hits = []
            for g, w in q.items():
                dv = vec.get(g)
                if dv:
                    s += w * dv
                    hits.append((w * dv, g))
            if s >= min_score:
                hits.sort(reverse=True)
                scored.append((doc_id, s, [h[1] for h in hits[:6]]))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


_cache: dict[str, tuple[object, Index]] = {}


def cached_index(name: str, version_key, loader) -> Index:
    """version_key 가 바뀌면 다시 색인한다(데이터 변경 감지)."""
    hit = _cache.get(name)
    if hit and hit[0] == version_key:
        return hit[1]
    idx = Index(loader())
    _cache[name] = (version_key, idx)
    return idx


def clear_cache() -> None:
    _cache.clear()
