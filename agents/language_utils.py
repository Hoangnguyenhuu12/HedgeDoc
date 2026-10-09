"""
Language utility for dynamic Language Mirroring in HedgeDoc.
Detects English vs Vietnamese to automatically adapt all agent responses.
"""

import re


def detect_language(text: str) -> str:
    """
    Detects whether the input text is English ('en') or Vietnamese ('vi').
    Balances Vietnamese diacritics and common vocabulary sets so foreign names or loan words
    (e.g., Saint-Exupéry, café) in English sentences don't misclassify as Vietnamese.
    """
    if not text:
        return "vi"
    t = text.lower().strip()

    # English stopword / structural vocabulary
    en_words = {
        "who", "what", "where", "when", "why", "how", "is", "are", "was", "were",
        "the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by",
        "can", "could", "should", "would", "do", "does", "did", "have", "has",
        "you", "your", "i", "me", "my", "we", "our", "they", "them", "their",
        "this", "that", "these", "those", "it", "its", "tell", "summarize",
        "explain", "show", "list", "give", "help", "hello", "hi", "hey",
        "thanks", "thank", "please", "document", "documents", "about",
        "read", "find", "search", "name", "author", "content", "and", "or",
        "not", "from", "which", "will", "would", "any", "all", "book", "system"
    }

    # Vietnamese vocabulary (with and without diacritics)
    vi_words = {
        "ban", "bạn", "la", "là", "ai", "toi", "tôi", "gi", "gì", "sao", "khong", "không",
        "co", "có", "giup", "giúp", "chao", "chào", "xin", "duoc", "được", "tai", "tại",
        "lieu", "liệu", "nay", "này", "nhu", "như", "the", "thế", "nao", "nào",
        "sach", "sách", "bao", "nhieu", "nhiều", "o", "ở", "dau", "đâu", "khi",
        "trong", "kho", "cua", "của", "va", "và", "nhung", "những", "cho",
        "voi", "với", "lam", "làm", "ve", "về", "doc", "đọc", "tim", "tìm"
    }

    words = re.findall(r"\b[\w\'-]+\b", t)
    token_set = set(words)
    en_count = len(token_set.intersection(en_words))
    vi_count = len(token_set.intersection(vi_words))

    # Vietnamese-specific diacritics
    vi_chars = set("àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ")
    vi_char_count = sum(1 for c in t if c in vi_chars)

    # 1. If strongly English vocabulary dominates
    if en_count >= 2 and en_count > vi_count:
        return "en"

    # 2. If substantial Vietnamese diacritics and not clearly English
    if vi_char_count >= 2 and vi_count >= en_count:
        return "vi"
    if vi_char_count > 0 and en_count == 0:
        return "vi"

    # 3. Fallback based on relative counts
    if en_count > vi_count:
        return "en"
    if vi_count > en_count:
        return "vi"

    return "en" if en_count > 0 else "vi"


def strip_vietnamese_accents(text: str) -> str:
    """Removes Vietnamese tone marks and special characters for fuzzy matching."""
    if not text:
        return ""
    import unicodedata
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return only_ascii.replace('đ', 'd').replace('Đ', 'D').lower().strip()


def clean_doc_title(file_name: str) -> str:
    """Extracts a human-friendly book/document title from file name."""
    if not file_name:
        return ""
    name = re.sub(r"\.[a-zA-Z0-9]+$", "", file_name)  # remove extension
    name = re.sub(r"^\d+[-_]", "", name)  # remove leading ID numbers like 10048-
    name = re.sub(r"[-_]thuviensach\.vn", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[-_]doc$", "", name, flags=re.IGNORECASE)
    name = name.replace("-", " ").replace("_", " ").strip()
    return name.title() if name.islower() else name


def is_summarization_query(query: str) -> bool:
    """Detects whether user is requesting a book/document summary or broad overview."""
    q = strip_vietnamese_accents(query)
    patterns = [
        r"\btom tat\b",
        r"\btong quan\b",
        r"\bnoi dung chinh\b",
        r"\bnoi dung cuon\b",
        r"\bnoi dung sach\b",
        r"\bnoi ve gi\b",
        r"\bco gi hay\b",
        r"\bgioi thieu sach\b",
        r"\bcuon sach nay\b",
        r"\bsach nay\b",
        r"\btai lieu nay\b",
        r"\bsummarize\b",
        r"\bsummary\b",
        r"\bwhat is .* about\b",
        r"\boverview\b",
    ]
    return any(re.search(p, q) for p in patterns)


def match_target_document(query: str, indexed_docs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Finds which indexed document the user is referring to based on query tokens.
    Returns matched document dict, or None if ambiguous/not found.
    """
    if not indexed_docs:
        return None

    q_norm = strip_vietnamese_accents(query)

    best_match = None
    best_score = 0

    for doc in indexed_docs:
        fname = doc.get("file_name", "")
        clean_t = clean_doc_title(fname)
        t_norm = strip_vietnamese_accents(clean_t)

        # Check full title phrase match (e.g. 'ca phe cung tony', 'hoang tu be')
        t_words = [w for w in re.findall(r"\b\w+\b", t_norm) if len(w) > 1]
        matched_words = [w for w in t_words if w in q_norm]

        if t_norm in q_norm:
            score = 100 + len(t_norm)
        elif len(q_norm) >= 3 and q_norm in t_norm:
            score = 80 + len(q_norm)
        elif len(matched_words) >= 2:
            score = len(matched_words) * 10
        elif len(matched_words) == 1 and len(matched_words[0]) >= 4 and matched_words[0] in q_norm:
            score = 25
        else:
            score = 0

        if score > best_score:
            best_score = score
            best_match = doc

    if best_score >= 10:
        return best_match

    # If only 1 indexed document and query asks 'sách này' or 'tài liệu này'
    generic_refs = ["sach nay", "tai lieu nay", "cuon sach nay", "cuon nay", "this book", "this document"]
    if any(r in q_norm for r in generic_refs):
        if len(indexed_docs) == 1:
            return indexed_docs[0]

    return None


def extract_followup_suggestions(text: str) -> List[str]:
    """Extracts 2-4 clean follow-up questions from LLM response text."""
    if not text:
        return []
    suggestions = []
    lines = text.split("\n")
    collecting = False

    for line in lines:
        line_clean = line.strip()
        lower_line = line_clean.lower()
        if any(h in lower_line for h in ["gợi ý tra cứu", "gợi ý câu hỏi", "follow-up question", "suggested question", "câu hỏi gợi ý"]):
            collecting = True
            continue
        if collecting:
            match = re.match(r"^[-*•\d\.\)]\s*(?:\[|\()?([^\]\)]+)(?:\]|\))?$", line_clean)
            if not match:
                match = re.match(r"^[-*•\d\.\)]\s*(.+)$", line_clean)
            if match:
                sug = match.group(1).strip().strip("[]\"'")
                if len(sug) > 6 and sug not in suggestions:
                    suggestions.append(sug)
            elif not line_clean:
                continue
            else:
                if line_clean.startswith("#") or line_clean.startswith("**"):
                    break
    return suggestions[:4]


def is_legal_inquiry(query: str) -> bool:
    """Detects whether user is looking for laws, legal clauses, contracts, or regulations."""
    q = strip_vietnamese_accents(query)
    patterns = [
        r"\bquy dinh\b",
        r"\bdieu khoan\b",
        r"\bdieu le\b",
        r"\bhop dong\b",
        r"\bvan ban luat\b",
        r"\bphap ly\b",
        r"\bnghi dinh\b",
        r"\bthong tu\b",
        r"\bterms and conditions\b",
        r"\bregulations?\b",
        r"\bclauses?\b",
        r"\blegal\b",
        r"\bcontract\b",
        r"\bbylaws?\b"
    ]
    return any(re.search(p, q) for p in patterns)


def is_legal_document(file_name: str) -> bool:
    """Checks whether the document title suggests a legal, contractual or regulatory document."""
    t = strip_vietnamese_accents(clean_doc_title(file_name))
    legal_keywords = [
        "luat", "nghi dinh", "thong tu", "quyet dinh", "hop dong",
        "dieu le", "quy che", "quy dinh", "phap luat", "chinh sach",
        "contract", "agreement", "policy", "regulation", "statute", "terms", "bylaws"
    ]
    return any(kw in t for kw in legal_keywords)


def is_clarification_context(chat_history: Optional[List[Dict[str, str]]]) -> bool:
    """Detects if the previous assistant message asked user to choose a document to summarize or query."""
    if not chat_history:
        return False
    last_assistant = None
    for m in reversed(chat_history):
        if m.get("role") == "assistant":
            last_assistant = m.get("content", "")
            break
    if not last_assistant:
        return False
    c_lower = last_assistant.lower()
    markers = [
        "tóm tắt cuốn sách hay tài liệu nào",
        "vui lòng chọn bên dưới hoặc cho tôi biết tên tác phẩm",
        "which book or document would you like me to summarize",
        "đang muốn tra cứu nội dung này trong tài liệu nào",
        "which document would you like to query"
    ]
    return any(m in c_lower for m in markers)


def resolve_document_from_context(
    query: str,
    chat_history: Optional[List[Dict[str, str]]],
    indexed_docs: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Resolves target document from multi-turn conversational cues like:
    - Ordinals: 'cuốn thứ nhất', 'cuốn 1', 'cuốn đầu', 'số 2', '2', 'first', etc.
    - Shorthand book names: 'Tony', 'Hoàng tử bé', etc.
    """
    if not indexed_docs:
        return None

    q_norm = strip_vietnamese_accents(query.strip())

    # 1. Match numeric or ordinal references
    ordinal_map = {
        0: [
            r"^cuon\s+(thu\s+)?(1|nhat|dau|dau\s+tien)$",
            r"^so\s+1$",
            r"^1$",
            r"^tap\s+1$",
            r"^first(\s+one|\s+book)?$",
            r"^#1$"
        ],
        1: [
            r"^cuon\s+(thu\s+)?(2|hai|nhi)$",
            r"^so\s+2$",
            r"^2$",
            r"^tap\s+2$",
            r"^second(\s+one|\s+book)?$",
            r"^#2$"
        ],
        2: [
            r"^cuon\s+(thu\s+)?(3|ba)$",
            r"^so\s+3$",
            r"^3$",
            r"^tap\s+3$",
            r"^third(\s+one|\s+book)?$",
            r"^#3$"
        ]
    }

    for idx, patterns in ordinal_map.items():
        if idx < len(indexed_docs) and any(re.search(p, q_norm) for p in patterns):
            return indexed_docs[idx]

    # Dynamic match: cuốn 4, cuốn 5, số 4, 4...
    match_num = re.search(r"^(?:cuon\s+(?:thu\s+)?)?(\d+)$", q_norm)
    if match_num:
        try:
            num = int(match_num.group(1)) - 1
            if 0 <= num < len(indexed_docs):
                return indexed_docs[num]
        except (ValueError, IndexError):
            pass

    # 2. Match shorthand titles (e.g. 'Tony', 'Ca phe', 'Hoang tu be')
    matched = match_target_document(query, indexed_docs)
    if matched:
        return matched

    return None
