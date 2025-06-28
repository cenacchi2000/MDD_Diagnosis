import re
from typing import Match, Pattern

# I have removed , and - as a eos separator seems it works better
# Add a space after each character to ensure it is not mid statement
# Except for full stops where we've added a neos
EOS_SEPARATORS_RAW = [
    r"\. ",
    r"\! ",
    r"\? ",
    r"\n",
    r"\: ",
    r"\; ",
    r"\… ",
    r"\。 ",
    r"\？ ",
    r"\， ",
    r"\！ ",
    r"\、 ",
    r"\۔ ",
    r"\؟ ",
    r"\١ ",
    r"\، ",
    r"\। ",
    r"\—",
]
EOS_SEPARATORS = re.compile("|".join(EOS_SEPARATORS_RAW))
NEOS_SEPARATORS_RAW = [
    r"[0-9]+[:blank:]?:[:blank:]?[0-9]+",  # This deals with times eg 3:30
    r"\b[A-Z][a-z]{,2}\.",  # This handles abbreviations eg Dr., St., Col. up to 3 letters (this can be increased)
]
NEOS_SEPARATORS = re.compile("|".join(NEOS_SEPARATORS_RAW))


def string_chunker(
    input_string: str,
    min_chunk_length: int,
    EOS: Pattern = EOS_SEPARATORS,
    NEOS: Pattern = NEOS_SEPARATORS,
    strip_tail: bool = True,
) -> tuple[str, str]:

    def key_function(match: Match) -> int:
        return match.end()

    # list of all match indexs large to small
    eos_matches = sorted(
        {match for match in re.finditer(EOS, input_string) if match},
        key=key_function,
        reverse=True,
    )
    # list of unordered neos matches
    neos_matches = {match for match in re.finditer(NEOS, input_string) if match}

    # As the EOS_SEPARATORS are only one character we can check that the beginning or the end of the index is in the neos match
    # Check for highest index first
    if eos_matches:
        for match in eos_matches:
            sep_index = match.end()
            sep_index_start = match.start()
            if sep_index > min_chunk_length:
                if not any(
                    (neos.start() <= sep_index and sep_index <= neos.end())
                    or (
                        neos.start() <= sep_index_start
                        and sep_index_start <= neos.end()
                    )
                    for neos in neos_matches
                ):
                    # The index is suitable
                    # Because we used the end of the match, we dont need to add the lenght of the eos separator.
                    split_index = sep_index
                    if strip_tail:
                        yield_content = input_string[:split_index].strip()
                    else:
                        yield_content = input_string[:split_index]
                    remaining_string = input_string[split_index:]
                    return yield_content, remaining_string

        # None of the matches satisfied the conditions
        # Current desired behaviour is to yield everything we have
        return "", input_string
    # No EOS matches
    else:
        # Yield everything and just say what we have
        return "", input_string