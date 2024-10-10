import logging
from datetime import datetime
from typing import Dict


class VisitorsLimit:
    def __init__(self, max_visits: int, max_visitor_limit: int, time_period_in_seconds: int):
        super().__init__()
        self._visitors: Dict[str, int] = {}
        self._MAX_VISITS = max_visits
        self._MAX_VISITOR_LIMIT = max_visitor_limit
        self._limit_reached_time = None
        self._TIME_PERIOD_IN_SECONDS = time_period_in_seconds

    def visit(self, visitor_id: str) -> bool:
        if (self._limit_reached_time is not None and
                (datetime.now() - self._limit_reached_time).seconds > self._TIME_PERIOD_IN_SECONDS):
            logging.info("Visitors limit reset. Time passed: %s",
                         (datetime.now() - self._limit_reached_time).seconds)
            self._visitors.clear()
            _limit_reached_time = None
        total_visits = sum(self._visitors.values())
        if total_visits < self._MAX_VISITS:
            if visitor_id not in self._visitors:
                self._visitors[visitor_id] = 1
            elif self._visitors[visitor_id] == self._MAX_VISITOR_LIMIT:
                return False
            else:
                self._visitors[visitor_id] += 1
            if total_visits == self._MAX_VISITS - 1:
                logging.info("Visitors limit reached")
                self._limit_reached_time = datetime.now()
            return True
        else:
            return False
