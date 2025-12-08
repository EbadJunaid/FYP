from datetime import datetime, timedelta, timezone

class date_helper:

    def month_key(self,dt):
        return dt.strftime("%Y-%m")

    def _now_iso(self):
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    def _soon_iso(self):
        return (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace('+00:00', 'Z')

    def _end_of_month(self, dt):
        if dt.month < 12:
            return datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)
        else:
            return datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)

