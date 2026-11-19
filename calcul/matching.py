"""Helpers for matching LinkedIn company profiles to company records using multi-field signals."""

from difflib import SequenceMatcher
import hashlib
import re
import unicodedata
import urllib.parse


STOP_WORDS = {
    "sarl", "sas", "sasu", "sa", "sci", "eurl", "snc", "gmbh", "ltd", "llc", "inc",
    "corp", "co", "cie", "de", "la", "le", "les", "du", "des", "et", "and", "the",
    "en", "france", "group", "groupe", "d", "l", "b", "v", "scp", "selarl", "earl"
}

FOREIGN_COUNTRIES = {
    "united states", "usa", "etats-unis", "india", "inde", "united kingdom",
    "royaume-uni", "london", "california", "new york", "texas", "florida",
    "australia", "australie", "canada", "brazil", "bresil", "singapore"
}

IRRELEVANT_KEYWORDS = {
    "football", "club", "association", "fc", "as", "sport", "volley", "basket", "handball"
}


def strip_accents(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def extract_distinctive_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", strip_accents(text))
    return {word for word in words if word not in STOP_WORDS and len(word) > 1}


def clean_company_name(name: str) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    legal_suffixes = [
        r"\bS\.?A\.?R\.?L\.?\b", r"\bS\.?A\.?S\.?U?\.?\b", r"\bS\.?A\.?\b",
        r"\bE\.?U\.?R\.?L\.?\b", r"\bS\.?N\.?C\.?\b", r"\bS\.?C\.?I\.?\b",
        r"\bL\.?T\.?D\.?\b", r"\bL\.?L\.?C\.?\b", r"\bI\.?N\.?C\.?\b",
        r"\bG\.?M\.?B\.?H\.?\b", r"\bB\.?V\.?\b", r"\bS\.?P\.?A\.?\b", r"\bS\.?L\.?\b",
    ]
    for pattern in legal_suffixes:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[-–|/\\].*$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or name.strip()


def clean_linkedin_title(title: str) -> str:
    cleaned = re.sub(r"\s*[-|:]\s*LinkedIn.*$", "", title, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\s*[-|:]\s*(Présentation|Overview|Accueil|Avis|Jobs|Emplois).*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def _normalize_compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", strip_accents(text))


def _collect_text_values(value) -> list[str]:
    """Extrait proprement les chaînes textuelles depuis une valeur simple, liste ou dictionnaire."""
    items: list[str] = []
    if value is None:
        return items
    if isinstance(value, str):
        cleaned = strip_accents(value)
        if cleaned:
            items.append(cleaned)
    elif isinstance(value, (list, tuple, set)):
        for sub in value:
            items.extend(_collect_text_values(sub))
    elif isinstance(value, dict):
        for sub in value.values():
            items.extend(_collect_text_values(sub))
    else:
        cleaned = strip_accents(str(value))
        if cleaned:
            items.append(cleaned)
    return items


def _is_french_company(company: dict) -> bool:
    country = strip_accents(company.get("countryCode") or "")
    region = strip_accents(company.get("region") or "")
    register_id = re.sub(r"\D+", "", str(company.get("registerId") or ""))
    if country in {"fr", "fra", "france"} or region.startswith("fr") or len(register_id) in {9, 14}:
        return True
    return False


def calculate_precision_resemblance(cand: dict, company: dict) -> tuple[float, dict]:
    """
    Calcule un pourcentage de correspondance multicritère en croisant :
    - le nom et nom commercial
    - l'adresse, localisation, code postal et coordonnées
    - le site web et les domaines
    - l'e-mail (domaine ou racine significative)
    - la description et les activités de l'entreprise
    Retourne 0.0 lorsqu'aucune correspondance pertinente n'est établie.
    """
    if not isinstance(cand, dict) or not isinstance(company, dict):
        return 0.0, {"is_valid": False, "name_f1": 0.0, "domain_match": False, "email_match": False}

    cand_name = strip_accents(clean_linkedin_title(cand.get("name") or ""))
    raw_url = urllib.parse.unquote(
        cand.get("url") or cand.get("URL") or cand.get("link") or ""
    )
    cand_url = strip_accents(raw_url)
    cand_desc = strip_accents(cand.get("snippet") or cand.get("description") or "")

    cand_slug_match = re.search(r"/company/([a-z0-9_\-%]+)", cand_url)
    cand_slug = urllib.parse.unquote(cand_slug_match.group(1)) if cand_slug_match else ""
    cand_full_text = f"{cand_desc} {cand_name} {cand_slug}".strip()

    if not cand_full_text or any(keyword in cand_full_text for keyword in IRRELEVANT_KEYWORDS):
        return 0.0, {"is_valid": False, "name_f1": 0.0, "domain_match": False, "email_match": False}

    comp_name = strip_accents(company.get("companyName") or "")
    trade_name = strip_accents(company.get("tradeName") or "")
    street = strip_accents(company.get("street") or company.get("streetName") or "")
    location = strip_accents(company.get("location") or company.get("region") or "")
    postal_code = strip_accents(
        str(company.get("postalCode") or company.get("zipCode") or company.get("zip") or "")
    )

    desc_parts = (
        _collect_text_values(company.get("description"))
        + _collect_text_values(company.get("about"))
        + _collect_text_values(company.get("activities"))
        + _collect_text_values(company.get("activity"))
        + _collect_text_values(company.get("sector"))
        + _collect_text_values(company.get("industry"))
    )
    contact_parts = (
        _collect_text_values(company.get("email"))
        + _collect_text_values(company.get("emails"))
        + _collect_text_values(company.get("phone"))
        + _collect_text_values(company.get("phones"))
        + _collect_text_values(company.get("contact"))
    )

    domains = [strip_accents(d) for d in (company.get("domains") or []) if d]
    comp_url = strip_accents(company.get("url") or company.get("website") or "")
    if comp_url and comp_url not in domains:
        domains.append(comp_url)

    best_f1 = 0.0
    best_text_ratio = 0.0
    best_slug_ratio = 0.0
    exact_token_match = False
    exact_slug_match = False
    has_any_signal = False

    cand_tokens = extract_distinctive_tokens(cand_name)
    slug_tokens = extract_distinctive_tokens(cand_slug.replace("-", " ").replace("_", " "))
    cand_desc_tokens = extract_distinctive_tokens(cand_desc)
    all_cand_tokens = cand_tokens | slug_tokens
    cand_compact = _normalize_compact(cand_name)
    slug_compact = _normalize_compact(cand_slug)

    for target in [comp_name, trade_name]:
        if not target:
            continue
        comp_tokens = extract_distinctive_tokens(target)
        target_clean = clean_company_name(target)
        target_compact = _normalize_compact(target_clean)

        if comp_tokens and all_cand_tokens:
            inter = comp_tokens & all_cand_tokens
            if inter:
                has_any_signal = True
                cov_comp = len(inter) / len(comp_tokens)
                cov_cand = len(inter) / len(all_cand_tokens)
                f1 = (2 * cov_comp * cov_cand) / (cov_comp + cov_cand)
                if f1 > best_f1:
                    best_f1 = f1
                if comp_tokens == all_cand_tokens:
                    exact_token_match = True

        if target_compact:
            if cand_compact:
                text_ratio = SequenceMatcher(None, target_compact, cand_compact).ratio()
                if text_ratio >= 0.45:
                    has_any_signal = True
                if text_ratio > best_text_ratio:
                    best_text_ratio = text_ratio
            if slug_compact:
                slug_ratio = SequenceMatcher(None, target_compact, slug_compact).ratio()
                if slug_ratio >= 0.45:
                    has_any_signal = True
                if slug_ratio > best_slug_ratio:
                    best_slug_ratio = slug_ratio
                if target_compact == slug_compact:
                    exact_slug_match = True
                    has_any_signal = True

    score = (
        (best_f1 * 36.0)
        + (best_text_ratio * 26.0)
        + (best_slug_ratio * 18.0)
    )

    if exact_token_match:
        score += 5.0
    if exact_slug_match:
        score += 10.0
    elif comp_name and comp_name in cand_slug:
        score += 5.0
        has_any_signal = True

    domain_match = False
    for domain in domains:
        clean_domain = re.sub(r"^https?://(?:www\.)?|/.*$", "", domain)
        domain_name = clean_domain.split(".")[0]
        if domain_name and len(domain_name) > 1 and domain_name in cand_full_text:
            score += 12.0
            domain_match = True
            has_any_signal = True
            break

    email_matched = False
    for entry in contact_parts:
        emails_found = re.findall(r"[a-z0-9._%+-]+@([a-z0-9.-]+)", entry)
        for email_domain in emails_found:
            mail_root = email_domain.split(".")[0]
            if mail_root and len(mail_root) > 2 and mail_root in cand_full_text:
                score += 6.0
                email_matched = True
                has_any_signal = True
                break
        if email_matched:
            break

    if street and len(street) > 3:
        street_tokens = extract_distinctive_tokens(street)
        if street_tokens and (street_tokens & (all_cand_tokens | cand_desc_tokens)):
            score += 4.0
            has_any_signal = True
    if location and len(location) > 2 and location in cand_full_text:
        score += 6.0
        has_any_signal = True
    if postal_code and len(postal_code) >= 4 and postal_code in cand_full_text:
        score += 4.0
        has_any_signal = True

    if desc_parts and cand_desc_tokens:
        comp_desc_tokens = extract_distinctive_tokens(" ".join(desc_parts))
        if comp_desc_tokens:
            overlap = comp_desc_tokens & cand_desc_tokens
            if overlap:
                ratio_desc = min(len(overlap) / max(len(comp_desc_tokens), 1), 1.0)
                score += round(ratio_desc * 8.0, 2)
                has_any_signal = True

    if not has_any_signal or score <= 0.0:
        return 0.0, {
            "is_valid": False,
            "name_f1": round(best_f1, 2),
            "domain_match": domain_match,
            "email_match": email_matched,
        }

    signature_source = (
        f"{cand_url}|{comp_name}|{trade_name}|{street}|{location}|{postal_code}|"
        f"{'|'.join(domains)}|{'|'.join(contact_parts[:2])}|{' '.join(desc_parts[:2])}"
    )
    url_hash = int(hashlib.md5(signature_source.encode("utf-8")).hexdigest(), 16)
    unique_jitter = (url_hash % 99) / 100.0

    final_score = max(1.0, min(round(score + unique_jitter, 2), 100.0))
    is_valid = final_score >= 45.0 and (
        best_f1 >= 0.30 or exact_slug_match or domain_match or email_matched
    )

    return final_score, {
        "is_valid": is_valid,
        "name_f1": round(best_f1, 2),
        "domain_match": domain_match,
        "email_match": email_matched,
    }