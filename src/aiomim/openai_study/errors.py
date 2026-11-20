"""Control-flow signals of the study runner.

`Pending`, `ForbiddenCall` and `NetworkBlocked` derive from `BaseException`, not
`Exception`: the project's code catches `Exception` in several places (a failed call
for one paper must not sink an entry), and none of these signals may be swallowed
there. The project's only `except BaseException` handlers (`cache.DiskCache.put_text`,
`http.Http.download`) re-raise.
"""

from __future__ import annotations


class Pending(BaseException):
    """A reply this task needs is not in the cache yet; the request was recorded for the next batch."""


class ForbiddenCall(BaseException):
    """The task asked for a model call the study does not allow (a different prompt, a split of a
    fixed fact list, a tool session, a Claude call). A kit or bundle problem: never sent."""


class NetworkBlocked(BaseException):
    """Something tried to reach the network while the study runs offline."""


class StudyError(RuntimeError):
    """A problem with the study's configuration, bundle or state that needs a person."""
