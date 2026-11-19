from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from pymongo import MongoClient

from application.config import COLLECTION, DB_NAME, MONGO_URI
from calcul.matching import calculate_precision_resemblance


class SchemaNormalizerWorker(QThread):
    """Normalise en arrière-plan les anciens profils link/resemblance vers url/percentage."""

    log = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, batch_limit: int = 25):
        super().__init__()
        self.batch_limit = batch_limit

    def run(self):
        updated_count = 0
        try:
            query = {
                "socialAccounts.linkedin": {
                    "$elemMatch": {
                        "$or": [
                            {"link": {"$exists": True}},
                            {"resemblance": {"$exists": True}},
                            {"url": {"$exists": False}},
                            {"percentage": {"$exists": False}},
                        ]
                    }
                }
            }
            with MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                socketTimeoutMS=20000,
            ) as client:
                col = client[DB_NAME][COLLECTION]
                docs = list(col.find(query).limit(self.batch_limit))
                for doc in docs:
                    entries = doc.get("socialAccounts", {}).get("linkedin") or []
                    if not isinstance(entries, list) or not entries:
                        continue

                    normalized = []
                    for item in entries:
                        if not isinstance(item, dict):
                            continue
                        raw_url = (
                            item.get("url")
                            or item.get("URL")
                            or item.get("link")
                            or ""
                        )
                        cand = {
                            "name": item.get("name", ""),
                            "url": raw_url,
                            "snippet": "",
                        }
                        score, _ = calculate_precision_resemblance(cand, doc)
                        if score <= 0:
                            continue
                        normalized.append(
                            {
                                "url": raw_url,
                                "name": item.get("name", ""),
                                "percentage": score,
                            }
                        )

                    res = col.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"socialAccounts.linkedin": normalized}},
                    )
                    updated_count += res.modified_count

            if updated_count > 0:
                self.log.emit(
                    f"🔄 Normalisation MongoDB automatique : {updated_count} document(s) "
                    f"mis à jour (url / name / percentage)."
                )
        except Exception as exc:
            self.log.emit(f"ℹ️ Normalisation arrière-plan différée : {exc}")
        finally:
            self.finished.emit(updated_count)