from dataclasses import dataclass, asdict
from datetime import datetime
import glob
import json
import os
from typing import Any, Optional, Iterable
import re
import fnmatch


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _iter_coauthors(commit_message: str) -> Iterable[tuple[str, str]]:
    """
    Extract co-authors from commit trailers like:
        Co-authored-by: Name Surname <email@example.com>
    Case-insensitive, tolerant to spacing.
    Yields (name, email) pairs in lowercase.
    """
    if not commit_message:
        return []
    pattern = re.compile(r"(?im)^\s*co-?authored-?by:\s*(.*?)\s*<([^>]+)>\s*$")
    for m in pattern.finditer(commit_message or ""):
        name = _normalize(m.group(1))
        mail = _normalize(m.group(2))
        if name or mail:
            yield (name, mail)


def _match_pattern(pat: str, text: str) -> bool:
    """
    Flexible matcher supporting three modes:
        1) Regex: prefix 're:' to use the remainder as a Python regex.
        2) Glob: if the pattern contains shell wildcards '*', '?', or '[]', use fnmatch.
        3) Substring: otherwise do a case-insensitive substring check.
    """
    pat_norm = (pat or "").strip()
    text_norm = _normalize(text)

    if not pat_norm:
        return False

    # Regex mode via explicit prefix
    if pat_norm.startswith("re:"):
        try:
            regex = re.compile(pat_norm[3:], re.IGNORECASE)
            return bool(regex.search(text_norm))
        except re.error:
            # Fall back to substring if regex is invalid
            return _normalize(pat_norm[3:]) in text_norm

    # Glob mode if shell wildcard chars are present
    if any(ch in pat_norm for ch in "*?[]"):
        return fnmatch.fnmatch(text_norm, pat_norm.lower())

    # Default: substring
    return _normalize(pat_norm) in text_norm


@dataclass(frozen=True)
class Heuristic:
    author_names: tuple[str]
    author_mails: tuple[str]
    files: tuple[str]
    branch_name_prefix: tuple[str]
    commit_message_prefix: tuple[str]
    period_start: datetime
    period_end: Optional[datetime]

    def match_commit(self, commit_message: str, commit_author: str) -> bool:
        """
        Returns True if this heuristic matches the given commit information.
        Matching is case-insensitive and supports substring, glob, and explicit regex ('re:' prefix).
        It checks:
            - author identity (name/email) against commit_author
            - co-authors listed in the commit message trailers
            - commit message content against known prefixes/hints
        """
        cm = commit_message or ""
        ca = commit_author or ""

        # 1) Author identity (name OR email) in the main author field
        for name in self.author_names:
            if _match_pattern(name, ca):
                return True
        for mail in self.author_mails:
            if _match_pattern(mail, ca):
                return True

        # 2) Co-authors listed in the commit message
        for co_name, co_mail in _iter_coauthors(cm):
            for name in self.author_names:
                if _match_pattern(name, co_name):
                    return True
            for mail in self.author_mails:
                if _match_pattern(mail, co_mail):
                    return True

        # 3) Commit message prefixes / hints
        for prefix in self.commit_message_prefix:
            if _match_pattern(prefix, cm):
                return True

        return False

    def match_branch(self, branch_name: str) -> bool:
        """
        Returns True if this heuristic matches the given branch or PR name.
        Supports substring, glob, and explicit regex ('re:' prefix).
        """
        bn = branch_name or ""
        for prefix in self.branch_name_prefix:
            if _match_pattern(prefix, bn):
                return True
        return False

    def is_active(self, time: Optional[datetime] = None) -> bool:
        """Check if this heuristic can be used at the given time.
        When None, now is used.

        Args:
            time (Optional[datetime], optional): time to check if heuristic can be active. Defaults to None.
        """
        to_check = time or datetime.now()
        return to_check >= self.period_start and (
            self.period_end is None or to_check <= self.period_end
        )

    def to_ser_json(self) -> Any:
        """Returns a serializable version of this object for JSON description."""
        dico = asdict(self)
        dico["period_start"] = self.period_start.isoformat()
        if self.period_end is None:
            dico["period_end"] = None
        else:
            dico["period_end"] = self.period_end.isoformat()
        return dico


def from_json(obj: Any) -> Heuristic:
    """
    Produce a heuristic by deserializing a JSON object.
    """
    author_names = tuple(obj["author_names"])
    author_mails = tuple(obj["author_mails"])
    files = tuple(obj["files"])
    branch_name_prefix = tuple(obj["branch_name_prefix"])
    commit_message_prefix = tuple(obj["commit_message_prefix"])
    try:
        period_start = datetime.fromisoformat(obj["period_start"])
    except (ValueError, KeyError):
        period_start = datetime.min  # treat missing/empty as "active from the beginning"
    period_end = None
    if not (obj["period_end"] is None or obj["period_end"] in ["None", "null"]):
        period_end = datetime.fromisoformat(obj["period_end"])

    return Heuristic(
        author_names,
        author_mails,
        files,
        branch_name_prefix,
        commit_message_prefix,
        period_start,
        period_end,
    )


def load_heuristics_for_agent(file: str) -> list[Heuristic]:
    """Loads all the heuristics contained in the specified JSON file.
    Note that it also loads inactive, i.e. no longer in use, heuristics.
    """
    todo = []
    with open(file) as fd:
        ser_heuristics_list = json.load(fd)
        if not isinstance(ser_heuristics_list, list):
            ser_heuristics_list = [ser_heuristics_list]
            todo.append(ser_heuristics_list)
    if todo:
        with open(file, "w") as fd:
            json.dump(ser_heuristics_list, fd)
    return [from_json(el) for el in ser_heuristics_list]


def load_heuristics(folder: str) -> dict[str, list[Heuristic]]:
    """Loads all the heuristics for each agent contained in the specified folder.

    Returns:
        dict[str, list[Heuristic]]: agent_name -> list[heuristic]
    """
    dico = {}
    for file in glob.glob(os.path.join(folder, "*.json")):
        heuristics_list = [
            el for el in load_heuristics_for_agent(file)
        ]
        agent_name = os.path.basename(file)[:-5]
        dico[agent_name] = heuristics_list
    return dico