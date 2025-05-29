from datetime import datetime, timedelta
import re

def replace_relative_date(sentence, base_date=None):
    if base_date is None:
        base_date = datetime.today()

    # Dictionary with a list of equivalent keywords for each relative date
    keyword_groups = {
        0: ["today", "tonight", "this evening", "this morning"],
        1: ["tomorrow", "tmr", "the next day"],
        -1: ["yesterday", "the previous day"]
    }

    # Compile a flattened keyword-to-offset map for regex matching
    keyword_to_offset = {
        keyword: offset
        for offset, keywords in keyword_groups.items()
        for keyword in keywords
    }

    # Sort keywords by length (longest first) to avoid partial replacements
    sorted_keywords = sorted(keyword_to_offset.keys(), key=len, reverse=True)
    replaced = False 
    for keyword in sorted_keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, sentence, flags=re.IGNORECASE):
            date_offset = keyword_to_offset[keyword]
            new_date = (base_date + timedelta(days=date_offset)).strftime("%Y-%m-%d")
            sentence = re.sub(pattern, new_date, sentence, flags=re.IGNORECASE)
            replaced = True
    return sentence, replaced
